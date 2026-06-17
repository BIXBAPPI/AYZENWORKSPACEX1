import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useLocation } from "wouter";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form";
import { Link } from "wouter";
import { Zap } from "lucide-react";

const schema = z.object({
  email: z.string().email("Valid email required"),
  password: z.string().min(8, "Password must be at least 8 characters"),
  full_name: z.string().min(1, "Name required"),
  activation_code: z.string().min(1, "Activation code required"),
});

type FormData = z.infer<typeof schema>;

export default function Register() {
  const [, setLocation] = useLocation();
  const [isPending, setIsPending] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const form = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: { email: "", password: "", full_name: "", activation_code: "" },
  });

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
    <div className="min-h-screen bg-background flex items-center justify-center p-8">
      <div className="w-full max-w-sm">
        <div className="mb-8">
          <div className="flex items-center gap-2 mb-6">
            <div className="w-8 h-8 rounded-sm flex items-center justify-center" style={{ background: "linear-gradient(135deg,#7c3aed,#06b6d4)" }}>
              <Zap className="w-5 h-5 text-white" />
            </div>
            <span className="font-black text-foreground" style={{ background: "linear-gradient(135deg,#7c3aed,#06b6d4)", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>
              AYZEN
            </span>
          </div>
          <h2 className="text-2xl font-bold text-foreground">Create account</h2>
          <p className="text-sm text-muted-foreground mt-1">Invite-only · Enter your activation code to join</p>
        </div>

        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
            <FormField
              control={form.control}
              name="full_name"
              render={({ field }) => (
                <FormItem>
                  <FormLabel className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Full name</FormLabel>
                  <FormControl>
                    <Input placeholder="Your name" autoComplete="name" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
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
                    <Input type="password" placeholder="8+ characters" autoComplete="new-password" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="activation_code"
              render={({ field }) => (
                <FormItem>
                  <FormLabel className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Activation Code</FormLabel>
                  <FormControl>
                    <Input
                      placeholder="AYZEN-XXXX-YYYY"
                      autoComplete="off"
                      className="font-mono tracking-wider uppercase"
                      {...field}
                      onChange={(e) => field.onChange(e.target.value.toUpperCase())}
                    />
                  </FormControl>
                  <FormMessage />
                  <p className="text-[11px] text-muted-foreground mt-1">
                    Need a code? Ask an admin or get referred by an existing member.
                  </p>
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
              {isPending ? "Creating account..." : "Create account"}
            </Button>
          </form>
        </Form>

        <p className="text-center text-xs text-muted-foreground mt-6">
          Already have an account?{" "}
          <Link href="/login" className="text-primary font-medium hover:underline">
            Sign in
          </Link>
        </p>
      </div>
    </div>
  );
}
