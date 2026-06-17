import { useState, useEffect, useCallback } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { useToast } from "@/hooks/use-toast";
import {
  Bot, Search, RefreshCw, Copy, Check, ExternalLink,
  Link2, Link2Off, Users, CheckCircle2, Clock, Zap,
} from "lucide-react";

const api = (path: string, opts?: RequestInit) =>
  fetch(`/api/v1${path}`, { credentials: "include", ...opts });

function CopyButton({ value, label = "Copy" }: { value: string; label?: string }) {
  const [copied, setCopied] = useState(false);
  const copy = async () => {
    await navigator.clipboard.writeText(value);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };
  return (
    <Button variant="outline" size="sm" className="h-7 gap-1.5 text-xs" onClick={copy}>
      {copied ? <Check className="w-3 h-3 text-green-500" /> : <Copy className="w-3 h-3" />}
      {copied ? "Copied!" : label}
    </Button>
  );
}

function StatCard({ label, value, icon: Icon, color }: {
  label: string; value: number | string; icon: any; color: string;
}) {
  return (
    <div className="bg-card border border-border rounded-lg p-4 flex items-center gap-3">
      <div className={`w-9 h-9 rounded-lg flex items-center justify-center ${color}`}>
        <Icon className="w-4 h-4 text-white" />
      </div>
      <div>
        <div className="text-xl font-bold text-foreground">{value}</div>
        <div className="text-xs text-muted-foreground">{label}</div>
      </div>
    </div>
  );
}

type LinkInfo = { link_code: string; command: string; bot_url: string | null };

export default function TelegramLinkPage() {
  const { toast } = useToast();
  const [users, setUsers] = useState<any[]>([]);
  const [total, setTotal] = useState(0);
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState<"all" | "linked" | "unlinked">("all");
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(false);
  const [linkInfo, setLinkInfo] = useState<Record<string, LinkInfo>>({});
  const [generating, setGenerating] = useState<Record<string, boolean>>({});
  const [botUsername, setBotUsername] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const r = await api(`/admin/users?q=${encodeURIComponent(search)}&page=${page}&limit=50`);
      const d = await r.json();
      const all: any[] = d.users || [];
      const filtered =
        filter === "linked" ? all.filter((u) => u.telegram_user_id) :
        filter === "unlinked" ? all.filter((u) => !u.telegram_user_id) :
        all;
      setUsers(filtered);
      setTotal(d.total || 0);
    } finally {
      setLoading(false);
    }
  }, [search, page, filter]);

  useEffect(() => { load(); }, [load]);

  const generateCode = async (userId: string) => {
    setGenerating(prev => ({ ...prev, [userId]: true }));
    try {
      const r = await api(`/admin/telegram-link-code/${userId}`);
      const d: LinkInfo = await r.json();
      setLinkInfo(prev => ({ ...prev, [userId]: d }));
      if (d.bot_url && !botUsername) {
        const m = d.bot_url.match(/t\.me\/([^?]+)/);
        if (m) setBotUsername(m[1]);
      }
    } catch {
      toast({ variant: "destructive", description: "Failed to generate link code." });
    } finally {
      setGenerating(prev => ({ ...prev, [userId]: false }));
    }
  };

  const linkedCount = users.filter(u => u.telegram_user_id).length;
  const unlinkedCount = users.filter(u => !u.telegram_user_id).length;

  return (
    <div className="p-6 space-y-6 max-w-6xl mx-auto">
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <div className="w-8 h-8 rounded-lg bg-blue-500/10 flex items-center justify-center">
              <Bot className="w-4 h-4 text-blue-400" />
            </div>
            <h1 className="text-xl font-bold text-foreground">Telegram Linking</h1>
          </div>
          <p className="text-sm text-muted-foreground">
            Generate one-time link codes for members to connect their Telegram account to the AYZEN bot.
          </p>
        </div>
        {botUsername && (
          <a
            href={`https://t.me/${botUsername}`}
            target="_blank"
            rel="noopener noreferrer"
          >
            <Button variant="outline" size="sm" className="gap-1.5 shrink-0">
              <ExternalLink className="w-3.5 h-3.5" />
              @{botUsername}
            </Button>
          </a>
        )}
      </div>

      <div className="grid grid-cols-3 gap-3">
        <StatCard label="Total Members" value={total} icon={Users} color="bg-primary" />
        <StatCard label="Telegram Linked" value={linkedCount} icon={Link2} color="bg-green-500" />
        <StatCard label="Not Yet Linked" value={unlinkedCount} icon={Link2Off} color="bg-orange-500" />
      </div>

      <div className="bg-card border border-border rounded-lg p-4">
        <div className="flex items-center gap-2 mb-4 flex-wrap">
          <div className="relative flex-1 min-w-[200px]">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <Input
              value={search}
              onChange={(e) => { setSearch(e.target.value); setPage(1); }}
              placeholder="Search members…"
              className="pl-8 h-8"
            />
          </div>
          <div className="flex items-center gap-1 bg-muted/40 rounded-md p-0.5">
            {(["all", "linked", "unlinked"] as const).map((f) => (
              <button
                key={f}
                onClick={() => { setFilter(f); setPage(1); }}
                className={`px-3 py-1 text-xs rounded font-medium transition-colors capitalize ${
                  filter === f
                    ? "bg-background text-foreground shadow-sm"
                    : "text-muted-foreground hover:text-foreground"
                }`}
              >
                {f}
              </button>
            ))}
          </div>
          <Button variant="outline" size="sm" className="h-8 gap-1.5" onClick={load} disabled={loading}>
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
            Refresh
          </Button>
        </div>

        <div className="rounded-md border border-border overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-muted/30">
              <tr>
                {["Member", "XP / Tier", "Telegram Status", "Link Code / Action"].map(h => (
                  <th key={h} className="px-3 py-2.5 text-left text-xs font-semibold text-muted-foreground">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {users.map(u => {
                const info = linkInfo[u.id];
                const isLinked = !!u.telegram_user_id;
                const isGenerating = generating[u.id];
                return (
                  <tr key={u.id} className="border-t border-border hover:bg-muted/20 transition-colors">
                    <td className="px-3 py-3">
                      <div className="flex items-center gap-2.5">
                        <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center text-xs font-bold text-primary shrink-0">
                          {(u.full_name || u.email)?.[0]?.toUpperCase()}
                        </div>
                        <div className="min-w-0">
                          <div className="font-medium text-foreground truncate max-w-[180px]">
                            {u.full_name || u.username || "—"}
                          </div>
                          <div className="text-xs text-muted-foreground truncate max-w-[180px]">{u.email}</div>
                        </div>
                      </div>
                    </td>
                    <td className="px-3 py-3">
                      <div className="font-mono font-bold text-primary text-sm">
                        {(u.global_xp || 0).toLocaleString()} XP
                      </div>
                      <div className="text-xs text-muted-foreground mt-0.5">
                        <Badge variant="outline" className="text-[10px] capitalize px-1.5 py-0">{u.role}</Badge>
                      </div>
                    </td>
                    <td className="px-3 py-3">
                      {isLinked ? (
                        <div className="flex items-center gap-1.5">
                          <div className="w-5 h-5 rounded-full bg-green-500/10 flex items-center justify-center">
                            <CheckCircle2 className="w-3 h-3 text-green-500" />
                          </div>
                          <div>
                            <div className="text-xs font-medium text-green-500">Linked</div>
                            {u.telegram_handle && (
                              <div className="text-xs text-muted-foreground">@{u.telegram_handle}</div>
                            )}
                          </div>
                        </div>
                      ) : (
                        <div className="flex items-center gap-1.5">
                          <div className="w-5 h-5 rounded-full bg-orange-500/10 flex items-center justify-center">
                            <Link2Off className="w-3 h-3 text-orange-400" />
                          </div>
                          <div className="text-xs text-orange-400 font-medium">Not linked</div>
                        </div>
                      )}
                    </td>
                    <td className="px-3 py-3">
                      {isLinked ? (
                        <span className="text-xs text-muted-foreground italic">—</span>
                      ) : info ? (
                        <div className="space-y-1.5">
                          <div className="flex items-center gap-1.5 flex-wrap">
                            <code className="text-xs bg-muted px-2 py-0.5 rounded font-mono text-foreground">
                              {info.command}
                            </code>
                            <CopyButton value={info.command} label="Copy command" />
                          </div>
                          {info.bot_url && (
                            <a href={info.bot_url} target="_blank" rel="noopener noreferrer">
                              <Button size="sm" className="h-7 gap-1.5 text-xs bg-blue-500 hover:bg-blue-600 text-white border-0">
                                <ExternalLink className="w-3 h-3" />
                                Open in Telegram
                              </Button>
                            </a>
                          )}
                          <div className="flex items-center gap-1 text-[11px] text-muted-foreground">
                            <Clock className="w-3 h-3" />
                            Valid 24 hours
                          </div>
                        </div>
                      ) : (
                        <Button
                          size="sm"
                          variant="outline"
                          className="h-7 gap-1.5 text-xs"
                          disabled={isGenerating}
                          onClick={() => generateCode(u.id)}
                        >
                          {isGenerating ? (
                            <RefreshCw className="w-3 h-3 animate-spin" />
                          ) : (
                            <Zap className="w-3 h-3" />
                          )}
                          {isGenerating ? "Generating…" : "Generate Code"}
                        </Button>
                      )}
                    </td>
                  </tr>
                );
              })}
              {!loading && users.length === 0 && (
                <tr>
                  <td colSpan={4} className="text-center py-12 text-muted-foreground text-sm">
                    <Bot className="w-8 h-8 mx-auto mb-2 opacity-30" />
                    No members found
                  </td>
                </tr>
              )}
              {loading && (
                <tr>
                  <td colSpan={4} className="text-center py-8 text-muted-foreground text-sm">
                    <RefreshCw className="w-4 h-4 mx-auto animate-spin" />
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        {total > 50 && (
          <div className="flex items-center justify-between mt-3">
            <span className="text-xs text-muted-foreground">
              Showing {users.length} of {total}
            </span>
            <div className="flex gap-2">
              <Button variant="outline" size="sm" disabled={page === 1} onClick={() => setPage(p => p - 1)}>
                Previous
              </Button>
              <Button variant="outline" size="sm" disabled={users.length < 50} onClick={() => setPage(p => p + 1)}>
                Next
              </Button>
            </div>
          </div>
        )}
      </div>

      <div className="bg-blue-500/5 border border-blue-500/20 rounded-lg p-4">
        <div className="flex items-start gap-3">
          <Bot className="w-4 h-4 text-blue-400 mt-0.5 shrink-0" />
          <div className="text-xs text-muted-foreground space-y-1">
            <p className="font-medium text-foreground">How it works</p>
            <p>1. Click <strong>Generate Code</strong> next to a member's name — a unique one-time code is created (valid 24 hours).</p>
            <p>2. Share the <code className="bg-muted px-1 rounded">/link {"{code}"}</code> command with the member, or send them the <strong>Open in Telegram</strong> deep link.</p>
            <p>3. The member pastes the command into the AYZEN bot on Telegram — their account is instantly linked.</p>
          </div>
        </div>
      </div>
    </div>
  );
}
