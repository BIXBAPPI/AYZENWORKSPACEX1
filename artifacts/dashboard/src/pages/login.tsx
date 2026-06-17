import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useLocation, useSearch } from "wouter";
import { useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form";
import { Link } from "wouter";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Zap, Eye, EyeOff, Shield } from "lucide-react";
import {
  isFirebaseConfigured,
  signInWithGoogle,
  signInWithFacebook,
  exchangeFirebaseToken,
} from "@/lib/firebase";

const schema = z.object({
  email: z.string().email("Valid email required"),
  password: z.string().min(1, "Password required"),
});

type FormData = z.infer<typeof schema>;

function GoogleIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
      <path d="M17.64 9.2c0-.637-.057-1.251-.164-1.84H9v3.481h4.844c-.209 1.125-.843 2.078-1.796 2.717v2.258h2.908c1.702-1.567 2.684-3.875 2.684-6.615Z" fill="#4285F4"/>
      <path d="M9 18c2.43 0 4.467-.806 5.956-2.18l-2.908-2.259c-.806.54-1.837.86-3.048.86-2.344 0-4.328-1.584-5.036-3.711H.957v2.332A8.997 8.997 0 0 0 9 18Z" fill="#34A853"/>
      <path d="M3.964 10.71A5.41 5.41 0 0 1 3.682 9c0-.593.102-1.17.282-1.71V4.958H.957A8.996 8.996 0 0 0 0 9c0 1.452.348 2.827.957 4.042l3.007-2.332Z" fill="#FBBC05"/>
      <path d="M9 3.58c1.321 0 2.508.454 3.44 1.345l2.582-2.58C13.463.891 11.426 0 9 0A8.997 8.997 0 0 0 .957 4.958L3.964 7.29C4.672 5.163 6.656 3.58 9 3.58Z" fill="#EA4335"/>
    </svg>
  );
}

function FacebookIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
      <circle cx="9" cy="9" r="9" fill="#1877F2"/>
      <path d="M12.5 9H10v6H7.5V9H6V6.5h1.5V5c0-1.654 1.346-3 3-3H13v2.5h-1.5c-.276 0-.5.224-.5.5v1.5H13L12.5 9Z" fill="white"/>
    </svg>
  );
}

export default function Login() {
  const [, setLocation] = useLocation();
  const queryClient = useQueryClient();
  const search = useSearch();
  const verified = new URLSearchParams(search).get("verified") === "1";

  const [isPending, setIsPending] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [showPassword, setShowPassword] = useState(false);
  const [socialLoading, setSocialLoading] = useState<"google" | "facebook" | null>(null);

  // 2FA state
  const [requires2fa, setRequires2fa] = useState(false);
  const [email2fa, setEmail2fa] = useState("");
  const [twoFACode, setTwoFACode] = useState("");
  const [twoFAMethod, setTwoFAMethod] = useState<"totp" | "email">("totp");
  const [twoFAPending, setTwoFAPending] = useState(false);
  const [twoFAError, setTwoFAError] = useState<string | null>(null);
  const [emailSent, setEmailSent] = useState(false);

  const firebaseEnabled = isFirebaseConfigured();

  const form = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: { email: "", password: "" },
  });

  async function onSubmit(values: FormData) {
    setIsPending(true);
    setErrorMsg(null);
    try {
      const res = await fetch("/api/v1/auth/login", {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(values),
      });
      const data = await res.json();
      if (!res.ok) {
        const msgs: Record<string, string> = {
          invalid_credentials: "Invalid email or password.",
          email_not_verified: "Please verify your email before logging in.",
        };
        setErrorMsg(msgs[data.detail] ?? data.detail ?? "Login failed");
        return;
      }
      if (data.requires_2fa) {
        setEmail2fa(values.email);
        setRequires2fa(true);
        return;
      }
      queryClient.invalidateQueries();
      setLocation("/dashboard");
    } catch {
      setErrorMsg("Network error. Please try again.");
    } finally {
      setIsPending(false);
    }
  }

  async function handleSocialLogin(provider: "google" | "facebook") {
    setSocialLoading(provider);
    setErrorMsg(null);
    try {
      const result = provider === "google"
        ? await signInWithGoogle()
        : await signInWithFacebook();
      if (!result) return;
      const ok = await exchangeFirebaseToken(result.idToken);
      if (ok) {
        queryClient.invalidateQueries();
        setLocation("/dashboard");
      } else {
        // New user — need activation code
        setLocation(`/register?social=1&email=${encodeURIComponent(result.email)}`);
      }
    } catch (e: any) {
      setErrorMsg(e.message || "Social login failed. Please try again.");
    } finally {
      setSocialLoading(null);
    }
  }

  async function sendEmailCode() {
    try {
      await fetch("/api/v1/vault/email-otp/send", { method: "POST", credentials: "include" });
      setEmailSent(true);
    } catch { /* ignore */ }
  }

  async function verify2fa() {
    if (!twoFACode.trim()) return;
    setTwoFAPending(true);
    setTwoFAError(null);
    try {
      const res = await fetch("/api/v1/auth/verify-2fa", {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: email2fa, code: twoFACode, method: twoFAMethod }),
      });
      const data = await res.json();
      if (!res.ok) { setTwoFAError(data.detail ?? "Invalid code. Try again."); return; }
      queryClient.invalidateQueries();
      setLocation("/dashboard");
    } catch {
      setTwoFAError("Network error. Please try again.");
    } finally {
      setTwoFAPending(false);
    }
  }

  if (requires2fa) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center p-8">
        <div className="w-full max-w-sm">
          <div className="mb-6 text-center">
            <div className="w-12 h-12 rounded-full bg-primary/10 flex items-center justify-center mx-auto mb-4">
              <Shield className="w-6 h-6 text-primary" />
            </div>
            <h2 className="text-xl font-bold text-foreground">Two-Factor Authentication</h2>
            <p className="text-sm text-muted-foreground mt-1">{email2fa}</p>
          </div>

          <Tabs value={twoFAMethod} onValueChange={(v) => setTwoFAMethod(v as "totp" | "email")} className="mb-4">
            <TabsList className="w-full">
              <TabsTrigger value="totp" className="flex-1">Authenticator App</TabsTrigger>
              <TabsTrigger value="email" className="flex-1">Email Code</TabsTrigger>
            </TabsList>
            <TabsContent value="totp" className="space-y-3 mt-4">
              <p className="text-sm text-muted-foreground">Enter the 6-digit code from your authenticator app.</p>
              <Input
                value={twoFACode}
                onChange={(e) => setTwoFACode(e.target.value.replace(/\D/g, "").slice(0, 6))}
                placeholder="000000"
                className="font-mono tracking-[0.4em] text-center text-lg"
                maxLength={6} autoFocus
              />
            </TabsContent>
            <TabsContent value="email" className="space-y-3 mt-4">
              {!emailSent ? (
                <Button variant="outline" className="w-full" onClick={sendEmailCode}>Send Code to {email2fa}</Button>
              ) : (
                <>
                  <p className="text-sm text-muted-foreground">Code sent. Enter it below.</p>
                  <Input value={twoFACode} onChange={(e) => setTwoFACode(e.target.value.replace(/\D/g, "").slice(0, 6))}
                    placeholder="000000" className="font-mono tracking-[0.4em] text-center text-lg" maxLength={6} autoFocus />
                </>
              )}
            </TabsContent>
          </Tabs>

          {twoFAError && <div className="text-xs text-destructive bg-destructive/10 border border-destructive/20 px-3 py-2 rounded-sm mb-3">{twoFAError}</div>}

          <Button className="w-full font-bold" onClick={verify2fa}
            disabled={twoFAPending || twoFACode.length !== 6 || (twoFAMethod === "email" && !emailSent)}>
            {twoFAPending ? "Verifying…" : "Verify"}
          </Button>
          <button className="text-xs text-muted-foreground hover:text-foreground mt-3 w-full text-center block" onClick={() => setRequires2fa(false)}>
            ← Back to login
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background flex">
      <div className="hidden lg:flex flex-1 bg-muted/30 border-r border-border flex-col items-center justify-center p-12">
        <div className="max-w-xs text-center">
          <div className="w-14 h-14 rounded-xl flex items-center justify-center mx-auto mb-6 shadow-lg"
            style={{ background: "linear-gradient(135deg,#7c3aed,#06b6d4)" }}>
            <Zap className="w-7 h-7 text-white" />
          </div>
          <h1 className="text-2xl font-black tracking-tight mb-2"
            style={{ background: "linear-gradient(135deg,#7c3aed,#06b6d4)", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>
            AYZEN WORKSPACE
          </h1>
          <p className="text-sm text-muted-foreground leading-relaxed mb-8">
            Web3 Airdrop Task Management — Earn XP. Complete Quests. Dominate the Leaderboard.
          </p>
          <div className="grid grid-cols-2 gap-3 text-left">
            {[
              ["🪂", "Airdrop Tasks", "Track every quest across all active airdrops"],
              ["🏆", "Tier System", "Rise from Bronze to Platinum with XP"],
              ["📊", "Leaderboard", "Compete with your community members"],
              ["🔐", "Account Vault", "Secure wallet and social storage"],
            ].map(([icon, title, desc]) => (
              <div key={title} className="bg-background border border-border p-3 rounded-lg">
                <div className="text-lg mb-1">{icon}</div>
                <div className="text-xs font-bold text-foreground">{title}</div>
                <div className="text-[11px] text-muted-foreground leading-snug">{desc}</div>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="flex-1 flex items-center justify-center p-8">
        <div className="w-full max-w-sm">
          <div className="mb-7">
            <div className="flex items-center gap-2 mb-5 lg:hidden">
              <div className="w-8 h-8 rounded-sm flex items-center justify-center"
                style={{ background: "linear-gradient(135deg,#7c3aed,#06b6d4)" }}>
                <Zap className="w-5 h-5 text-white" />
              </div>
              <span className="font-black"
                style={{ background: "linear-gradient(135deg,#7c3aed,#06b6d4)", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>
                AYZEN
              </span>
            </div>
            <h2 className="text-2xl font-bold text-foreground">Welcome back</h2>
            <p className="text-sm text-muted-foreground mt-1">Sign in to your AYZEN workspace</p>
          </div>

          {verified && (
            <div className="text-xs text-green-700 bg-green-50 dark:bg-green-950 dark:text-green-400 border border-green-200 dark:border-green-800 px-3 py-2 rounded-lg mb-4">
              ✓ Email verified! You can now sign in.
            </div>
          )}

          {/* Social Login Buttons */}
          {firebaseEnabled && (
            <div className="space-y-2 mb-5">
              <Button variant="outline" className="w-full h-10 flex items-center gap-2 font-medium"
                disabled={!!socialLoading}
                onClick={() => handleSocialLogin("google")}>
                {socialLoading === "google" ? (
                  <div className="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin" />
                ) : <GoogleIcon />}
                Continue with Google
              </Button>
              <Button variant="outline" className="w-full h-10 flex items-center gap-2 font-medium"
                disabled={!!socialLoading}
                onClick={() => handleSocialLogin("facebook")}>
                {socialLoading === "facebook" ? (
                  <div className="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin" />
                ) : <FacebookIcon />}
                Continue with Facebook
              </Button>
              <div className="flex items-center gap-3 my-4">
                <div className="flex-1 h-px bg-border" />
                <span className="text-xs text-muted-foreground font-medium">or continue with email</span>
                <div className="flex-1 h-px bg-border" />
              </div>
            </div>
          )}

          <Form {...form}>
            <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
              <FormField control={form.control} name="email" render={({ field }) => (
                <FormItem>
                  <FormLabel className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Email</FormLabel>
                  <FormControl>
                    <Input type="email" placeholder="you@example.com" autoComplete="email" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )} />
              <FormField control={form.control} name="password" render={({ field }) => (
                <FormItem>
                  <FormLabel className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Password</FormLabel>
                  <FormControl>
                    <div className="relative">
                      <Input
                        type={showPassword ? "text" : "password"}
                        placeholder="••••••••"
                        autoComplete="current-password"
                        className="pr-10"
                        {...field}
                      />
                      <button type="button" className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                        onClick={() => setShowPassword(!showPassword)}>
                        {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                      </button>
                    </div>
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )} />

              {errorMsg && (
                <div className="text-xs text-destructive bg-destructive/10 border border-destructive/20 px-3 py-2 rounded-lg">
                  {errorMsg}
                </div>
              )}

              <Button type="submit" className="w-full font-bold h-10" disabled={isPending}
                style={{ background: "linear-gradient(135deg,#7c3aed,#06b6d4)" }}>
                {isPending ? "Signing in…" : "Sign in"}
              </Button>
            </form>
          </Form>

          <p className="text-center text-xs text-muted-foreground mt-5">
            No account?{" "}
            <Link href="/register" className="text-primary font-medium hover:underline">
              Get an invite code
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
