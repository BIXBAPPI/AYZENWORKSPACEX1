import { useState, useEffect, useRef } from "react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  Users, Key, GitBranch, BarChart3, Copy, Check, Trash2, RefreshCw,
  Shield, Zap, Search, Plus, ChevronDown, AlertCircle, Activity, Bot,
  CheckCircle2, XCircle, Clock, TrendingUp, ChevronRight, FolderKanban,
  Wallet, Twitter, MessageSquare, Eye
} from "lucide-react";
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { useToast } from "@/hooks/use-toast";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter
} from "@/components/ui/dialog";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue
} from "@/components/ui/select";
import { useAuth } from "@/lib/auth";

const api = (path: string, opts?: RequestInit) =>
  fetch(`/api/v1${path}`, { credentials: "include", ...opts });

function StatCard({ label, value, icon: Icon, color }: { label: string; value: number | string; icon: any; color: string }) {
  return (
    <div className="bg-card border border-border rounded-lg p-4 flex items-center gap-4">
      <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${color}`}>
        <Icon className="w-5 h-5 text-white" />
      </div>
      <div>
        <div className="text-2xl font-bold text-foreground">{value}</div>
        <div className="text-xs text-muted-foreground">{label}</div>
      </div>
    </div>
  );
}

function TierBadge({ xp }: { xp: number }) {
  if (xp >= 20000) return <Badge className="bg-cyan-500/10 text-cyan-400 border-cyan-500/30">💎 Platinum</Badge>;
  if (xp >= 5000) return <Badge className="bg-yellow-500/10 text-yellow-400 border-yellow-500/30">🥇 Gold</Badge>;
  if (xp >= 1000) return <Badge className="bg-slate-400/10 text-slate-300 border-slate-400/30">🥈 Silver</Badge>;
  return <Badge className="bg-amber-700/10 text-amber-600 border-amber-700/30">🥉 Bronze</Badge>;
}

// ── Users Tab ────────────────────────────────────────────────────────────────

function UsersTab() {
  const { toast } = useToast();
  const [users, setUsers] = useState<any[]>([]);
  const [total, setTotal] = useState(0);
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(false);
  const [editUser, setEditUser] = useState<any | null>(null);
  const [editRole, setEditRole] = useState("");
  const [editXP, setEditXP] = useState("");
  const [linkInfo, setLinkInfo] = useState<Record<string, any>>({});
  const [viewUserId, setViewUserId] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    try {
      const r = await api(`/admin/users?q=${encodeURIComponent(search)}&page=${page}&limit=25`);
      const d = await r.json();
      setUsers(d.users || []);
      setTotal(d.total || 0);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, [search, page]);

  const updateUser = async () => {
    if (!editUser) return;
    const body: any = {};
    if (editRole && editRole !== editUser.role) body.role = editRole;
    if (editXP !== "" && parseInt(editXP) !== editUser.global_xp) body.global_xp = parseInt(editXP);
    if (Object.keys(body).length === 0) { setEditUser(null); return; }
    const r = await api(`/admin/users/${editUser.id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (r.ok) {
      toast({ description: "User updated" });
      setEditUser(null);
      load();
    } else {
      toast({ variant: "destructive", description: "Update failed" });
    }
  };

  const deleteUser = async (u: any) => {
    if (!confirm(`Delete ${u.email}? This is permanent.`)) return;
    const r = await api(`/admin/users/${u.id}`, { method: "DELETE" });
    if (r.ok) { toast({ description: "User deleted" }); load(); }
    else toast({ variant: "destructive", description: "Delete failed" });
  };

  const fetchLinkCode = async (userId: string) => {
    const r = await api(`/admin/telegram-link-code/${userId}`);
    const d = await r.json();
    setLinkInfo(prev => ({ ...prev, [userId]: d }));
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <Input
            value={search}
            onChange={(e) => { setSearch(e.target.value); setPage(1); }}
            placeholder="Search users…"
            className="pl-8"
          />
        </div>
        <Button variant="outline" size="sm" onClick={load} disabled={loading}>
          <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
        </Button>
        <span className="text-xs text-muted-foreground">{total} members</span>
      </div>

      <div className="rounded-lg border border-border overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-muted/30">
            <tr>
              {["Member", "Role / Tier", "XP", "Tasks", "Telegram", "Actions"].map(h => (
                <th key={h} className="px-3 py-2 text-left text-xs font-semibold text-muted-foreground">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {users.map(u => (
              <tr key={u.id} className="border-t border-border hover:bg-muted/20 transition-colors">
                <td className="px-3 py-2.5">
                  <div className="flex items-center gap-2">
                    <div className="w-7 h-7 rounded-full bg-primary/10 flex items-center justify-center text-xs font-bold text-primary">
                      {(u.full_name || u.email)?.[0]?.toUpperCase()}
                    </div>
                    <div>
                      <div className="font-medium text-foreground truncate max-w-[150px]">{u.full_name || u.username || "—"}</div>
                      <div className="text-xs text-muted-foreground truncate max-w-[150px]">{u.email}</div>
                    </div>
                  </div>
                </td>
                <td className="px-3 py-2.5">
                  <div className="flex flex-col gap-1">
                    <Badge variant="outline" className="w-fit text-[10px] capitalize">{u.role}</Badge>
                    <TierBadge xp={u.global_xp} />
                  </div>
                </td>
                <td className="px-3 py-2.5">
                  <div className="font-mono font-bold text-primary">{(u.global_xp || 0).toLocaleString()}</div>
                  <div className="text-xs text-muted-foreground">🔥 {u.global_streak || 0} streak</div>
                </td>
                <td className="px-3 py-2.5">
                  <div className="text-xs">{u.tasks_done} done</div>
                  {u.email_verified ? (
                    <div className="flex items-center gap-1 text-green-500 text-xs"><CheckCircle2 className="w-3 h-3" /> verified</div>
                  ) : (
                    <div className="flex items-center gap-1 text-yellow-500 text-xs"><AlertCircle className="w-3 h-3" /> unverified</div>
                  )}
                </td>
                <td className="px-3 py-2.5">
                  {u.telegram_user_id ? (
                    <div className="flex items-center gap-1 text-blue-400 text-xs"><Bot className="w-3 h-3" /> @{u.telegram_handle || "linked"}</div>
                  ) : (
                    <div>
                      <div className="text-xs text-muted-foreground mb-1">Not linked</div>
                      {linkInfo[u.id] ? (
                        <CopyButton value={linkInfo[u.id].command} label="Copy /link" small />
                      ) : (
                        <Button variant="ghost" size="sm" className="h-6 text-xs px-2" onClick={() => fetchLinkCode(u.id)}>
                          Get code
                        </Button>
                      )}
                    </div>
                  )}
                </td>
                <td className="px-3 py-2.5">
                  <div className="flex items-center gap-1">
                    <Button variant="ghost" size="sm" className="h-7 w-7 p-0 text-muted-foreground hover:text-primary"
                      title="View detail" onClick={() => setViewUserId(u.id)}>
                      <Eye className="w-3.5 h-3.5" />
                    </Button>
                    <Button variant="outline" size="sm" className="h-7 text-xs px-2"
                      onClick={() => { setEditUser(u); setEditRole(u.role); setEditXP(String(u.global_xp || 0)); }}>
                      Edit
                    </Button>
                    <Button variant="ghost" size="sm" className="h-7 w-7 p-0 text-destructive hover:bg-destructive/10"
                      onClick={() => deleteUser(u)}>
                      <Trash2 className="w-3.5 h-3.5" />
                    </Button>
                  </div>
                </td>
              </tr>
            ))}
            {users.length === 0 && (
              <tr><td colSpan={6} className="text-center py-8 text-muted-foreground text-sm">No users found</td></tr>
            )}
          </tbody>
        </table>
      </div>

      {total > 25 && (
        <div className="flex items-center justify-center gap-2">
          <Button variant="outline" size="sm" disabled={page === 1} onClick={() => setPage(p => p - 1)}>Previous</Button>
          <span className="text-xs text-muted-foreground">Page {page}</span>
          <Button variant="outline" size="sm" onClick={() => setPage(p => p + 1)}>Next</Button>
        </div>
      )}

      <Dialog open={!!editUser} onOpenChange={() => setEditUser(null)}>
        <DialogContent>
          <DialogHeader><DialogTitle>Edit {editUser?.full_name || editUser?.email}</DialogTitle></DialogHeader>
          <div className="space-y-4 py-2">
            <div>
              <label className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-1.5 block">Role</label>
              <Select value={editRole} onValueChange={setEditRole}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="owner">Owner</SelectItem>
                  <SelectItem value="manager">Manager</SelectItem>
                  <SelectItem value="member">Member</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <label className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-1.5 block">XP Points</label>
              <Input type="number" value={editXP} onChange={e => setEditXP(e.target.value)} min={0} />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setEditUser(null)}>Cancel</Button>
            <Button onClick={updateUser} style={{ background: "linear-gradient(135deg,#7c3aed,#06b6d4)" }}>Save Changes</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <UserDetailDrawer userId={viewUserId} onClose={() => setViewUserId(null)} />
    </div>
  );
}

// ── Codes Tab ────────────────────────────────────────────────────────────────

function CopyButton({ value, label, small }: { value: string; label?: string; small?: boolean }) {
  const [copied, setCopied] = useState(false);
  const copy = () => {
    navigator.clipboard.writeText(value);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };
  return (
    <Button variant="outline" size={small ? "sm" : "default"}
      className={small ? "h-6 text-xs px-2" : "h-8 text-xs px-3"}
      onClick={copy}>
      {copied ? <><Check className="w-3 h-3 mr-1 text-green-500" /> Copied</> : <><Copy className="w-3 h-3 mr-1" /> {label || "Copy"}</>}
    </Button>
  );
}

function CodesTab() {
  const { toast } = useToast();
  const [codes, setCodes] = useState<any[]>([]);
  const [count, setCount] = useState(5);
  const [days, setDays] = useState(30);
  const [loading, setLoading] = useState(false);
  const [generating, setGenerating] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const r = await api("/activation-codes/");
      setCodes(await r.json());
    } finally { setLoading(false); }
  };

  useEffect(() => { load(); }, []);

  const generate = async () => {
    setGenerating(true);
    try {
      const r = await api("/activation-codes/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ count, expires_in_days: days }),
      });
      if (r.ok) { toast({ description: `Generated ${count} codes` }); load(); }
      else toast({ variant: "destructive", description: "Failed to generate codes" });
    } finally { setGenerating(false); }
  };

  const revoke = async (id: string) => {
    if (!confirm("Revoke this code?")) return;
    const r = await api(`/activation-codes/${id}`, { method: "DELETE" });
    if (r.ok) { toast({ description: "Code revoked" }); load(); }
    else toast({ variant: "destructive", description: "Failed to revoke" });
  };

  const inviteLink = (code: string) =>
    `${window.location.origin}/register?code=${encodeURIComponent(code)}`;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end gap-3 p-4 bg-muted/20 rounded-lg border border-border">
        <div>
          <label className="text-xs font-semibold uppercase tracking-wide text-muted-foreground block mb-1">Count</label>
          <Input type="number" value={count} onChange={e => setCount(Number(e.target.value))}
            min={1} max={50} className="w-20" />
        </div>
        <div>
          <label className="text-xs font-semibold uppercase tracking-wide text-muted-foreground block mb-1">Expires (days)</label>
          <Input type="number" value={days} onChange={e => setDays(Number(e.target.value))}
            min={1} max={365} className="w-24" />
        </div>
        <Button onClick={generate} disabled={generating}
          style={{ background: "linear-gradient(135deg,#7c3aed,#06b6d4)" }}>
          <Plus className="w-4 h-4 mr-1.5" />
          {generating ? "Generating…" : `Generate ${count} Code${count > 1 ? "s" : ""}`}
        </Button>
        <Button variant="outline" size="sm" onClick={load} disabled={loading}>
          <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
        </Button>
      </div>

      <div className="rounded-lg border border-border overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-muted/30">
            <tr>
              {["Code", "Status", "Expires", "Used By", "Actions"].map(h => (
                <th key={h} className="px-3 py-2 text-left text-xs font-semibold text-muted-foreground">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {codes.map(c => (
              <tr key={c.id} className="border-t border-border hover:bg-muted/20">
                <td className="px-3 py-2.5">
                  <code className="font-mono text-xs font-bold text-primary bg-primary/10 px-2 py-0.5 rounded">{c.code}</code>
                </td>
                <td className="px-3 py-2.5">
                  {c.is_used
                    ? <Badge className="bg-red-500/10 text-red-400 border-red-500/30 text-[10px]"><XCircle className="w-3 h-3 mr-1" />Used</Badge>
                    : <Badge className="bg-green-500/10 text-green-400 border-green-500/30 text-[10px]"><CheckCircle2 className="w-3 h-3 mr-1" />Active</Badge>}
                </td>
                <td className="px-3 py-2.5 text-xs text-muted-foreground">
                  {c.expires_at ? new Date(c.expires_at).toLocaleDateString() : "Never"}
                </td>
                <td className="px-3 py-2.5 text-xs text-muted-foreground">
                  {c.used_by_email || "—"}
                  {c.used_at && <div className="text-[10px]">{new Date(c.used_at).toLocaleDateString()}</div>}
                </td>
                <td className="px-3 py-2.5">
                  {!c.is_used && (
                    <div className="flex items-center gap-1">
                      <CopyButton value={c.code} label="Code" small />
                      <CopyButton value={inviteLink(c.code)} label="Link" small />
                      <Button variant="ghost" size="sm" className="h-6 w-6 p-0 text-destructive hover:bg-destructive/10"
                        onClick={() => revoke(c.id)}>
                        <Trash2 className="w-3 h-3" />
                      </Button>
                    </div>
                  )}
                </td>
              </tr>
            ))}
            {codes.length === 0 && (
              <tr><td colSpan={5} className="text-center py-8 text-muted-foreground text-sm">No codes yet — generate some above</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ── Referrals Tab ────────────────────────────────────────────────────────────

function ReferralsTab() {
  const { toast } = useToast();
  const [pending, setPending] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [approvedCodes, setApprovedCodes] = useState<Record<string, string>>({});

  const load = async () => {
    setLoading(true);
    try {
      const r = await api("/referrals/pending");
      const d = await r.json();
      setPending(Array.isArray(d) ? d : []);
    } finally { setLoading(false); }
  };

  useEffect(() => { load(); }, []);

  const approve = async (id: string) => {
    const r = await api(`/referrals/${id}/approve`, { method: "POST" });
    const d = await r.json();
    if (r.ok) {
      setApprovedCodes(prev => ({ ...prev, [id]: d.activation_code }));
      toast({ description: `Approved! Code: ${d.activation_code}` });
      load();
    } else {
      toast({ variant: "destructive", description: "Approval failed" });
    }
  };

  const reject = async (id: string) => {
    const r = await api(`/referrals/${id}/reject`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ note: "Rejected by admin" }),
    });
    if (r.ok) { toast({ description: "Referral rejected" }); load(); }
    else toast({ variant: "destructive", description: "Rejection failed" });
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-foreground">Pending Referrals</h3>
        <Button variant="outline" size="sm" onClick={load} disabled={loading}>
          <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
        </Button>
      </div>

      {pending.length === 0 ? (
        <div className="text-center py-12 text-muted-foreground">
          <GitBranch className="w-8 h-8 mx-auto mb-2 opacity-30" />
          <p className="text-sm">No pending referrals</p>
        </div>
      ) : (
        <div className="space-y-3">
          {pending.map(r => (
            <div key={r.id} className="border border-border rounded-lg p-4 bg-card">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <div className="font-medium text-sm">{r.referred_email}</div>
                  {r.referred_username && <div className="text-xs text-muted-foreground">@{r.referred_username}</div>}
                  <div className="text-xs text-muted-foreground mt-1">
                    Referred by <span className="font-medium text-foreground">{r.referrer_name || r.referrer_email}</span>
                    {" · "}{new Date(r.created_at).toLocaleDateString()}
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  {approvedCodes[r.id] ? (
                    <CopyButton value={approvedCodes[r.id]} label={approvedCodes[r.id]} small />
                  ) : (
                    <>
                      <Button size="sm" className="h-7 text-xs bg-green-600 hover:bg-green-700 text-white"
                        onClick={() => approve(r.id)}>
                        <CheckCircle2 className="w-3.5 h-3.5 mr-1" /> Approve
                      </Button>
                      <Button variant="outline" size="sm" className="h-7 text-xs text-destructive hover:bg-destructive/10"
                        onClick={() => reject(r.id)}>
                        <XCircle className="w-3.5 h-3.5 mr-1" /> Reject
                      </Button>
                    </>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ── System Tab ────────────────────────────────────────────────────────────────

function SystemTab() {
  const [stats, setStats] = useState<any>(null);
  const [errors, setErrors] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setLoading(true);
    try {
      const [sr, er] = await Promise.all([
        api("/admin/stats"),
        api("/admin/errors?limit=20"),
      ]);
      setStats(await sr.json());
      setErrors(await er.json());
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  if (loading || !stats) {
    return <div className="text-center py-12 text-muted-foreground text-sm">Loading system data…</div>;
  }

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <StatCard label="Total Members" value={stats.total_users} icon={Users} color="bg-purple-600" />
        <StatCard label="Verified" value={stats.verified_users} icon={CheckCircle2} color="bg-green-600" />
        <StatCard label="Telegram Linked" value={stats.telegram_linked} icon={Bot} color="bg-blue-500" />
        <StatCard label="Total XP" value={(stats.total_xp || 0).toLocaleString()} icon={Zap} color="bg-yellow-500" />
        <StatCard label="Total Tasks" value={stats.total_tasks} icon={Activity} color="bg-pink-600" />
        <StatCard label="Completed" value={stats.completed_tasks} icon={CheckCircle2} color="bg-teal-600" />
        <StatCard label="Active Codes" value={stats.unused_codes} icon={Key} color="bg-violet-600" />
        <StatCard label="Errors (24h)" value={stats.errors_24h} icon={AlertCircle} color={stats.errors_24h > 0 ? "bg-red-600" : "bg-gray-600"} />
      </div>

      {stats.pending_referrals > 0 && (
        <div className="bg-yellow-500/10 border border-yellow-500/30 rounded-lg p-3 flex items-center gap-2 text-sm text-yellow-500">
          <AlertCircle className="w-4 h-4 shrink-0" />
          {stats.pending_referrals} pending referral{stats.pending_referrals !== 1 ? "s" : ""} awaiting review
        </div>
      )}

      <div>
        <h3 className="text-sm font-semibold mb-3 text-foreground flex items-center gap-2">
          <AlertCircle className="w-4 h-4 text-destructive" /> Recent Errors
        </h3>
        {errors.length === 0 ? (
          <div className="text-center py-8 text-muted-foreground text-sm border border-border rounded-lg">
            <CheckCircle2 className="w-8 h-8 mx-auto mb-2 text-green-500 opacity-50" />
            No recent errors — system healthy
          </div>
        ) : (
          <div className="space-y-2">
            {errors.map(e => (
              <div key={e.id} className="bg-card border border-border rounded p-3 text-xs">
                <div className="flex items-center gap-2 mb-1">
                  <Badge variant="outline" className={e.level === "ERROR" ? "border-red-500/30 text-red-400" : "border-yellow-500/30 text-yellow-400"}>
                    {e.level}
                  </Badge>
                  <span className="text-muted-foreground">{e.module}</span>
                  <span className="text-muted-foreground ml-auto">{new Date(e.created_at).toLocaleTimeString()}</span>
                </div>
                <div className="font-mono text-foreground/80 truncate">{e.message}</div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// ── User Detail Drawer ────────────────────────────────────────────────────────

function UserDetailDrawer({ userId, onClose }: { userId: string | null; onClose: () => void }) {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!userId) { setData(null); return; }
    setLoading(true);
    api(`/admin/users/${userId}/progress`)
      .then(r => r.json())
      .then(d => setData(d))
      .finally(() => setLoading(false));
  }, [userId]);

  const u = data?.user;
  const projects: any[] = data?.projects ?? [];

  const tier = (xp: number) => {
    if (xp >= 20000) return { label: "💎 Platinum", color: "text-cyan-400" };
    if (xp >= 5000) return { label: "🥇 Gold", color: "text-yellow-400" };
    if (xp >= 1000) return { label: "🥈 Silver", color: "text-slate-300" };
    return { label: "🥉 Bronze", color: "text-amber-600" };
  };

  return (
    <Sheet open={!!userId} onOpenChange={(open) => { if (!open) onClose(); }}>
      <SheetContent className="w-full sm:max-w-xl overflow-y-auto">
        <SheetHeader className="mb-4">
          <SheetTitle className="font-black">Member Detail</SheetTitle>
        </SheetHeader>

        {loading && (
          <div className="space-y-3">
            {Array.from({ length: 4 }).map((_, i) => <div key={i} className="h-16 bg-muted/20 rounded-lg animate-pulse" />)}
          </div>
        )}

        {!loading && u && (
          <div className="space-y-5">
            {/* User summary card */}
            <div className="bg-card border border-border rounded-lg p-4 flex items-start gap-4">
              <div className="w-12 h-12 rounded-full bg-primary/10 flex items-center justify-center text-lg font-black text-primary shrink-0">
                {(u.full_name || u.email)?.[0]?.toUpperCase()}
              </div>
              <div className="flex-1 min-w-0">
                <div className="font-bold text-foreground text-base">{u.full_name || u.username || "—"}</div>
                <div className="text-xs text-muted-foreground truncate">{u.email}</div>
                <div className="flex flex-wrap items-center gap-2 mt-2">
                  <Badge variant="outline" className="capitalize text-[10px]">{u.role}</Badge>
                  <span className={`text-xs font-bold ${tier(u.global_xp || 0).color}`}>{tier(u.global_xp || 0).label}</span>
                  <span className="text-xs text-muted-foreground font-mono">{(u.global_xp || 0).toLocaleString()} XP</span>
                </div>
                <div className="flex flex-wrap gap-3 mt-2">
                  {u.email_verified && <span className="flex items-center gap-1 text-[11px] text-green-500"><CheckCircle2 className="w-3 h-3" /> Verified</span>}
                  {u.telegram_handle && <span className="flex items-center gap-1 text-[11px] text-blue-400"><Bot className="w-3 h-3" /> @{u.telegram_handle}</span>}
                  {u.last_active_date && <span className="text-[11px] text-muted-foreground">Last active: {u.last_active_date}</span>}
                </div>
              </div>
            </div>

            {/* Projects & Progress */}
            <div>
              <h3 className="text-sm font-semibold text-foreground mb-3 flex items-center gap-2">
                <FolderKanban className="w-4 h-4" /> Project Access & Progress
              </h3>
              {projects.length === 0 ? (
                <div className="text-center py-8 border border-dashed border-border rounded-lg">
                  <FolderKanban className="w-6 h-6 mx-auto mb-1.5 text-muted-foreground/30" />
                  <p className="text-xs text-muted-foreground">No project activity yet</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {projects.map((p: any) => (
                    <div key={p.project_id} className="border border-border rounded-lg p-3 bg-card">
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-sm font-semibold text-foreground">{p.project_name}</span>
                        <div className="flex items-center gap-2">
                          <Badge variant="outline" className="text-[10px] px-1.5 py-0">{p.slot_count} slot{p.slot_count !== 1 ? "s" : ""}</Badge>
                          <span className="text-xs font-mono text-primary">{p.completed_tasks}/{p.total_tasks} tasks</span>
                        </div>
                      </div>
                      {/* Progress bar */}
                      <div className="h-1.5 bg-muted rounded-full overflow-hidden mb-2">
                        <div
                          className="h-full bg-primary rounded-full transition-all"
                          style={{ width: `${p.completion_pct}%` }}
                        />
                      </div>
                      <div className="text-[10px] text-muted-foreground mb-2">{p.completion_pct}% complete</div>
                      {/* Slots */}
                      {p.slots.length > 0 && (
                        <div className="flex flex-wrap gap-1.5 mt-2">
                          {p.slots.map((s: any) => (
                            <div key={s.id} className="flex items-center gap-1.5 bg-muted/40 border border-border rounded px-2 py-1">
                              <span className="text-[11px] font-black text-primary">{s.slot_name}</span>
                              {s.wallet_address && (
                                <span className="text-[10px] font-mono text-muted-foreground">{s.wallet_address.slice(0, 8)}…</span>
                              )}
                              {s.twitter_username && (
                                <span className="text-[10px] text-muted-foreground">{s.twitter_username}</span>
                              )}
                              {s.completions > 0 && (
                                <Badge className="text-[9px] px-1 py-0 bg-green-500/10 text-green-400 border-green-500/20">✓{s.completions}</Badge>
                              )}
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}
      </SheetContent>
    </Sheet>
  );
}

// ── Main Admin Page ───────────────────────────────────────────────────────────

export default function AdminPage() {
  const { user } = useAuth();

  if (!user || (user.role !== "owner" && user.role !== "manager")) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <Shield className="w-12 h-12 mx-auto mb-3 text-muted-foreground opacity-30" />
          <p className="text-muted-foreground">Admin access required</p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-6xl mx-auto">
      <div className="mb-6">
        <div className="flex items-center gap-2 mb-1">
          <div className="w-8 h-8 rounded-lg flex items-center justify-center" style={{ background: "linear-gradient(135deg,#7c3aed,#06b6d4)" }}>
            <Shield className="w-4 h-4 text-white" />
          </div>
          <h1 className="text-2xl font-bold text-foreground">Admin Panel</h1>
          <Badge className="ml-2 bg-primary/10 text-primary border-primary/30">AYZEN V4</Badge>
        </div>
        <p className="text-sm text-muted-foreground">Manage users, activation codes, referrals, and system health</p>
      </div>

      <Tabs defaultValue="users">
        <TabsList className="mb-6 w-full sm:w-auto">
          <TabsTrigger value="users" className="flex items-center gap-1.5">
            <Users className="w-4 h-4" /> Members
          </TabsTrigger>
          <TabsTrigger value="codes" className="flex items-center gap-1.5">
            <Key className="w-4 h-4" /> Invite Codes
          </TabsTrigger>
          <TabsTrigger value="referrals" className="flex items-center gap-1.5">
            <GitBranch className="w-4 h-4" /> Referrals
          </TabsTrigger>
          <TabsTrigger value="system" className="flex items-center gap-1.5">
            <Activity className="w-4 h-4" /> System
          </TabsTrigger>
        </TabsList>

        <TabsContent value="users"><UsersTab /></TabsContent>
        <TabsContent value="codes"><CodesTab /></TabsContent>
        <TabsContent value="referrals"><ReferralsTab /></TabsContent>
        <TabsContent value="system"><SystemTab /></TabsContent>
      </Tabs>
    </div>
  );
}
