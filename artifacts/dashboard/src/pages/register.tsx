import { useState, useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useLocation, useSearch } from "wouter";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form";
import { Link } from "wouter";
import { Zap, Eye, EyeOff } from "lucide-react";

const schema = z.object({
  email: z.string().email("Valid email required"),
  password: z.string().min(8, "Password must be at least 8 characters"),
  full_name: z.string().min(1, "Name required"),
  activation_code: z.string().min(1, "Activation code required"),
});

type FormData = z.infer<typeof schema>;

export default function Register() {
  const [, setLocation] = useLocation();
  const search = useSearch();
  const [isPending, setIsPending] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [showPassword, setShowPassword] = useState(false);

  // Auto-fill activation code from URL param
  const urlCode = new URLSearchParams(search).get("code") || "";

  const form = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: { email: "", password: "", full_name: "", activation_code: urlCode },
  });

  // Update code field if URL changes
  useEffect(() => {
    if (urlCode) form.setValue("activation_code", urlCode);
  }, [urlCode]);

  async function onSubmit(values: FormData) {
    setIsPending(true);
    setErrorMsg(null);
    try {
      const res = await fetch("/api/v1/auth/register", {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(values),
      });
      const data = await res.json();
      if (!res.ok) {
        const detail = data.detail || "Registration failed";
        const msgs: Record<string, string> = {
          activation_code_required: "An activation code is required to register.",
          invalid_activation_code: "Invalid activation code. Please check and try again.",
          activation_code_already_used: "This activation code has already been used.",
          activation_code_expired: "This activation code has expired.",
          email_already_registered: "This email is already registered.",
        };
        setErrorMsg(msgs[detail] ?? detail);
        return;
      }
      setLocation("/verify-email?email=" + encodeURIComponent(values.email));
    } catch {
      setErrorMsg("Network error. Please try again.");
    } finally {
      setIsPending(false);
    }
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
            Invite-only Web3 community platform. Complete airdrop quests, earn XP, and climb the leaderboard.
          </p>
          <div className="space-y-3 text-left">
            {[
              ["🔐", "Invite-Only Access", "Exclusive community with vetted members"],
              ["🪂", "Airdrop Quests", "Track tasks across all active Web3 airdrops"],
              ["💎", "XP & Tiers", "Earn Bronze → Platinum with your contributions"],
              ["🤖", "Telegram Bot", "Complete tasks and check rankings via Telegram"],
            ].map(([icon, title, desc]) => (
              <div key={title} className="flex gap-3 items-start">
                <span className="text-xl leading-none mt-0.5">{icon}</span>
                <div>
                  <div className="text-sm font-semibold text-foreground">{title}</div>
                  <div className="text-xs text-muted-foreground">{desc}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="flex-1 flex items-center justify-center p-8">
        <div className="w-full max-w-sm">
          <div className="mb-8">
            <div className="flex items-center gap-2 mb-6 lg:hidden">
              <div className="w-8 h-8 rounded-sm flex items-center justify-center"
                style={{ background: "linear-gradient(135deg,#7c3aed,#06b6d4)" }}>
                <Zap className="w-5 h-5 text-white" />
              </div>
              <span className="font-black" style={{ background: "linear-gradient(135deg,#7c3aed,#06b6d4)", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>AYZEN</span>
            </div>
            <h2 className="text-2xl font-bold text-foreground">Create account</h2>
            <p className="text-sm text-muted-foreground mt-1">
              {urlCode ? "🎉 You've been invited! Fill in your details below." : "Invite-only · Enter your activation code to join"}
            </p>
          </div>

          {urlCode && (
            <div className="mb-4 px-3 py-2 bg-green-500/10 border border-green-500/30 rounded-lg text-xs text-green-600 dark:text-green-400 flex items-center gap-2">
              <span>✓</span>
              <span>Invite code pre-filled from your invitation link</span>
            </div>
          )}

          <Form {...form}>
            <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
              <FormField control={form.control} name="full_name" render={({ field }) => (
                <FormItem>
                  <FormLabel className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Full Name</FormLabel>
                  <FormControl><Input placeholder="Your name" autoComplete="name" {...field} /></FormControl>
                  <FormMessage />
                </FormItem>
              )} />
              <FormField control={form.control} name="email" render={({ field }) => (
                <FormItem>
                  <FormLabel className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Email</FormLabel>
                  <FormControl><Input type="email" placeholder="you@example.com" autoComplete="email" {...field} /></FormControl>
                  <FormMessage />
                </FormItem>
              )} />
              <FormField control={form.control} name="password" render={({ field }) => (
                <FormItem>
                  <FormLabel className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Password</FormLabel>
                  <FormControl>
                    <div className="relative">
                      <Input type={showPassword ? "text" : "password"} placeholder="8+ characters" autoComplete="new-password" className="pr-10" {...field} />
                      <button type="button" className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                        onClick={() => setShowPassword(!showPassword)}>
                        {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                      </button>
                    </div>
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )} />
              <FormField control={form.control} name="activation_code" render={({ field }) => (
                <FormItem>
                  <FormLabel className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Activation Code</FormLabel>
                  <FormControl>
                    <Input
                      placeholder="AYZEN-XXXX-YYYY"
                      autoComplete="off"
                      className={`font-mono tracking-wider uppercase ${urlCode ? "border-green-500/40 bg-green-500/5" : ""}`}
                      {...field}
                      onChange={(e) => field.onChange(e.target.value.toUpperCase())}
                    />
                  </FormControl>
                  <FormMessage />
                  {!urlCode && (
                    <p className="text-[11px] text-muted-foreground mt-1">
                      Need a code? Get referred by an existing member or contact an admin.
                    </p>
                  )}
                </FormItem>
              )} />

              {errorMsg && (
                <div className="text-xs text-destructive bg-destructive/10 border border-destructive/20 px-3 py-2 rounded-sm">
                  {errorMsg}
                </div>
              )}

              <Button type="submit" className="w-full font-bold" disabled={isPending}
                style={{ background: "linear-gradient(135deg,#7c3aed,#06b6d4)" }}>
                {isPending ? "Creating account…" : "Create Account"}
              </Button>
            </form>
          </Form>

          <p className="text-center text-xs text-muted-foreground mt-6">
            Already have an account?{" "}
            <Link href="/login" className="text-primary font-medium hover:underline">Sign in</Link>
          </p>
        </div>
      </div>
    </div>
  );
}
