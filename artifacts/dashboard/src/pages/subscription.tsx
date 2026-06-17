import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useToast } from "@/hooks/use-toast";
import { useAuth } from "@/lib/auth";
import {
  Crown, Zap, Check, ExternalLink, RefreshCw, Star, Sparkles,
} from "lucide-react";

const api = (path: string, opts?: RequestInit) =>
  fetch(`/api/v1${path}`, { credentials: "include", ...opts });

const TIERS = [
  {
    id: "free",
    name: "Free",
    price: 0,
    label: "Current",
    icon: Zap,
    color: "border-border",
    headerColor: "bg-muted/30",
    features: [
      "2 vault accounts",
      "3 projects",
      "10 airdrop tools",
      "1 email config",
      "Basic analytics",
    ],
    missing: ["Unlimited accounts", "All 30 tools", "Tutorial access", "Priority support"],
  },
  {
    id: "pro",
    name: "Pro",
    price: 3,
    label: "⭐ Popular",
    icon: Star,
    color: "border-primary/60",
    headerColor: "bg-primary/10",
    features: [
      "Unlimited vault accounts",
      "Unlimited projects",
      "All 30 airdrop tools",
      "5 email configs",
      "Advanced analytics",
      "Full tutorial access",
      "Priority support",
    ],
    missing: [],
  },
  {
    id: "elite",
    name: "Elite",
    price: 9,
    label: "👑 Best Value",
    icon: Crown,
    color: "border-yellow-500/50",
    headerColor: "bg-yellow-500/10",
    features: [
      "Everything in Pro",
      "Unlimited email configs",
      "API access",
      "White-label dashboard",
      "1-on-1 support",
      "Early access to new tools",
      "Custom integrations",
    ],
    missing: [],
  },
];

export default function SubscriptionPage() {
  const { user } = useAuth();
  const { toast } = useToast();
  const [sub, setSub] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [ordering, setOrdering] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      const r = await api("/subscriptions/current");
      if (r.ok) setSub(await r.json());
      setLoading(false);
    })();
  }, []);

  const subscribe = async (tier: string) => {
    setOrdering(tier);
    const r = await api("/subscriptions/create-order", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ tier }),
    });
    const data = await r.json();
    setOrdering(null);
    if (!r.ok) {
      toast({ title: "Error", description: data.detail, variant: "destructive" });
      return;
    }
    if (data.demo_mode) {
      toast({
        title: "Demo mode",
        description: "Set COINGATE_API_TOKEN and BASE_URL to enable crypto payments.",
      });
      return;
    }
    if (data.payment_url) {
      window.open(data.payment_url, "_blank");
    }
  };

  const currentTier = sub?.tier || user?.subscription_tier || "free";

  return (
    <div className="p-6 space-y-8 max-w-4xl mx-auto">
      <div>
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <Crown className="w-6 h-6 text-yellow-400" /> Subscription
        </h1>
        <p className="text-muted-foreground text-sm mt-0.5">Upgrade to unlock unlimited accounts, tools, and more</p>
      </div>

      {!loading && sub && (
        <div className="flex items-center gap-4 p-4 bg-primary/5 border border-primary/20 rounded-lg">
          <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center">
            <Sparkles className="w-5 h-5 text-primary" />
          </div>
          <div>
            <div className="font-semibold capitalize">
              Current Plan: <span className="text-primary">{currentTier}</span>
            </div>
            {sub.expires_at ? (
              <div className="text-xs text-muted-foreground">
                Renews: {new Date(sub.expires_at).toLocaleDateString()}
              </div>
            ) : (
              <div className="text-xs text-muted-foreground">No expiry set</div>
            )}
          </div>
          {sub.subscription && (
            <Badge className={`ml-auto ${sub.subscription.status === "paid" ? "bg-green-500/10 text-green-400 border-green-500/30" : "bg-yellow-500/10 text-yellow-400 border-yellow-500/30"}`}>
              {sub.subscription.status}
            </Badge>
          )}
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {TIERS.map((tier) => {
          const isCurrent = currentTier === tier.id;
          return (
            <Card key={tier.id} className={`border-2 ${tier.color} relative overflow-hidden`}>
              {tier.id === "pro" && (
                <div className="absolute top-0 left-0 right-0 h-0.5" style={{ background: "linear-gradient(90deg,#7c3aed,#06b6d4)" }} />
              )}
              <CardHeader className={`${tier.headerColor} pb-3`}>
                <div className="flex items-center justify-between">
                  <CardTitle className="flex items-center gap-2 text-base">
                    <tier.icon className={`w-5 h-5 ${tier.id === "elite" ? "text-yellow-400" : tier.id === "pro" ? "text-primary" : "text-muted-foreground"}`} />
                    {tier.name}
                  </CardTitle>
                  <Badge variant="outline" className="text-[10px]">{tier.label}</Badge>
                </div>
                <div className="mt-2">
                  {tier.price === 0 ? (
                    <span className="text-2xl font-bold">Free</span>
                  ) : (
                    <div>
                      <span className="text-3xl font-bold">${tier.price}</span>
                      <span className="text-muted-foreground text-sm">/month</span>
                    </div>
                  )}
                </div>
              </CardHeader>
              <CardContent className="pt-4 space-y-4">
                <ul className="space-y-2">
                  {tier.features.map((f) => (
                    <li key={f} className="flex items-start gap-2 text-sm">
                      <Check className="w-4 h-4 text-green-400 shrink-0 mt-0.5" />
                      <span>{f}</span>
                    </li>
                  ))}
                  {tier.missing.map((f) => (
                    <li key={f} className="flex items-start gap-2 text-sm text-muted-foreground/50 line-through">
                      <span className="w-4 h-4 shrink-0 mt-0.5 text-center text-muted-foreground/30">✕</span>
                      <span>{f}</span>
                    </li>
                  ))}
                </ul>

                {isCurrent ? (
                  <Button className="w-full" variant="outline" disabled>
                    Current Plan
                  </Button>
                ) : tier.price === 0 ? (
                  <Button className="w-full" variant="ghost" disabled>
                    Free Forever
                  </Button>
                ) : (
                  <Button
                    className="w-full"
                    onClick={() => subscribe(tier.id)}
                    disabled={!!ordering}
                    style={tier.id === "pro" ? { background: "linear-gradient(135deg,#7c3aed,#06b6d4)" } : {}}
                  >
                    {ordering === tier.id ? (
                      <RefreshCw className="w-4 h-4 mr-1 animate-spin" />
                    ) : (
                      <ExternalLink className="w-4 h-4 mr-1" />
                    )}
                    Subscribe with Crypto
                  </Button>
                )}
              </CardContent>
            </Card>
          );
        })}
      </div>

      <div className="text-center space-y-2">
        <div className="flex items-center justify-center gap-4 text-xs text-muted-foreground">
          <span>💰 Pay with BTC, ETH, USDT, and 70+ cryptos</span>
          <span>🔒 Secured by CoinGate</span>
          <span>⚡ Instant activation</span>
        </div>
        <p className="text-[11px] text-muted-foreground/60">
          Payments powered by CoinGate. Subscriptions auto-expire after 30 days. Contact support to cancel.
        </p>
      </div>
    </div>
  );
}
