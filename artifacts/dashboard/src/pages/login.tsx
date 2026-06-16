import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useLogin } from "@workspace/api-client-react";
import { useLocation, useSearch } from "wouter";
import { useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form";
import { Link } from "wouter";
import { Zap } from "lucide-react";

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

  const form = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: { email: "", password: "" },
  });

  const { mutate, isPending, error } = useLogin({
    mutation: {
      onSuccess: () => {
        queryClient.invalidateQueries();
        setLocation("/dashboard");
      },
    },
  });

  function onSubmit(values: FormData) {
    mutate({ data: values });
  }

  return (
    <div className="min-h-screen bg-background flex">
      <div className="hidden lg:flex flex-1 bg-primary/5 border-r border-border flex-col items-center justify-center p-12">
        <div className="max-w-xs text-center">
          <div className="w-14 h-14 bg-primary rounded-sm flex items-center justify-center mx-auto mb-6">
            <Zap className="w-8 h-8 text-primary-foreground" />
          </div>
          <h1 className="text-3xl font-black text-foreground tracking-tight mb-3">AYZEN</h1>
          <p className="text-sm text-muted-foreground leading-relaxed">
            Mission control for crypto communities. Manage tasks, track progress, and coordinate your Telegram team from one place.
          </p>
          <div className="mt-8 grid grid-cols-2 gap-3 text-left">
            {[
              ["Task Tracking", "Assign and monitor community tasks with real-time status"],
              ["Leaderboards", "Rank members by completion and reward top performers"],
              ["Broadcasts", "Send targeted messages to your entire Telegram community"],
              ["Analytics", "Daily snapshots and trend charts for your operations"],
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
              <div className="w-8 h-8 bg-primary rounded-sm flex items-center justify-center">
                <Zap className="w-5 h-5 text-primary-foreground" />
              </div>
              <span className="font-black text-foreground">AYZEN</span>
            </div>
            <h2 className="text-2xl font-bold text-foreground">Sign in</h2>
            <p className="text-sm text-muted-foreground mt-1">Enter your credentials to access the dashboard</p>
          </div>

          {verified && (
            <div className="text-xs text-green-700 bg-green-50 border border-green-200 px-3 py-2 rounded-sm mb-4">
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
                      <Input type="password" placeholder="••••••••" autoComplete="current-password" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              {error && (
                <div className="text-xs text-destructive bg-destructive/10 border border-destructive/20 px-3 py-2 rounded-sm">
                  Invalid email or password
                </div>
              )}

              <Button type="submit" className="w-full font-bold" disabled={isPending}>
                {isPending ? "Signing in..." : "Sign in"}
              </Button>
            </form>
          </Form>

          <p className="text-center text-xs text-muted-foreground mt-6">
            No account?{" "}
            <Link href="/register" className="text-primary font-medium hover:underline">
              Create one
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
