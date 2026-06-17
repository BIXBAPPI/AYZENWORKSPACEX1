import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { RefreshCw, Fuel } from "lucide-react";

interface GasData {
  name: string;
  symbol: string;
  slow_gwei?: number;
  standard_gwei?: number;
  fast_gwei?: number;
  usd_slow?: number;
  usd_standard?: number;
  usd_fast?: number;
  color?: "green" | "yellow" | "red";
  error?: boolean;
  coming_soon?: boolean;
  updated_at?: string;
}

const CHAIN_ICONS: Record<string, string> = {
  "Ethereum": "https://raw.githubusercontent.com/trustwallet/assets/master/blockchains/ethereum/info/logo.png",
  "Arbitrum One": "https://raw.githubusercontent.com/trustwallet/assets/master/blockchains/arbitrum/info/logo.png",
  "Optimism": "https://raw.githubusercontent.com/trustwallet/assets/master/blockchains/optimism/info/logo.png",
  "Base": "https://raw.githubusercontent.com/trustwallet/assets/master/blockchains/base/info/logo.png",
  "Polygon": "https://raw.githubusercontent.com/trustwallet/assets/master/blockchains/polygon/info/logo.png",
  "BNB Chain": "https://raw.githubusercontent.com/trustwallet/assets/master/blockchains/binance/info/logo.png",
  "Avalanche": "https://raw.githubusercontent.com/trustwallet/assets/master/blockchains/avalanchec/info/logo.png",
  "Fantom": "https://raw.githubusercontent.com/trustwallet/assets/master/blockchains/fantom/info/logo.png",
};

const COLOR_MAP = {
  green: { bg: "bg-green-500/10", text: "text-green-400", dot: "bg-green-400" },
  yellow: { bg: "bg-yellow-500/10", text: "text-yellow-400", dot: "bg-yellow-400" },
  red: { bg: "bg-red-500/10", text: "text-red-400", dot: "bg-red-400" },
};

function GasCard({ net }: { net: GasData }) {
  const colorKey = net.color ?? "green";
  const colors = COLOR_MAP[colorKey] ?? COLOR_MAP.green;

  if (net.coming_soon) {
    return (
      <Card className="border-border opacity-50">
        <CardContent className="p-4">
          <div className="flex items-center gap-2 mb-3">
            <div className="w-8 h-8 rounded-full bg-muted flex items-center justify-center text-xs font-bold text-muted-foreground">?</div>
            <div>
              <p className="text-sm font-bold text-foreground">{net.name}</p>
              <p className="text-xs text-muted-foreground">{net.symbol}</p>
            </div>
          </div>
          <Badge variant="secondary" className="text-xs">Coming Soon</Badge>
        </CardContent>
      </Card>
    );
  }

  if (net.error) {
    return (
      <Card className="border-border opacity-60">
        <CardContent className="p-4">
          <div className="flex items-center gap-2 mb-3">
            <div className="w-8 h-8 rounded-full bg-muted flex items-center justify-center text-xs font-bold text-muted-foreground">⚠</div>
            <div>
              <p className="text-sm font-bold text-foreground">{net.name}</p>
              <p className="text-xs text-muted-foreground">{net.symbol}</p>
            </div>
          </div>
          <p className="text-xs text-muted-foreground">RPC unavailable</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="border-border hover:border-primary/30 transition-colors">
      <CardContent className="p-4">
        <div className="flex items-center gap-2 mb-3">
          {CHAIN_ICONS[net.name] ? (
            <img src={CHAIN_ICONS[net.name]} alt={net.name} className="w-8 h-8 rounded-full bg-muted" onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }} />
          ) : (
            <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center">
              <Fuel className="w-4 h-4 text-primary" />
            </div>
          )}
          <div className="flex-1 min-w-0">
            <p className="text-sm font-bold text-foreground truncate">{net.name}</p>
            <div className="flex items-center gap-1">
              <div className={`w-1.5 h-1.5 rounded-full ${colors.dot}`} />
              <p className="text-xs text-muted-foreground">{net.symbol}</p>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-3 gap-1 text-center">
          {[
            { label: "Slow", gwei: net.slow_gwei, usd: net.usd_slow },
            { label: "Std", gwei: net.standard_gwei, usd: net.usd_standard },
            { label: "Fast", gwei: net.fast_gwei, usd: net.usd_fast },
          ].map(({ label, gwei, usd }) => (
            <div key={label} className={`rounded p-1.5 ${label === "Std" ? colors.bg : "bg-muted/30"}`}>
              <p className="text-[10px] text-muted-foreground">{label}</p>
              <p className={`text-xs font-bold ${label === "Std" ? colors.text : "text-foreground"}`}>
                {gwei != null ? `${gwei}` : "—"}
              </p>
              <p className="text-[9px] text-muted-foreground">${usd?.toFixed(4) ?? "—"}</p>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

export default function GasTracker() {
  const [data, setData] = useState<GasData[]>([]);
  const [loading, setLoading] = useState(true);
  const [updatedAt, setUpdatedAt] = useState<string | null>(null);
  const [ttl, setTtl] = useState(30);

  const fetch = async () => {
    setLoading(true);
    try {
      const res = await window.fetch("/api/v1/gas/");
      const json = await res.json();
      setData(json.data ?? []);
      setTtl(json.ttl ?? 30);
      if ((json.data as GasData[])[0]?.updated_at) setUpdatedAt((json.data as GasData[])[0].updated_at ?? null);
    } catch { /* ignore */ } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetch();
    const id = setInterval(fetch, 30000);
    return () => clearInterval(id);
  }, []);

  return (
    <div className="p-4 md:p-6 max-w-[1400px]">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-black text-foreground flex items-center gap-2">
            <Fuel className="w-6 h-6 text-primary" /> Live Gas Tracker
          </h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            {updatedAt ? `Updated: ${new Date(updatedAt).toLocaleTimeString()}` : "Loading…"} · Auto-refresh every 30s
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={fetch} disabled={loading} className="gap-1.5">
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
          Refresh
        </Button>
      </div>

      <div className="flex gap-3 mb-4 flex-wrap">
        <Badge variant="outline" className="text-[10px] gap-1"><div className="w-2 h-2 rounded-full bg-green-400" />Low (&lt;5 gwei)</Badge>
        <Badge variant="outline" className="text-[10px] gap-1"><div className="w-2 h-2 rounded-full bg-yellow-400" />Moderate (5–30 gwei)</Badge>
        <Badge variant="outline" className="text-[10px] gap-1"><div className="w-2 h-2 rounded-full bg-red-400" />High (&gt;30 gwei)</Badge>
      </div>

      {loading && data.length === 0 ? (
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-3">
          {Array.from({ length: 15 }).map((_, i) => (
            <div key={i} className="h-36 bg-muted/20 rounded-lg animate-pulse" />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-3">
          {data.map((net) => <GasCard key={net.name} net={net} />)}
        </div>
      )}
    </div>
  );
}
