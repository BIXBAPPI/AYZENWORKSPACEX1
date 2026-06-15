import { useListMembers, getListMembersQueryKey, useGetMemberLeaderboard, getGetMemberLeaderboardQueryKey, useUpdateMember } from "@workspace/api-client-react";
import { useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Trophy, Users, Search, CheckSquare } from "lucide-react";
import { format } from "date-fns";

const ROLE_COLORS: Record<string, string> = {
  owner: "bg-yellow-100 text-yellow-800 border-yellow-200",
  manager: "bg-primary/10 text-primary border-primary/20",
  member: "bg-muted text-muted-foreground border-border",
};

export default function MembersPage() {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState("");
  const [tab, setTab] = useState<"roster" | "leaderboard">("roster");

  const { data: members, isLoading } = useListMembers({
    query: { queryKey: getListMembersQueryKey() },
  });

  const { data: leaderboard, isLoading: leaderLoading } = useGetMemberLeaderboard(
    { limit: 20 },
    { query: { queryKey: getGetMemberLeaderboardQueryKey({ limit: 20 }) } }
  );

  const { mutate: updateMember } = useUpdateMember({
    mutation: {
      onSuccess: () => queryClient.invalidateQueries({ queryKey: getListMembersQueryKey() }),
    },
  });

  const filtered = (members ?? []).filter((m: any) =>
    !search || m.full_name?.toLowerCase().includes(search.toLowerCase()) || m.email?.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="p-6 max-w-[1400px]">
      <div className="mb-6">
        <h1 className="text-2xl font-black text-foreground tracking-tight">Members</h1>
        <p className="text-sm text-muted-foreground mt-0.5">{members?.length ?? 0} total members</p>
      </div>

      <div className="flex gap-1 mb-5 border-b border-border">
        <button
          onClick={() => setTab("roster")}
          className={`pb-2 px-1 mr-4 text-sm font-semibold border-b-2 transition-colors ${tab === "roster" ? "border-primary text-primary" : "border-transparent text-muted-foreground hover:text-foreground"}`}
        >
          <span className="flex items-center gap-1.5"><Users className="w-3.5 h-3.5" /> Roster</span>
        </button>
        <button
          onClick={() => setTab("leaderboard")}
          className={`pb-2 px-1 text-sm font-semibold border-b-2 transition-colors ${tab === "leaderboard" ? "border-primary text-primary" : "border-transparent text-muted-foreground hover:text-foreground"}`}
        >
          <span className="flex items-center gap-1.5"><Trophy className="w-3.5 h-3.5" /> Leaderboard</span>
        </button>
      </div>

      {tab === "roster" ? (
        <>
          <div className="mb-4 relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <Input placeholder="Search members..." value={search} onChange={(e) => setSearch(e.target.value)} className="pl-9" />
          </div>
          <Card className="border-border">
            <CardContent className="p-0">
              {isLoading ? (
                <div className="p-4 space-y-2">{Array.from({ length: 5 }).map((_, i) => <Skeleton key={i} className="h-14" />)}</div>
              ) : filtered.length === 0 ? (
                <div className="py-16 text-center text-sm text-muted-foreground">No members found</div>
              ) : (
                <div className="divide-y divide-border">
                  {filtered.map((m: any) => (
                    <div key={m.id} className="flex items-center gap-3 px-4 py-3">
                      <div className="w-8 h-8 rounded-sm bg-primary/10 flex items-center justify-center shrink-0">
                        <span className="text-xs font-bold text-primary">{m.full_name?.[0]?.toUpperCase() ?? "?"}</span>
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-semibold text-foreground truncate">{m.full_name}</span>
                          <Badge className={`text-[10px] px-1.5 py-0 border font-semibold ${ROLE_COLORS[m.role] ?? ROLE_COLORS.member}`} variant="outline">
                            {m.role}
                          </Badge>
                        </div>
                        <div className="text-xs text-muted-foreground truncate">{m.email}</div>
                      </div>
                      <div className="flex items-center gap-3 shrink-0">
                        <div className="text-right">
                          <div className="text-xs font-bold text-foreground flex items-center gap-1">
                            <CheckSquare className="w-3 h-3 text-secondary" />
                            {m.tasks_completed}/{m.tasks_assigned}
                          </div>
                          <div className="text-[10px] text-muted-foreground">tasks</div>
                        </div>
                        {m.role !== "owner" && (
                          <Select
                            value={m.role}
                            onValueChange={(role) => updateMember({ userId: m.id, data: { role } })}
                          >
                            <SelectTrigger className="w-24 h-6 text-[11px]">
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="manager">Manager</SelectItem>
                              <SelectItem value="member">Member</SelectItem>
                            </SelectContent>
                          </Select>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </>
      ) : (
        <Card className="border-border">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-bold uppercase tracking-wider text-muted-foreground">Top Performers</CardTitle>
          </CardHeader>
          <CardContent className="pt-0">
            {leaderLoading ? (
              <div className="space-y-2">{Array.from({ length: 5 }).map((_, i) => <Skeleton key={i} className="h-12" />)}</div>
            ) : !leaderboard?.length ? (
              <div className="py-12 text-center text-sm text-muted-foreground">No data yet</div>
            ) : (
              <div className="space-y-1">
                {leaderboard.map((m: any, i: number) => (
                  <div key={m.user_id} className="flex items-center gap-3 p-3 rounded-sm hover:bg-muted/50 transition-colors">
                    <div className={`text-lg font-black w-8 text-center ${i === 0 ? "text-yellow-500" : i === 1 ? "text-slate-400" : i === 2 ? "text-amber-600" : "text-muted-foreground"}`}>
                      {i < 3 ? ["#1", "#2", "#3"][i] : `#${i + 1}`}
                    </div>
                    <div className="w-8 h-8 rounded-sm bg-primary/10 flex items-center justify-center shrink-0">
                      <span className="text-xs font-bold text-primary">{m.full_name?.[0]?.toUpperCase()}</span>
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="text-sm font-semibold text-foreground">{m.full_name}</div>
                      <div className="text-xs text-muted-foreground">{m.email}</div>
                    </div>
                    <div className="text-right">
                      <div className="text-lg font-black text-primary">{m.completed_count}</div>
                      <div className="text-[10px] text-muted-foreground">completed</div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
