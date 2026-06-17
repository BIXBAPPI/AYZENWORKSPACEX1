import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { Code2, Database, Bot, Key, Eye, EyeOff, RefreshCw } from "lucide-react";

async function fetchDeveloperInfo() {
  const res = await fetch("/api/v1/system/developer", { credentials: "include" });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export default function DeveloperPage() {
  const [revealed, setRevealed] = useState<Record<string, boolean>>({});
  const { data, isLoading, refetch, isFetching } = useQuery({
    queryKey: ["system-developer"],
    queryFn: fetchDeveloperInfo,
    retry: false,
  });

  const toggleReveal = (key: string) =>
    setRevealed((prev) => ({ ...prev, [key]: !prev[key] }));

  if (isLoading) {
    return (
      <div className="p-4 md:p-6 space-y-4">
        <Skeleton className="h-8 w-48" />
        {[1, 2, 3].map((i) => <Skeleton key={i} className="h-32" />)}
      </div>
    );
  }

  return (
    <div className="p-4 md:p-6 max-w-[1200px] space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl md:text-2xl font-black text-foreground tracking-tight">Developer</h1>
          <p className="text-sm text-muted-foreground mt-0.5">System configuration — admin only</p>
        </div>
        <Button variant="outline" size="sm" onClick={() => refetch()} disabled={isFetching}>
          <RefreshCw className={`w-3.5 h-3.5 mr-1.5 ${isFetching ? "animate-spin" : ""}`} />
          Refresh
        </Button>
      </div>

      {/* Environment Variables */}
      <Card className="border-border">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-2">
            <Key className="w-4 h-4" /> Environment Variables
          </CardTitle>
        </CardHeader>
        <CardContent className="pt-0">
          <div className="divide-y divide-border">
            {(data?.env_vars ?? []).map((ev: any) => (
              <div key={ev.key} className="flex items-center gap-3 py-2.5">
                <code className="text-xs font-mono text-foreground w-56 shrink-0 truncate">{ev.key}</code>
                <div className="flex-1 font-mono text-xs text-muted-foreground truncate">
                  {ev.sensitive && !revealed[ev.key]
                    ? ev.is_set ? "●●●●●●●●" : <span className="text-destructive/70">(not set)</span>
                    : <span className={ev.is_set ? "text-foreground" : "text-destructive/70"}>{ev.value}</span>
                  }
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <Badge variant={ev.is_set ? "secondary" : "outline"} className={`text-[10px] px-1.5 py-0 ${ev.is_set ? "" : "border-destructive/40 text-destructive/70"}`}>
                    {ev.is_set ? "SET" : "MISSING"}
                  </Badge>
                  {ev.sensitive && ev.is_set && (
                    <button onClick={() => toggleReveal(ev.key)} className="text-muted-foreground hover:text-foreground transition-colors">
                      {revealed[ev.key] ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Python Runtime */}
        <Card className="border-border">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-2">
              <Code2 className="w-4 h-4" /> Python Runtime
            </CardTitle>
          </CardHeader>
          <CardContent className="pt-0 space-y-2">
            <InfoRow label="Version" value={data?.python?.version?.split(" ")[0] ?? "—"} />
            <InfoRow label="Venv Path" value={data?.python?.venv_path ?? "—"} mono />
          </CardContent>
        </Card>

        {/* Telegram */}
        <Card className="border-border">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-2">
              <Bot className="w-4 h-4" /> Telegram Bot
            </CardTitle>
          </CardHeader>
          <CardContent className="pt-0 space-y-2">
            <InfoRow label="Bot Token" value={data?.telegram?.bot_token_set ? "Configured" : "Not set"} status={data?.telegram?.bot_token_set} />
            <InfoRow label="Username" value={data?.telegram?.bot_username ?? "—"} />
            <InfoRow label="Webhook Secret" value={data?.telegram?.webhook_secret_set ? "Configured" : "Not set"} status={data?.telegram?.webhook_secret_set} />
          </CardContent>
        </Card>
      </div>

      {/* DB Table Counts */}
      <Card className="border-border">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-2">
            <Database className="w-4 h-4" /> Database Tables
            <Badge variant={data?.db?.connected ? "secondary" : "destructive"} className="text-[10px] px-1.5 py-0 ml-auto">
              {data?.db?.connected ? "CONNECTED" : "DISCONNECTED"}
            </Badge>
          </CardTitle>
        </CardHeader>
        <CardContent className="pt-0">
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
            {(data?.db?.table_counts ?? []).map((t: any) => (
              <div key={t.table} className="bg-muted/40 rounded-sm px-3 py-2">
                <div className="text-[10px] font-mono text-muted-foreground uppercase tracking-wider">{t.table}</div>
                <div className="text-lg font-black text-foreground mt-0.5">
                  {t.rows < 0 ? <span className="text-destructive/60 text-sm">ERR</span> : t.rows.toLocaleString()}
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

function InfoRow({ label, value, mono, status }: { label: string; value: string; mono?: boolean; status?: boolean }) {
  return (
    <div className="flex items-center justify-between gap-2">
      <span className="text-xs text-muted-foreground shrink-0">{label}</span>
      <span className={`text-xs truncate ${mono ? "font-mono" : "font-medium"} ${status === false ? "text-destructive/70" : status === true ? "text-green-500" : "text-foreground"}`}>
        {value}
      </span>
    </div>
  );
}
