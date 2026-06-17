import { useQuery } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Progress } from "@/components/ui/progress";
import { RadialBarChart, RadialBar, ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, CartesianGrid } from "recharts";
import { Trophy, Flame, Star, Target, CheckSquare, AlertTriangle, TrendingUp, Layers } from "lucide-react";

async function fetchMyAnalytics() {
  const res = await fetch("/api/v1/analytics/me", { credentials: "include" });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

const TIER_COLORS: Record<string, string> = {
  Bronze: "text-amber-700",
  Silver: "text-slate-400",
  Gold: "text-yellow-400",
  Platinum: "text-cyan-400",
};

const TIER_XP: Record<string, number> = {
  Bronze: 1000,
  Silver: 5000,
  Gold: 10000,
  Platinum: 10000,
};

function XpProgressBar({ xp, tier }: { xp: number; tier: string }) {
  const nextTier = tier === "Bronze" ? "Silver" : tier === "Silver" ? "Gold" : tier === "Gold" ? "Platinum" : null;
  const nextXp = nextTier ? TIER_XP[tier] : null;
  const prevXp = tier === "Bronze" ? 0 : tier === "Silver" ? 1000 : tier === "Gold" ? 5000 : 10000;
  const pct = nextXp ? Math.min(100, ((xp - prevXp) / (nextXp - prevXp)) * 100) : 100;
  return (
    <div className="space-y-1.5">
      <div className="flex justify-between text-[10px] text-muted-foreground">
        <span>{tier}</span>
        {nextTier && <span>{nextTier} at {nextXp?.toLocaleString()} XP</span>}
        {!nextTier && <span>Max tier reached</span>}
      </div>
      <Progress value={pct} className="h-2" />
      <div className="text-[10px] text-muted-foreground text-right">{xp.toLocaleString()} XP</div>
    </div>
  );
}

export default function AnalysisPage() {
  const { data, isLoading } = useQuery({
    queryKey: ["analytics-me"],
    queryFn: fetchMyAnalytics,
  });

  if (isLoading) {
    return (
      <div className="p-4 md:p-6 space-y-4">
        <Skeleton className="h-8 w-48" />
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {[1,2,3,4].map(i => <Skeleton key={i} className="h-24" />)}
        </div>
        <Skeleton className="h-48" />
      </div>
    );
  }

  const tierColor = TIER_COLORS[data?.tier ?? "Bronze"] ?? "text-amber-700";
  const activityData = (data?.daily_activity ?? []).map((d: any) => ({
    date: d.date.slice(5),
    tasks: d.count,
  }));

  return (
    <div className="p-4 md:p-6 max-w-[1200px] space-y-5">
      <div>
        <h1 className="text-xl md:text-2xl font-black text-foreground tracking-tight">My Analysis</h1>
        <p className="text-sm text-muted-foreground mt-0.5">Your personal performance &amp; XP progress</p>
      </div>

      {/* XP / Tier hero */}
      <Card className="border-border">
        <CardContent className="p-5">
          <div className="flex flex-col md:flex-row md:items-center gap-5">
            <div className="flex items-center gap-4 flex-1">
              <div className="w-16 h-16 rounded-sm bg-primary/10 flex items-center justify-center shrink-0">
                <Star className={`w-8 h-8 ${tierColor}`} />
              </div>
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-1">
                  <span className={`text-2xl font-black ${tierColor}`}>{data?.tier ?? "Bronze"}</span>
                  {data?.rank && (
                    <Badge variant="outline" className="text-[10px] px-1.5 py-0">#{data.rank} in community</Badge>
                  )}
                </div>
                <XpProgressBar xp={data?.xp ?? 0} tier={data?.tier ?? "Bronze"} />
              </div>
            </div>
            <div className="flex items-center gap-5 md:gap-8">
              <div className="text-center">
                <Flame className="w-5 h-5 text-orange-400 mx-auto mb-1" />
                <div className="text-2xl font-black text-foreground">{data?.streak ?? 0}</div>
                <div className="text-[10px] text-muted-foreground">Day streak</div>
              </div>
              <div className="text-center">
                <Trophy className="w-5 h-5 text-yellow-400 mx-auto mb-1" />
                <div className="text-2xl font-black text-foreground">{data?.roi_pct ?? 0}%</div>
                <div className="text-[10px] text-muted-foreground">Completion ROI</div>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Task stats */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        {[
          { label: "Assigned", value: data?.total_assigned ?? 0, icon: Layers, color: "bg-primary/10" },
          { label: "Completed", value: data?.completed ?? 0, icon: CheckSquare, color: "bg-green-500/10" },
          { label: "In Progress", value: data?.in_progress ?? 0, icon: TrendingUp, color: "bg-blue-500/10" },
          { label: "Pending", value: data?.pending ?? 0, icon: Target, color: "bg-yellow-500/10" },
          { label: "Overdue", value: data?.overdue ?? 0, icon: AlertTriangle, color: "bg-destructive/10" },
        ].map(({ label, value, icon: Icon, color }) => (
          <Card key={label} className="border-border">
            <CardContent className="p-4">
              <div className={`w-8 h-8 rounded-sm ${color} flex items-center justify-center mb-2`}>
                <Icon className="w-4 h-4 text-foreground/70" />
              </div>
              <div className="text-2xl font-black text-foreground">{value}</div>
              <div className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground mt-0.5">{label}</div>
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Activity chart */}
        <Card className="border-border">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-bold uppercase tracking-wider text-muted-foreground">
              Daily Completions (60 days)
            </CardTitle>
          </CardHeader>
          <CardContent className="pt-0">
            {activityData.length === 0 ? (
              <div className="h-40 flex items-center justify-center text-sm text-muted-foreground">No activity yet</div>
            ) : (
              <ResponsiveContainer width="100%" height={180}>
                <BarChart data={activityData} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(240 5% 90%)" vertical={false} />
                  <XAxis dataKey="date" tick={{ fontSize: 9, fill: "hsl(240 5% 40%)" }} tickLine={false} axisLine={false} interval={6} />
                  <YAxis tick={{ fontSize: 9, fill: "hsl(240 5% 40%)" }} tickLine={false} axisLine={false} />
                  <Tooltip contentStyle={{ background: "hsl(0 0% 100%)", border: "1px solid hsl(240 5% 85%)", borderRadius: 0, fontSize: 11 }} />
                  <Bar dataKey="tasks" fill="hsl(260 100% 60%)" radius={[2, 2, 0, 0]} name="Tasks done" />
                </BarChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>

        {/* Project breakdown */}
        <Card className="border-border">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-bold uppercase tracking-wider text-muted-foreground">
              Project Breakdown
            </CardTitle>
          </CardHeader>
          <CardContent className="pt-0">
            {!data?.projects?.length ? (
              <div className="h-40 flex items-center justify-center text-sm text-muted-foreground">No projects assigned</div>
            ) : (
              <div className="space-y-3">
                {data.projects.map((p: any) => (
                  <div key={p.id}>
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-xs font-medium text-foreground truncate flex-1 mr-2">{p.name}</span>
                      <div className="flex items-center gap-2 shrink-0">
                        <span className="text-[10px] text-muted-foreground">{p.completed_tasks}/{p.total_tasks}</span>
                        <Badge variant="outline" className="text-[10px] px-1.5 py-0">{p.xp_earned} XP</Badge>
                      </div>
                    </div>
                    <Progress value={p.completion_pct} className="h-1.5" />
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
