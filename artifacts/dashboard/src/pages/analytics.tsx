import { useListAnalyticsSnapshots, getListAnalyticsSnapshotsQueryKey, useGetMemberLeaderboard, getGetMemberLeaderboardQueryKey } from "@workspace/api-client-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useState } from "react";
import { AreaChart, Area, BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts";
import { format } from "date-fns";
import { TrendingUp, Trophy, Users, CheckSquare } from "lucide-react";
import { Badge } from "@/components/ui/badge";

export default function AnalyticsPage() {
  const [days, setDays] = useState(30);

  const { data: snapshots, isLoading } = useListAnalyticsSnapshots(
    { days },
    { query: { queryKey: getListAnalyticsSnapshotsQueryKey({ days }) } }
  );

  const { data: leaderboard } = useGetMemberLeaderboard(
    { limit: 10 },
    { query: { queryKey: getGetMemberLeaderboardQueryKey({ limit: 10 }) } }
  );

  const chartData = (snapshots ?? []).map((s: any) => ({
    date: format(new Date(s.snapshot_date), days > 14 ? "MMM d" : "d MMM"),
    completed: s.completed_tasks,
    new: s.new_tasks,
    members: s.active_members,
  }));

  const totalCompleted = chartData.reduce((acc, d) => acc + d.completed, 0);
  const totalNew = chartData.reduce((acc, d) => acc + d.new, 0);
  const peakDay = chartData.reduce((max, d) => d.completed > max.completed ? d : max, { completed: 0, date: "" });

  return (
    <div className="p-6 max-w-[1400px]">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-black text-foreground tracking-tight">Analytics</h1>
          <p className="text-sm text-muted-foreground mt-0.5">Performance trends and insights</p>
        </div>
        <Select value={String(days)} onValueChange={(v) => setDays(Number(v))}>
          <SelectTrigger className="w-28">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="7">7 days</SelectItem>
            <SelectItem value="14">14 days</SelectItem>
            <SelectItem value="30">30 days</SelectItem>
            <SelectItem value="90">90 days</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div className="grid grid-cols-3 gap-4 mb-6">
        {[
          { label: "Total Completed", value: totalCompleted, icon: CheckSquare, color: "text-primary" },
          { label: "New Tasks", value: totalNew, icon: TrendingUp, color: "text-secondary-foreground" },
          { label: "Peak Day", value: peakDay.date || "—", icon: Users, color: "text-foreground" },
        ].map(({ label, value, icon: Icon, color }) => (
          <Card key={label} className="border-border">
            <CardContent className="p-5">
              <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2">{label}</p>
              <div className="flex items-center gap-2">
                <Icon className={`w-4 h-4 ${color}`} />
                <span className="text-2xl font-black text-foreground">{value}</span>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <Card className="lg:col-span-2 border-border">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-bold uppercase tracking-wider text-muted-foreground">Daily Completions</CardTitle>
          </CardHeader>
          <CardContent className="pt-0">
            {isLoading ? (
              <Skeleton className="h-56" />
            ) : chartData.length === 0 ? (
              <div className="h-56 flex items-center justify-center text-sm text-muted-foreground">No data for this period</div>
            ) : (
              <ResponsiveContainer width="100%" height={220}>
                <AreaChart data={chartData} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
                  <defs>
                    <linearGradient id="gradCompleted" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="hsl(260 100% 60%)" stopOpacity={0.3} />
                      <stop offset="95%" stopColor="hsl(260 100% 60%)" stopOpacity={0} />
                    </linearGradient>
                    <linearGradient id="gradNew" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="hsl(160 100% 50%)" stopOpacity={0.2} />
                      <stop offset="95%" stopColor="hsl(160 100% 50%)" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(240 5% 90%)" vertical={false} />
                  <XAxis dataKey="date" tick={{ fontSize: 10, fill: "hsl(240 5% 40%)" }} tickLine={false} axisLine={false} interval={Math.floor(chartData.length / 6)} />
                  <YAxis tick={{ fontSize: 10, fill: "hsl(240 5% 40%)" }} tickLine={false} axisLine={false} />
                  <Tooltip contentStyle={{ background: "hsl(0 0% 100%)", border: "1px solid hsl(240 5% 85%)", borderRadius: 0, fontSize: 12 }} />
                  <Area type="monotone" dataKey="completed" stroke="hsl(260 100% 60%)" strokeWidth={2} fill="url(#gradCompleted)" name="Completed" />
                  <Area type="monotone" dataKey="new" stroke="hsl(160 100% 40%)" strokeWidth={2} fill="url(#gradNew)" name="New" />
                </AreaChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>

        <Card className="border-border">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-2">
              <Trophy className="w-4 h-4" /> Top Members
            </CardTitle>
          </CardHeader>
          <CardContent className="pt-0">
            {!leaderboard?.length ? (
              <div className="py-10 text-center text-sm text-muted-foreground">No data yet</div>
            ) : (
              <div className="space-y-2">
                {leaderboard.map((m: any, i: number) => (
                  <div key={m.user_id} className="flex items-center gap-2">
                    <span className={`text-xs font-black w-5 text-center ${i === 0 ? "text-yellow-500" : i === 1 ? "text-slate-400" : i === 2 ? "text-amber-600" : "text-muted-foreground"}`}>
                      {i + 1}
                    </span>
                    <div className="w-6 h-6 rounded-sm bg-primary/10 flex items-center justify-center shrink-0">
                      <span className="text-[10px] font-bold text-primary">{m.full_name?.[0]?.toUpperCase()}</span>
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="text-xs font-semibold text-foreground truncate">{m.full_name}</div>
                    </div>
                    <Badge variant="secondary" className="text-[10px] px-1.5 py-0 font-bold shrink-0">{m.completed_count}</Badge>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        <Card className="lg:col-span-3 border-border">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-bold uppercase tracking-wider text-muted-foreground">New Tasks per Day</CardTitle>
          </CardHeader>
          <CardContent className="pt-0">
            {isLoading ? (
              <Skeleton className="h-40" />
            ) : (
              <ResponsiveContainer width="100%" height={160}>
                <BarChart data={chartData} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(240 5% 90%)" vertical={false} />
                  <XAxis dataKey="date" tick={{ fontSize: 10, fill: "hsl(240 5% 40%)" }} tickLine={false} axisLine={false} interval={Math.floor(chartData.length / 6)} />
                  <YAxis tick={{ fontSize: 10, fill: "hsl(240 5% 40%)" }} tickLine={false} axisLine={false} />
                  <Tooltip contentStyle={{ background: "hsl(0 0% 100%)", border: "1px solid hsl(240 5% 85%)", borderRadius: 0, fontSize: 12 }} />
                  <Bar dataKey="new" fill="hsl(160 100% 40%)" radius={0} name="New Tasks" />
                </BarChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
