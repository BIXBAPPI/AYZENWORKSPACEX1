import { useQuery } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { Activity, Database, Server, Clock, Cpu, RefreshCw, CheckCircle, XCircle } from "lucide-react";

async function fetchTelemetry() {
  const res = await fetch("/api/v1/system/health/telemetry", { credentials: "include" });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

function StatusDot({ ok }: { ok: boolean }) {
  return (
    <span className={`inline-block w-2 h-2 rounded-full shrink-0 ${ok ? "bg-green-500" : "bg-destructive"}`} />
  );
}

function formatUptime(seconds: number): string {
  const d = Math.floor(seconds / 86400);
  const h = Math.floor((seconds % 86400) / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = seconds % 60;
  if (d > 0) return `${d}d ${h}h ${m}m`;
  if (h > 0) return `${h}h ${m}m ${s}s`;
  if (m > 0) return `${m}m ${s}s`;
  return `${s}s`;
}

export default function HealthPage() {
  const { data, isLoading, refetch, isFetching, dataUpdatedAt } = useQuery({
    queryKey: ["system-health"],
    queryFn: fetchTelemetry,
    refetchInterval: 30_000,
    retry: false,
  });

  if (isLoading) {
    return (
      <div className="p-4 md:p-6 space-y-4">
        <Skeleton className="h-8 w-48" />
        {[1, 2, 3].map((i) => <Skeleton key={i} className="h-32" />)}
      </div>
    );
  }

  const dbOk = data?.db?.connected ?? false;
  const uptime = data?.server?.uptime_seconds ?? 0;
  const latency = data?.db?.latency_ms ?? -1;
  const lastUpdated = dataUpdatedAt ? new Date(dataUpdatedAt).toLocaleTimeString() : "—";

  return (
    <div className="p-4 md:p-6 max-w-[1200px] space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl md:text-2xl font-black text-foreground tracking-tight">Health</h1>
          <p className="text-sm text-muted-foreground mt-0.5">System telemetry — refreshes every 30s · last: {lastUpdated}</p>
        </div>
        <Button variant="outline" size="sm" onClick={() => refetch()} disabled={isFetching}>
          <RefreshCw className={`w-3.5 h-3.5 mr-1.5 ${isFetching ? "animate-spin" : ""}`} />
          Refresh
        </Button>
      </div>

      {/* Status cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <StatusCard
          title="API Server"
          value="Running"
          icon={Server}
          ok={true}
          sub={`Port ${data?.ports?.node_api ?? 8080}`}
        />
        <StatusCard
          title="Python API"
          value="Running"
          icon={Activity}
          ok={true}
          sub={`Port ${data?.ports?.python_api ?? 8000}`}
        />
        <StatusCard
          title="Database"
          value={dbOk ? "Connected" : "Down"}
          icon={Database}
          ok={dbOk}
          sub={latency >= 0 ? `${latency}ms latency` : "no connection"}
        />
        <StatusCard
          title="Uptime"
          value={formatUptime(uptime)}
          icon={Clock}
          ok={uptime > 0}
          sub={data?.server?.node_env ?? "—"}
        />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Server Info */}
        <Card className="border-border">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-2">
              <Cpu className="w-4 h-4" /> Server Info
            </CardTitle>
          </CardHeader>
          <CardContent className="pt-0 space-y-2.5">
            <InfoRow label="Python" value={data?.server?.python_version?.split(" ")[0] ?? "—"} />
            <InfoRow label="Platform" value={`${data?.server?.platform ?? "—"} (${data?.server?.arch ?? "—"})`} />
            <InfoRow label="Environment" value={data?.server?.node_env ?? "—"} />
            <InfoRow label="Memory RSS" value={data?.memory?.rss_mb ? `${data.memory.rss_mb} MB` : "—"} />
          </CardContent>
        </Card>

        {/* Port Map */}
        <Card className="border-border">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-2">
              <Activity className="w-4 h-4" /> Services
            </CardTitle>
          </CardHeader>
          <CardContent className="pt-0 space-y-2.5">
            <ServiceRow name="Node.js API Proxy" port={data?.ports?.node_api ?? 8080} ok={true} />
            <ServiceRow name="Python FastAPI" port={data?.ports?.python_api ?? 8000} ok={true} />
            <ServiceRow name="Dashboard (Vite)" port={5000} ok={true} />
          </CardContent>
        </Card>
      </div>

      {/* DB Table Counts */}
      <Card className="border-border">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-2">
            <Database className="w-4 h-4" /> Database Tables
            <Badge variant={dbOk ? "secondary" : "destructive"} className="text-[10px] px-1.5 py-0 ml-auto">
              {dbOk ? `${latency}ms` : "OFFLINE"}
            </Badge>
          </CardTitle>
        </CardHeader>
        <CardContent className="pt-0">
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
            {(data?.db?.table_counts ?? []).map((t: any) => (
              <div key={t.table} className="bg-muted/40 rounded-sm px-3 py-2 flex items-center justify-between gap-2">
                <div>
                  <div className="text-[10px] font-mono text-muted-foreground uppercase tracking-wider">{t.table}</div>
                  <div className="text-lg font-black text-foreground mt-0.5">
                    {t.rows < 0 ? <span className="text-destructive/60 text-sm">ERR</span> : t.rows.toLocaleString()}
                  </div>
                </div>
                {t.rows >= 0 ? <CheckCircle className="w-3 h-3 text-green-500/60 shrink-0" /> : <XCircle className="w-3 h-3 text-destructive/60 shrink-0" />}
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Routes */}
      {data?.routes?.length > 0 && (
        <Card className="border-border">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-2">
              <Activity className="w-4 h-4" /> API Routes
              <Badge variant="outline" className="ml-auto text-[10px] px-1.5 py-0">{data.routes.length}</Badge>
            </CardTitle>
          </CardHeader>
          <CardContent className="pt-0 max-h-72 overflow-y-auto">
            <div className="space-y-0.5">
              {data.routes.map((r: any, i: number) => (
                <div key={i} className="flex items-center gap-2.5 py-1">
                  <Badge variant="outline" className={`text-[9px] px-1 py-0 font-mono w-12 text-center shrink-0 ${r.method === "GET" ? "border-blue-500/40 text-blue-500" : r.method === "POST" ? "border-green-500/40 text-green-500" : r.method === "DELETE" ? "border-destructive/40 text-destructive" : "border-primary/40 text-primary"}`}>
                    {r.method}
                  </Badge>
                  <code className="text-xs font-mono text-muted-foreground truncate">{r.path}</code>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

function StatusCard({ title, value, icon: Icon, ok, sub }: { title: string; value: string; icon: any; ok: boolean; sub: string }) {
  return (
    <Card className="border-border">
      <CardContent className="p-4">
        <div className="flex items-start justify-between mb-2">
          <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">{title}</p>
          <div className={`w-7 h-7 rounded-sm flex items-center justify-center ${ok ? "bg-green-500/10" : "bg-destructive/10"}`}>
            <Icon className={`w-3.5 h-3.5 ${ok ? "text-green-500" : "text-destructive"}`} />
          </div>
        </div>
        <div className="flex items-center gap-1.5">
          <StatusDot ok={ok} />
          <p className="text-base font-black text-foreground">{value}</p>
        </div>
        <p className="text-[10px] text-muted-foreground mt-1 font-mono">{sub}</p>
      </CardContent>
    </Card>
  );
}

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-2">
      <span className="text-xs text-muted-foreground shrink-0">{label}</span>
      <span className="text-xs font-medium text-foreground font-mono">{value}</span>
    </div>
  );
}

function ServiceRow({ name, port, ok }: { name: string; port: number; ok: boolean }) {
  return (
    <div className="flex items-center gap-2">
      <StatusDot ok={ok} />
      <span className="text-xs text-foreground flex-1">{name}</span>
      <code className="text-[10px] font-mono text-muted-foreground">:{port}</code>
    </div>
  );
}
