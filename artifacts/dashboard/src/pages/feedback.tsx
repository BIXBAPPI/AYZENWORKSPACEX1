import { useState, useEffect, useCallback } from "react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { useToast } from "@/hooks/use-toast";
import { useAuth } from "@/lib/auth";
import {
  MessageSquare, Star, Check, Search, RefreshCw, Send, Filter,
} from "lucide-react";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle,
} from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

const api = (path: string, opts?: RequestInit) =>
  fetch(`/api/v1${path}`, { credentials: "include", ...opts });

function StarRating({ value }: { value: number }) {
  return (
    <div className="flex gap-0.5">
      {[1, 2, 3, 4, 5].map((s) => (
        <Star
          key={s}
          className={`w-3.5 h-3.5 ${s <= value ? "fill-yellow-400 text-yellow-400" : "text-muted-foreground/30"}`}
        />
      ))}
    </div>
  );
}

export default function FeedbackPage() {
  const { user } = useAuth();
  const { toast } = useToast();
  const isAdmin = user?.role === "owner" || user?.role === "manager";
  const [items, setItems] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [filterStatus, setFilterStatus] = useState("all");
  const [filterRating, setFilterRating] = useState("all");
  const [replyTarget, setReplyTarget] = useState<any>(null);
  const [reply, setReply] = useState("");
  const [replying, setReplying] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    const r = await api("/tutorials/admin/feedback");
    if (r.ok) setItems(await r.json());
    setLoading(false);
  }, []);

  useEffect(() => { load(); }, [load]);

  const sendReply = async () => {
    if (!reply.trim() || !replyTarget) return;
    setReplying(true);
    const r = await api(`/tutorials/admin/feedback/${replyTarget.id}/reply`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ reply }),
    });
    setReplying(false);
    if (r.ok) {
      toast({ title: "Reply sent" });
      setReplyTarget(null);
      setReply("");
      load();
    }
  };

  const filtered = items.filter((f) => {
    if (search && !f.user_name?.toLowerCase().includes(search.toLowerCase()) && !f.tutorial_title?.toLowerCase().includes(search.toLowerCase())) return false;
    if (filterStatus !== "all" && f.status !== filterStatus) return false;
    if (filterRating !== "all" && String(f.rating) !== filterRating) return false;
    return true;
  });

  const stats = {
    total: items.length,
    pending: items.filter((f) => f.status === "pending").length,
    avgRating: items.length ? (items.reduce((s, f) => s + f.rating, 0) / items.length).toFixed(1) : "—",
  };

  if (!isAdmin) {
    return (
      <div className="p-6 text-center text-muted-foreground">
        <MessageSquare className="w-12 h-12 mx-auto mb-3 opacity-30" />
        <p>Admin access required to view feedback.</p>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6 max-w-4xl mx-auto">
      <Dialog open={!!replyTarget} onOpenChange={() => setReplyTarget(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Reply to Feedback</DialogTitle>
          </DialogHeader>
          {replyTarget && (
            <div className="space-y-4">
              <div className="p-3 bg-muted/40 rounded-lg border border-border text-sm">
                <div className="flex items-center gap-2 mb-1">
                  <span className="font-medium">{replyTarget.user_name}</span>
                  <StarRating value={replyTarget.rating} />
                </div>
                <p className="text-muted-foreground">{replyTarget.comment || "(no comment)"}</p>
              </div>
              <div className="space-y-1.5">
                <Textarea
                  value={reply}
                  onChange={(e) => setReply(e.target.value)}
                  placeholder="Your reply..."
                  rows={3}
                />
              </div>
              <div className="flex justify-end gap-2">
                <Button variant="outline" onClick={() => setReplyTarget(null)}>Cancel</Button>
                <Button onClick={sendReply} disabled={replying || !reply.trim()}>
                  {replying ? <RefreshCw className="w-4 h-4 mr-1 animate-spin" /> : <Send className="w-4 h-4 mr-1" />}
                  Send Reply
                </Button>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>

      <div>
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <MessageSquare className="w-6 h-6 text-primary" /> Feedback Center
        </h1>
        <p className="text-muted-foreground text-sm mt-0.5">User feedback from tutorials</p>
      </div>

      <div className="grid grid-cols-3 gap-3">
        {[
          { label: "Total Feedback", value: stats.total, color: "text-primary" },
          { label: "Pending Review", value: stats.pending, color: "text-yellow-400" },
          { label: "Avg Rating", value: stats.avgRating, color: "text-green-400" },
        ].map(({ label, value, color }) => (
          <Card key={label} className="border-border">
            <CardContent className="p-4">
              <div className={`text-2xl font-bold ${color}`}>{value}</div>
              <div className="text-xs text-muted-foreground">{label}</div>
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="flex gap-3 flex-wrap">
        <div className="relative flex-1 min-w-[200px]">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <Input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search user or tutorial..." className="pl-9" />
        </div>
        <Select value={filterStatus} onValueChange={setFilterStatus}>
          <SelectTrigger className="w-36"><SelectValue placeholder="Status" /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Status</SelectItem>
            <SelectItem value="pending">Pending</SelectItem>
            <SelectItem value="resolved">Resolved</SelectItem>
          </SelectContent>
        </Select>
        <Select value={filterRating} onValueChange={setFilterRating}>
          <SelectTrigger className="w-36"><SelectValue placeholder="Rating" /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Ratings</SelectItem>
            {[5, 4, 3, 2, 1].map((r) => (
              <SelectItem key={r} value={String(r)}>{r} Stars</SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Button variant="outline" size="icon" onClick={load}>
          <RefreshCw className="w-4 h-4" />
        </Button>
      </div>

      {loading ? (
        <div className="text-center py-12 text-muted-foreground">Loading feedback...</div>
      ) : filtered.length === 0 ? (
        <div className="text-center py-12 space-y-2">
          <MessageSquare className="w-10 h-10 text-muted-foreground/30 mx-auto" />
          <p className="text-muted-foreground text-sm">
            {items.length === 0 ? "No feedback yet" : "No feedback matches your filters"}
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {filtered.map((f) => (
            <Card key={f.id} className="border-border">
              <CardContent className="p-4">
                <div className="flex items-start gap-3">
                  <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center text-xs font-bold text-primary shrink-0">
                    {f.user_name?.[0]?.toUpperCase() || "?"}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="font-medium text-sm">{f.user_name}</span>
                      <StarRating value={f.rating} />
                      <Badge
                        variant="outline"
                        className={`text-[10px] ${f.status === "resolved"
                          ? "border-green-500/30 text-green-400"
                          : "border-yellow-500/30 text-yellow-400"
                        }`}
                      >
                        {f.status === "resolved" ? <Check className="w-2.5 h-2.5 mr-0.5" /> : null}
                        {f.status}
                      </Badge>
                    </div>
                    <div className="text-xs text-muted-foreground mt-0.5">
                      Tutorial: <span className="text-foreground">{f.tutorial_title}</span> ·{" "}
                      {f.created_at ? new Date(f.created_at).toLocaleDateString() : ""}
                    </div>
                    {f.comment && (
                      <p className="text-sm text-muted-foreground mt-2">{f.comment}</p>
                    )}
                    {f.admin_reply && (
                      <div className="mt-2 pl-3 border-l-2 border-primary/30">
                        <div className="text-xs text-primary font-medium mb-0.5">Admin reply:</div>
                        <p className="text-sm text-muted-foreground">{f.admin_reply}</p>
                      </div>
                    )}
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => { setReplyTarget(f); setReply(f.admin_reply || ""); }}
                  >
                    <MessageSquare className="w-3.5 h-3.5 mr-1" />
                    {f.admin_reply ? "Edit Reply" : "Reply"}
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
