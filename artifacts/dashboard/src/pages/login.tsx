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

const schema = z.object({
  email: z.string().email("Valid email required"),
  password: z.string().min(1, "Password required"),
});

type FormData = z.infer<typeof schema>;

export default function Login() {
  const [, setLocation] = useLocation();
  const queryClient = useQueryClient();
  const search = useSearch();
  const verified = new URLSearchParams(search).get("verified") === "1";

  const [isPending, setIsPending] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [showPassword, setShowPassword] = useState(false);

  // 2FA state
  const [requires2fa, setRequires2fa] = useState(false);
  const [email2fa, setEmail2fa] = useState("");
  const [twoFACode, setTwoFACode] = useState("");
  const [twoFAMethod, setTwoFAMethod] = useState<"totp" | "email">("totp");
  const [twoFAPending, setTwoFAPending] = useState(false);
  const [twoFAError, setTwoFAError] = useState<string | null>(null);
  const [emailSent, setEmailSent] = useState(false);

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
      if (!res.ok) {
        setTwoFAError(data.detail ?? "Invalid code. Try again.");
        return;
      }
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
                maxLength={6}
                autoFocus
              />
            </TabsContent>
            <TabsContent value="email" className="space-y-3 mt-4">
              {!emailSent ? (
                <Button variant="outline" className="w-full" onClick={sendEmailCode}>
                  Send Code to {email2fa}
                </Button>
              ) : (
                <>
                  <p className="text-sm text-muted-foreground">Code sent to your email. Enter it below.</p>
                  <Input
                    value={twoFACode}
                    onChange={(e) => setTwoFACode(e.target.value.replace(/\D/g, "").slice(0, 6))}
                    placeholder="000000"
                    className="font-mono tracking-[0.4em] text-center text-lg"
                    maxLength={6}
                    autoFocus
                  />
                </>
              )}
            </TabsContent>
          </Tabs>

          {twoFAError && (
            <div className="text-xs text-destructive bg-destructive/10 border border-destructive/20 px-3 py-2 rounded-sm mb-3">
              {twoFAError}
            </div>
          )}

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
      <div className="hidden lg:flex flex-1 bg-primary/5 border-r border-border flex-col items-center justify-center p-12">
        <div className="max-w-xs text-center">
          <div className="w-14 h-14 rounded-sm flex items-center justify-center mx-auto mb-6" style={{ background: "linear-gradient(135deg,#7c3aed,#06b6d4)" }}>
            <Zap className="w-8 h-8 text-white" />
          </div>
          <h1 className="text-3xl font-black tracking-tight mb-3" style={{ background: "linear-gradient(135deg,#7c3aed,#06b6d4)", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>
            AYZEN
          </h1>
          <p className="text-sm text-muted-foreground leading-relaxed">
            Web3 Airdrop Task Management — Earn XP, complete quests, and dominate the leaderboard.
          </p>
          <div className="mt-8 grid grid-cols-2 gap-3 text-left">
            {[
              ["🪂 Airdrop Tasks", "Track every quest across all active airdrops"],
              ["🏆 Tier System", "Rise from Bronze to Platinum with XP"],
              ["📊 Leaderboard", "Compete with your community members"],
              ["🔐 Account Vault", "Secure wallet and social storage"],
            ].map(([title, desc]) => (
              <div key={title} className="bg-background border border-border p-3 rounded-sm">
                <div className="text-xs font-bold text-primary mb-1">{title}</div>
                <div className="text-[11px] text-muted-foreground leading-snug">{desc}</div>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="flex-1 flex items-center justify-center p-8">
        <div className="w-full max-w-sm">
          <div className="mb-8">
            <div className="flex items-center gap-2 mb-6 lg:hidden">
              <div className="w-8 h-8 rounded-sm flex items-center justify-center" style={{ background: "linear-gradient(135deg,#7c3aed,#06b6d4)" }}>
                <Zap className="w-5 h-5 text-white" />
              </div>
              <span className="font-black" style={{ background: "linear-gradient(135deg,#7c3aed,#06b6d4)", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>AYZEN</span>
            </div>
            <h2 className="text-2xl font-bold text-foreground">Sign in</h2>
            <p className="text-sm text-muted-foreground mt-1">Enter your credentials to access the dashboard</p>
          </div>

          {verified && (
            <div className="text-xs text-green-700 bg-green-50 dark:bg-green-950 dark:text-green-400 border border-green-200 dark:border-green-800 px-3 py-2 rounded-sm mb-4">
              ✓ Email verified! Please log in.
            </div>
          )}

          <Form {...form}>
            <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
              <FormField
                control={form.control}
                name="email"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Email</FormLabel>
                    <FormControl>
                      <Input type="email" placeholder="you@example.com" autoComplete="email" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="password"
                render={({ field }) => (
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
                        <button
                          type="button"
                          className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                          onClick={() => setShowPassword(!showPassword)}
                        >
                          {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                        </button>
                      </div>
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              {errorMsg && (
                <div className="text-xs text-destructive bg-destructive/10 border border-destructive/20 px-3 py-2 rounded-sm">
                  {errorMsg}
                </div>
              )}

              <Button type="submit" className="w-full font-bold" disabled={isPending}
                style={{ background: "linear-gradient(135deg,#7c3aed,#06b6d4)" }}>
                {isPending ? "Signing in..." : "Sign in"}
              </Button>
            </form>
          </Form>

          <p className="text-center text-xs text-muted-foreground mt-6">
            No account?{" "}
            <Link href="/register" className="text-primary font-medium hover:underline">
              Get invite code
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
