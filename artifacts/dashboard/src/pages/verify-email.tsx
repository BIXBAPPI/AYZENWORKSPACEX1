import { useState } from "react";
import { useLocation, useSearch } from "wouter";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Zap, Mail } from "lucide-react";

export default function VerifyEmail() {
  const [, setLocation] = useLocation();
  const search = useSearch();
  const params = new URLSearchParams(search);
  const email = params.get("email") ?? "";

  const [code, setCode] = useState("");
  const [isPending, setIsPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!code.trim()) return;
    setIsPending(true);
    setError(null);
    try {
      const res = await fetch("/api/auth/verify-email", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, code: code.trim() }),
      });
      const data = await res.json();
      if (!res.ok) {
        const msg =
          data?.detail === "invalid_code" ? "Invalid code. Please check and try again." :
          data?.detail === "code_expired" ? "Code has expired. Please register again." :
          data?.detail === "code_already_used" ? "Code already used. Please log in." :
          "Verification failed. Please try again.";
        setError(msg);
        return;
      }
      setLocation("/login?verified=1");
    } catch {
      setError("Network error. Please try again.");
    } finally {
      setIsPending(false);
    }
  }

  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-8">
      <div className="w-full max-w-sm">
        <div className="mb-8">
          <div className="flex items-center gap-2 mb-6">
            <div className="w-8 h-8 bg-primary rounded-sm flex items-center justify-center">
              <Zap className="w-5 h-5 text-primary-foreground" />
            </div>
            <span className="font-black text-foreground">AYZEN</span>
          </div>
          <div className="w-12 h-12 bg-primary/10 rounded-sm flex items-center justify-center mb-4">
            <Mail className="w-6 h-6 text-primary" />
          </div>
          <h2 className="text-2xl font-bold text-foreground">Check your email</h2>
          <p className="text-sm text-muted-foreground mt-1">
            We sent a 6-digit code to{" "}
            <span className="font-semibold text-foreground">{email}</span>
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="text-xs font-semibold uppercase tracking-wide text-muted-foreground block mb-1.5">
              Verification code
            </label>
            <Input
              value={code}
              onChange={(e) => setCode(e.target.value)}
              placeholder="000000"
              maxLength={6}
              inputMode="numeric"
              autoComplete="one-time-code"
              className="text-center text-xl font-bold tracking-widest"
              autoFocus
            />
          </div>

          {error && (
            <div className="text-xs text-destructive bg-destructive/10 border border-destructive/20 px-3 py-2 rounded-sm">
              {error}
            </div>
          )}

          <Button type="submit" className="w-full font-bold" disabled={isPending || code.length < 6}>
            {isPending ? "Verifying..." : "Verify email"}
          </Button>
        </form>

        <p className="text-center text-xs text-muted-foreground mt-6">
          Wrong email?{" "}
          <a href="/register" className="text-primary font-medium hover:underline">
            Register again
          </a>
        </p>
      </div>
    </div>
  );
}
