import { useGetDashboardSummary, getGetDashboardSummaryQueryKey, useListAnalyticsSnapshots, getListAnalyticsSnapshotsQueryKey } from "@workspace/api-client-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";
import { CheckSquare, Users, AlertTriangle, TrendingUp, Trophy, Activity } from "lucide-react";
import { format } from "date-fns";

function KpiCard({ title, value, icon: Icon, trend, color }: { title: string; value: string | number; icon: any; trend?: string; color?: string }) {
  return (
    <Card className="border-border">
      <CardContent className="p-5">
        <div className="flex items-start justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2">{title}</p>
            <p className="text-3xl font-black text-foreground">{value}</p>
            {trend && <p className="text-xs text-muted-foreground mt-1">{trend}</p>}
          </div>
          <div className={`w-10 h-10 rounded-sm flex items-center justify-center ${color ?? "bg-primary/10"}`}>
            <Icon className="w-5 h-5 text-primary" />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

export default function DashboardPage() {
  const { data: summary, isLoading } = useGetDashboardSummary({
    query: { queryKey: getGetDashboardSummaryQueryKey() },
  });

  const { data: snapshots } = useListAnalyticsSnapshots(
    { days: 30 },
    { query: { queryKey: getListAnalyticsSnapshotsQueryKey({ days: 30 }) } }
  );

  const chartData = (snapshots ?? []).map((s: any) => ({
    date: format(new Date(s.snapshot_date), "MMM d"),
    completed: s.completed_tasks,
    new: s.new_tasks,
  }));

  if (isLoading) {
    return (
      <div className="p-6">
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
          {Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-28" />)}
        </div>
        <Skeleton className="h-64" />
      </div>
    );
  }

  const completionRate = summary?.completion_rate ?? 0;

  return (
    <div className="p-6 max-w-[1400px]">
      <div className="mb-6">
        <h1 className="text-2xl font-black text-foreground tracking-tight">Dashboard</h1>
        <p className="text-sm text-muted-foreground mt-0.5">Operations overview</p>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <KpiCard title="Total Tasks" value={summary?.total_tasks ?? 0} icon={CheckSquare} trend={`${completionRate}% completion rate`} />
        <KpiCard title="Completed" value={summary?.completed_tasks ?? 0} icon={TrendingUp} color="bg-secondary/20" />
        <KpiCard title="Overdue" value={summary?.overdue_tasks ?? 0} icon={AlertTriangle} color="bg-destructive/10" />
        <KpiCard title="Active Members" value={summary?.active_members ?? 0} icon={Users} color="bg-accent" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <Card className="lg:col-span-2 border-border">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-2">
              <Activity className="w-4 h-4" /> Completions (30 days)
            </CardTitle>
          </CardHeader>
          <CardContent className="pt-0">
            {chartData.length === 0 ? (
              <div className="h-48 flex items-center justify-center text-sm text-muted-foreground">No data yet</div>
            ) : (
              <ResponsiveContainer width="100%" height={200}>
                <AreaChart data={chartData} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
                  <defs>
                    <linearGradient id="colorCompleted" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="hsl(260 100% 60%)" stopOpacity={0.3} />
                      <stop offset="95%" stopColor="hsl(260 100% 60%)" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <XAxis dataKey="date" tick={{ fontSize: 10, fill: "hsl(240 5% 40%)" }} tickLine={false} axisLine={false} interval={4} />
                  <YAxis tick={{ fontSize: 10, fill: "hsl(240 5% 40%)" }} tickLine={false} axisLine={false} />
                  <Tooltip
                    contentStyle={{ background: "hsl(0 0% 100%)", border: "1px solid hsl(240 5% 85%)", borderRadius: 0, fontSize: 12 }}
                  />
                  <Area type="monotone" dataKey="completed" stroke="hsl(260 100% 60%)" strokeWidth={2} fill="url(#colorCompleted)" name="Completed" />
                </AreaChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>

        <Card className="border-border">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-2">
              <Trophy className="w-4 h-4" /> Leaderboard
            </CardTitle>
          </CardHeader>
          <CardContent className="pt-0">
            {!summary?.top_members?.length ? (
              <div className="h-48 flex items-center justify-center text-sm text-muted-foreground">No members yet</div>
            ) : (
              <div className="space-y-2">
                {summary.top_members.map((m: any, i: number) => (
                  <div key={m.user_id} className="flex items-center gap-2.5">
                    <span className={`text-xs font-black w-5 text-center ${i === 0 ? "text-yellow-500" : i === 1 ? "text-slate-400" : i === 2 ? "text-amber-600" : "text-muted-foreground"}`}>
                      {i + 1}
                    </span>
                    <div className="w-7 h-7 rounded-sm bg-primary/10 flex items-center justify-center shrink-0">
                      <span className="text-xs font-bold text-primary">{m.full_name?.[0]?.toUpperCase()}</span>
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="text-xs font-semibold text-foreground truncate">{m.full_name}</div>
                      <div className="text-[10px] text-muted-foreground">{m.email}</div>
                    </div>
                    <Badge variant="secondary" className="text-[10px] px-1.5 py-0 font-bold">
                      {m.completed_count}
                    </Badge>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        <Card className="lg:col-span-3 border-border">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-2">
              <Activity className="w-4 h-4" /> Recent Completions
            </CardTitle>
          </CardHeader>
          <CardContent className="pt-0">
            {!summary?.recent_completions?.length ? (
              <div className="py-8 text-center text-sm text-muted-foreground">No completions yet</div>
            ) : (
              <div className="divide-y divide-border">
                {summary.recent_completions.map((c: any) => (
                  <div key={c.id} className="flex items-center gap-3 py-2.5">
                    <div className="w-6 h-6 rounded-sm bg-secondary/20 flex items-center justify-center shrink-0">
                      <CheckSquare className="w-3.5 h-3.5 text-secondary-foreground" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <span className="text-xs font-semibold text-foreground">{c.user_name}</span>
                      <span className="text-xs text-muted-foreground"> completed </span>
                      <span className="text-xs font-medium text-foreground">{c.task_title}</span>
                    </div>
                    <span className="text-[10px] text-muted-foreground shrink-0">
                      {c.created_at ? format(new Date(c.created_at), "MMM d") : ""}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
