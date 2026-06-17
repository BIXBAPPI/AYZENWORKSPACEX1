import { useEffect, useRef, useState } from "react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { useToast } from "@/hooks/use-toast";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Lock, Wallet, Share2, Shield, Copy, Eye, EyeOff, CheckCircle, Loader2, RotateCcw, Send, Coins, ArrowLeftRight, Users, Plus, Trash2, FolderKanban, Twitter, CheckCircle2 } from "lucide-react";

const api = (path: string, opts?: RequestInit) =>
  fetch(`/api/v1${path}`, { credentials: "include", ...opts });

function apiFetch(path: string, opts?: RequestInit) {
  return api(path, opts).then((r) => r.json());
}

function CopyButton({ value }: { value: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <Button
      variant="ghost"
      size="icon"
      className="h-8 w-8"
      onClick={() => {
        navigator.clipboard.writeText(value);
        setCopied(true);
        setTimeout(() => setCopied(false), 1500);
      }}
    >
      {copied ? <CheckCircle className="w-3.5 h-3.5 text-green-500" /> : <Copy className="w-3.5 h-3.5" />}
    </Button>
  );
}

function MaskedField({ label, value, onChange, onSave, placeholder }: {
  label: string; value: string; onChange: (v: string) => void; onSave: () => void; placeholder?: string;
}) {
  const [show, setShow] = useState(false);
  return (
    <div className="space-y-1.5">
      <Label className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">{label}</Label>
      <div className="flex gap-2">
        <div className="relative flex-1">
          <Input
            type={show ? "text" : "password"}
            value={value}
            onChange={(e) => onChange(e.target.value)}
            placeholder={placeholder}
            className="pr-10 font-mono text-sm"
          />
          <button className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground" onClick={() => setShow(!show)}>
            {show ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
          </button>
        </div>
        {value && <CopyButton value={value} />}
        <Button size="sm" onClick={onSave}>Save</Button>
      </div>
    </div>
  );
}

function WalletsTab({ vault, refresh }: { vault: any; refresh: () => void }) {
  const { toast } = useToast();
  const [fields, setFields] = useState({
    evm_address: "", solana_address: "", cosmos_address: "",
    sui_address: "", aptos_address: "", btc_address: "",
  });

  useEffect(() => {
    if (vault) {
      setFields({
        evm_address: vault.evm_address || "",
        solana_address: vault.solana_address || "",
        cosmos_address: vault.cosmos_address || "",
        sui_address: vault.sui_address || "",
        aptos_address: vault.aptos_address || "",
        btc_address: vault.btc_address || "",
      });
    }
  }, [vault]);

  const save = async (key: string, value: string) => {
    await apiFetch("/vault/", { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ [key]: value }) });
    toast({ title: "Saved", description: `${key.replace("_address", "").replace("_", " ").toUpperCase()} address saved.` });
    refresh();
  };

  const WALLETS = [
    { key: "evm_address", label: "EVM Address (Ethereum, Arbitrum, Base…)", placeholder: "0x…" },
    { key: "solana_address", label: "Solana Address", placeholder: "SOL public key" },
    { key: "cosmos_address", label: "Cosmos Address", placeholder: "cosmos1…" },
    { key: "sui_address", label: "Sui Address", placeholder: "0x…" },
    { key: "aptos_address", label: "Aptos Address", placeholder: "0x…" },
    { key: "btc_address", label: "Bitcoin Address", placeholder: "bc1… or 1… or 3…" },
  ] as const;

  return (
    <div className="space-y-5">
      {WALLETS.map(({ key, label, placeholder }) => (
        <MaskedField
          key={key}
          label={label}
          value={fields[key]}
          onChange={(v) => setFields((f) => ({ ...f, [key]: v }))}
          onSave={() => save(key, fields[key])}
          placeholder={placeholder}
        />
      ))}
    </div>
  );
}

function SocialsTab({ vault, refresh }: { vault: any; refresh: () => void }) {
  const { toast } = useToast();
  const [fields, setFields] = useState({ twitter: "", discord: "", telegram: "", github: "" });

  useEffect(() => {
    if (vault) {
      setFields({
        twitter: vault.twitter || "",
        discord: vault.discord || "",
        telegram: vault.telegram || "",
        github: vault.github || "",
      });
    }
  }, [vault]);

  const save = async (key: string, value: string) => {
    await apiFetch("/vault/", { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ [key]: value }) });
    toast({ title: "Saved" });
    refresh();
  };

  const SOCIALS = [
    { key: "twitter", label: "Twitter / X Handle", placeholder: "@username" },
    { key: "discord", label: "Discord Username", placeholder: "user#1234 or username" },
    { key: "telegram", label: "Telegram Username", placeholder: "@username" },
    { key: "github", label: "GitHub Username", placeholder: "username" },
  ] as const;

  return (
    <div className="space-y-5">
      {SOCIALS.map(({ key, label, placeholder }) => (
        <div key={key} className="space-y-1.5">
          <Label className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">{label}</Label>
          <div className="flex gap-2">
            <Input
              value={fields[key]}
              onChange={(e) => setFields((f) => ({ ...f, [key]: e.target.value }))}
              placeholder={placeholder}
              className="font-mono text-sm"
            />
            <Button size="sm" onClick={() => save(key, fields[key])}>Save</Button>
          </div>
        </div>
      ))}
    </div>
  );
}

function TotpDisplay({ secret }: { secret: boolean }) {
  const [code, setCode] = useState<{ code: string; remaining: number } | null>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchCode = async () => {
    try {
      const data = await apiFetch("/vault/totp/generate");
      if (data.code) setCode({ code: data.code, remaining: data.remaining_seconds });
    } catch { /* ignore */ }
  };

  useEffect(() => {
    if (!secret) return;
    fetchCode();
    intervalRef.current = setInterval(fetchCode, 5000);
    return () => { if (intervalRef.current) clearInterval(intervalRef.current); };
  }, [secret]);

  if (!code) return null;

  const pct = (code.remaining / 30) * 100;
  const color = code.remaining > 10 ? "#22c55e" : code.remaining > 5 ? "#f59e0b" : "#ef4444";

  return (
    <div className="flex items-center gap-4 p-4 rounded-lg bg-muted/30 border border-border">
      <div className="relative w-14 h-14">
        <svg viewBox="0 0 56 56" className="w-14 h-14 -rotate-90">
          <circle cx="28" cy="28" r="24" fill="none" stroke="currentColor" strokeWidth="4" className="text-muted" />
          <circle cx="28" cy="28" r="24" fill="none" stroke={color} strokeWidth="4"
            strokeDasharray={`${2 * Math.PI * 24}`}
            strokeDashoffset={`${2 * Math.PI * 24 * (1 - pct / 100)}`}
            strokeLinecap="round"
          />
        </svg>
        <span className="absolute inset-0 flex items-center justify-center text-xs font-bold">{code.remaining}s</span>
      </div>
      <div>
        <p className="text-xs text-muted-foreground mb-1">Current TOTP Code</p>
        <p className="text-3xl font-black tracking-widest" style={{ color }}>{code.code}</p>
      </div>
      <CopyButton value={code.code} />
    </div>
  );
}

function TwoFATab({ vault, refresh }: { vault: any; refresh: () => void }) {
  const { toast } = useToast();
  const [qr, setQr] = useState<{ secret: string; uri: string } | null>(null);
  const [verifyCode, setVerifyCode] = useState("");
  const [disableCode, setDisableCode] = useState("");
  const [loading, setLoading] = useState(false);
  const [emailCode, setEmailCode] = useState("");
  const [emailSent, setEmailSent] = useState(false);

  const enabled = vault?.totp_enabled;

  const enableTotp = async () => {
    setLoading(true);
    try {
      const data = await apiFetch("/vault/totp/enable", { method: "POST" });
      setQr(data);
    } catch (e: any) {
      toast({ title: "Error", description: e.message, variant: "destructive" });
    } finally { setLoading(false); }
  };

  const verifyTotp = async () => {
    setLoading(true);
    try {
      await apiFetch("/vault/totp/verify", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ code: verifyCode }) });
      toast({ title: "2FA Enabled ✅", description: "TOTP authentication is now active." });
      setQr(null);
      refresh();
    } catch {
      toast({ title: "Invalid code", description: "Check the code and try again.", variant: "destructive" });
    } finally { setLoading(false); }
  };

  const disableTotp = async () => {
    setLoading(true);
    try {
      await apiFetch("/vault/totp/disable", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ code: disableCode }) });
      toast({ title: "2FA Disabled" });
      refresh();
    } catch {
      toast({ title: "Invalid code", variant: "destructive" });
    } finally { setLoading(false); }
  };

  const sendEmail = async () => {
    try {
      await apiFetch("/vault/email-otp/send", { method: "POST" });
      setEmailSent(true);
      toast({ title: "Code sent to your email" });
    } catch { toast({ title: "Failed to send email", variant: "destructive" }); }
  };

  const verifyEmail = async () => {
    try {
      await apiFetch("/vault/email-otp/verify", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ code: emailCode }) });
      toast({ title: "Email code verified ✅" });
      setEmailCode("");
      setEmailSent(false);
    } catch { toast({ title: "Invalid or expired code", variant: "destructive" }); }
  };

  return (
    <div className="space-y-6">
      {/* TOTP Section */}
      <Card className="border-border">
        <CardHeader className="pb-3">
          <CardTitle className="text-base flex items-center gap-2">
            <Shield className="w-4 h-4 text-primary" />
            Authenticator App (TOTP)
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {enabled ? (
            <>
              <div className="flex items-center gap-2">
                <CheckCircle className="w-5 h-5 text-green-500" />
                <span className="font-semibold text-green-500">2FA is ACTIVE</span>
              </div>
              <TotpDisplay secret={enabled} />
              <div className="pt-2 border-t border-border">
                <p className="text-xs text-muted-foreground mb-2">Enter your 6-digit code to disable 2FA</p>
                <div className="flex gap-2">
                  <Input value={disableCode} onChange={(e) => setDisableCode(e.target.value)} maxLength={6} placeholder="000000" className="max-w-[140px] font-mono tracking-widest" />
                  <Button variant="destructive" onClick={disableTotp} disabled={loading || disableCode.length !== 6}>
                    {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : "Disable 2FA"}
                  </Button>
                </div>
              </div>
            </>
          ) : qr ? (
            <div className="space-y-4">
              <div className="p-4 bg-white rounded-lg inline-block">
                <img src={`https://api.qrserver.com/v1/create-qr-code/?size=160x160&data=${encodeURIComponent(qr.uri)}`} alt="QR code" className="w-40 h-40" />
              </div>
              <div>
                <p className="text-xs text-muted-foreground mb-1">Manual entry secret:</p>
                <div className="flex items-center gap-2">
                  <code className="text-xs bg-muted px-2 py-1 rounded font-mono">{qr.secret}</code>
                  <CopyButton value={qr.secret} />
                </div>
              </div>
              <div>
                <p className="text-xs text-muted-foreground mb-2">Enter the 6-digit code from your authenticator app to confirm:</p>
                <div className="flex gap-2">
                  <Input value={verifyCode} onChange={(e) => setVerifyCode(e.target.value)} maxLength={6} placeholder="000000" className="max-w-[140px] font-mono tracking-widest" />
                  <Button onClick={verifyTotp} disabled={loading || verifyCode.length !== 6}>
                    {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : "Verify & Enable"}
                  </Button>
                </div>
              </div>
            </div>
          ) : (
            <Button onClick={enableTotp} disabled={loading} className="gap-2">
              {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Shield className="w-4 h-4" />}
              Enable 2FA
            </Button>
          )}
        </CardContent>
      </Card>

      {/* Email OTP Section */}
      <Card className="border-border">
        <CardHeader className="pb-3">
          <CardTitle className="text-base flex items-center gap-2">
            <Send className="w-4 h-4 text-primary" />
            Email OTP
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-sm text-muted-foreground">Receive a 6-digit one-time code to your email.</p>
          <Button variant="outline" onClick={sendEmail} className="gap-2">
            <Send className="w-4 h-4" />
            {emailSent ? "Resend Code" : "Send Code to Email"}
          </Button>
          {emailSent && (
            <div className="flex gap-2">
              <Input value={emailCode} onChange={(e) => setEmailCode(e.target.value)} maxLength={6} placeholder="000000" className="max-w-[140px] font-mono tracking-widest" />
              <Button onClick={verifyEmail} disabled={emailCode.length !== 6}>Verify Code</Button>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function XPWalletTab() {
  const { toast } = useToast();
  const [balance, setBalance] = useState<any>(null);
  const [txs, setTxs] = useState<any[]>([]);
  const [toUser, setToUser] = useState("");
  const [amount, setAmount] = useState("");
  const [note, setNote] = useState("");
  const [sending, setSending] = useState(false);

  const loadData = async () => {
    const [b, t] = await Promise.all([
      apiFetch("/wallet/balance"),
      apiFetch("/wallet/transactions"),
    ]);
    setBalance(b);
    setTxs(Array.isArray(t) ? t : []);
  };

  useEffect(() => { loadData(); }, []);

  const transfer = async () => {
    if (!toUser || !amount) return;
    setSending(true);
    try {
      await apiFetch("/wallet/transfer", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ to_username: toUser, amount: parseInt(amount), note }),
      });
      toast({ title: "XP Transferred ✅" });
      setToUser(""); setAmount(""); setNote("");
      loadData();
    } catch (e: any) {
      toast({ title: "Transfer failed", description: e.message, variant: "destructive" });
    } finally { setSending(false); }
  };

  const TIER_COLORS: Record<string, string> = {
    Bronze: "text-amber-600", Silver: "text-slate-400", Gold: "text-yellow-500", Platinum: "text-slate-200",
  };

  return (
    <div className="space-y-5">
      {balance && (
        <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
          <Card className="border-border">
            <CardContent className="p-4">
              <p className="text-xs text-muted-foreground">Total XP</p>
              <p className="text-2xl font-black text-foreground">{balance.xp?.toLocaleString()}</p>
              <span className={`text-xs font-bold ${TIER_COLORS[balance.tier] ?? "text-muted-foreground"}`}>{balance.tier}</span>
            </CardContent>
          </Card>
          <Card className="border-border">
            <CardContent className="p-4">
              <p className="text-xs text-muted-foreground">Transferable XP</p>
              <p className="text-2xl font-black text-primary">{balance.xp_transferable?.toLocaleString()}</p>
            </CardContent>
          </Card>
        </div>
      )}

      <Card className="border-border">
        <CardHeader className="pb-3">
          <CardTitle className="text-base flex items-center gap-2">
            <ArrowLeftRight className="w-4 h-4 text-primary" />
            Transfer XP
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label className="text-xs text-muted-foreground">To (username or email)</Label>
              <Input value={toUser} onChange={(e) => setToUser(e.target.value)} placeholder="username" />
            </div>
            <div>
              <Label className="text-xs text-muted-foreground">Amount</Label>
              <Input type="number" value={amount} onChange={(e) => setAmount(e.target.value)} placeholder="100" min={1} />
            </div>
          </div>
          <div>
            <Label className="text-xs text-muted-foreground">Note (optional)</Label>
            <Input value={note} onChange={(e) => setNote(e.target.value)} placeholder="Bonus for task completion" />
          </div>
          <Button onClick={transfer} disabled={sending || !toUser || !amount} className="gap-2">
            {sending ? <Loader2 className="w-4 h-4 animate-spin" /> : <ArrowLeftRight className="w-4 h-4" />}
            Transfer
          </Button>
        </CardContent>
      </Card>

      <Card className="border-border">
        <CardHeader className="pb-3">
          <CardTitle className="text-sm">Transaction History</CardTitle>
        </CardHeader>
        <CardContent>
          {txs.length === 0 ? (
            <p className="text-sm text-muted-foreground">No transactions yet.</p>
          ) : (
            <div className="space-y-2">
              {txs.map((tx) => (
                <div key={tx.id} className="flex items-center justify-between py-2 border-b border-border last:border-0">
                  <div>
                    <p className="text-sm font-medium">{tx.type === "sent" ? `→ ${tx.counterpart}` : `← ${tx.counterpart}`}</p>
                    {tx.note && <p className="text-xs text-muted-foreground">{tx.note}</p>}
                  </div>
                  <div className="text-right">
                    <p className={`text-sm font-bold ${tx.type === "sent" ? "text-red-400" : "text-green-400"}`}>
                      {tx.type === "sent" ? "-" : "+"}{tx.amount} XP
                    </p>
                    <p className="text-[10px] text-muted-foreground">{new Date(tx.created_at).toLocaleDateString()}</p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

// ── Accounts (Multi-Account Slots) Tab ───────────────────────────────────────

type Slot = {
  id: string; project_id: string; project_name: string; slot_name: string;
  wallet_address: string | null; twitter_username: string | null; discord_username: string | null;
  completions: number;
};

function AccountsTab() {
  const { toast } = useToast();
  const [slots, setSlots] = useState<Slot[]>([]);
  const [projects, setProjects] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedProject, setSelectedProject] = useState<string>("all");
  const [showAdd, setShowAdd] = useState(false);
  const [editSlot, setEditSlot] = useState<Slot | null>(null);
  const [deleting, setDeleting] = useState<string | null>(null);
  const [form, setForm] = useState({ project_id: "", slot_name: "", wallet_address: "", twitter_username: "", discord_username: "" });
  const [saving, setSaving] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const [slotsData, projData] = await Promise.all([
        apiFetch("/progress/slots"),
        apiFetch("/projects/"),
      ]);
      setSlots(Array.isArray(slotsData) ? slotsData : []);
      setProjects(Array.isArray(projData) ? projData : []);
    } finally { setLoading(false); }
  };

  useEffect(() => { load(); }, []);

  const filtered = selectedProject === "all" ? slots : slots.filter(s => s.project_id === selectedProject);

  const grouped = filtered.reduce<Record<string, Slot[]>>((acc, s) => {
    (acc[s.project_name] = acc[s.project_name] || []).push(s);
    return acc;
  }, {});

  const openAdd = () => {
    setForm({ project_id: projects[0]?.id || "", slot_name: "", wallet_address: "", twitter_username: "", discord_username: "" });
    setShowAdd(true);
  };

  const openEdit = (s: Slot) => {
    setEditSlot(s);
    setForm({ project_id: s.project_id, slot_name: s.slot_name, wallet_address: s.wallet_address || "", twitter_username: s.twitter_username || "", discord_username: s.discord_username || "" });
  };

  const createSlot = async () => {
    if (!form.project_id || !form.slot_name.trim()) return;
    setSaving(true);
    try {
      const r = await api("/progress/slots", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(form) });
      if (r.ok) { toast({ title: "Account added ✅" }); setShowAdd(false); load(); }
      else {
        const d = await r.json();
        toast({ title: d.detail === "slot_name_exists" ? "Slot name already exists for this project" : "Failed to create slot", variant: "destructive" });
      }
    } finally { setSaving(false); }
  };

  const saveEdit = async () => {
    if (!editSlot) return;
    setSaving(true);
    try {
      const { project_id: _, ...update } = form;
      const r = await api(`/progress/slots/${editSlot.id}`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify(update) });
      if (r.ok) { toast({ title: "Updated ✅" }); setEditSlot(null); load(); }
      else toast({ title: "Failed to update", variant: "destructive" });
    } finally { setSaving(false); }
  };

  const deleteSlot = async (id: string) => {
    if (!confirm("Delete this account slot? This will also remove its task completion history.")) return;
    setDeleting(id);
    try {
      await api(`/progress/slots/${id}`, { method: "DELETE" });
      toast({ title: "Slot deleted" });
      load();
    } finally { setDeleting(null); }
  };

  const SLOT_NAMES = ["M1","M2","M3","M4","M5","M6","M7","M8","M9","M10","WEB","ALT1","ALT2","ALT3"];

  const SlotForm = ({ onSave, onCancel }: { onSave: () => void; onCancel: () => void }) => (
    <div className="space-y-3 py-2">
      {showAdd && (
        <div>
          <Label className="text-xs font-semibold uppercase tracking-wide text-muted-foreground block mb-1">Project</Label>
          <Select value={form.project_id} onValueChange={v => setForm(f => ({ ...f, project_id: v }))}>
            <SelectTrigger><SelectValue placeholder="Select project" /></SelectTrigger>
            <SelectContent>
              {projects.map(p => <SelectItem key={p.id} value={p.id}>{p.name}</SelectItem>)}
            </SelectContent>
          </Select>
        </div>
      )}
      <div>
        <Label className="text-xs font-semibold uppercase tracking-wide text-muted-foreground block mb-1">Slot Name</Label>
        <Select value={form.slot_name} onValueChange={v => setForm(f => ({ ...f, slot_name: v }))}>
          <SelectTrigger><SelectValue placeholder="e.g. M1, M2…" /></SelectTrigger>
          <SelectContent>
            {SLOT_NAMES.map(n => <SelectItem key={n} value={n}>{n}</SelectItem>)}
          </SelectContent>
        </Select>
      </div>
      <div>
        <Label className="text-xs font-semibold uppercase tracking-wide text-muted-foreground block mb-1">Wallet Address</Label>
        <Input value={form.wallet_address} onChange={e => setForm(f => ({ ...f, wallet_address: e.target.value }))} placeholder="0x… or solana address" className="font-mono text-xs" />
      </div>
      <div>
        <Label className="text-xs font-semibold uppercase tracking-wide text-muted-foreground block mb-1">Twitter / X Username</Label>
        <Input value={form.twitter_username} onChange={e => setForm(f => ({ ...f, twitter_username: e.target.value }))} placeholder="@username" />
      </div>
      <div>
        <Label className="text-xs font-semibold uppercase tracking-wide text-muted-foreground block mb-1">Discord Username</Label>
        <Input value={form.discord_username} onChange={e => setForm(f => ({ ...f, discord_username: e.target.value }))} placeholder="user#1234" />
      </div>
      <div className="flex gap-2 pt-1">
        <Button variant="outline" size="sm" onClick={onCancel}>Cancel</Button>
        <Button size="sm" disabled={saving || !form.slot_name} onClick={onSave}>
          {saving ? <Loader2 className="w-3.5 h-3.5 animate-spin mr-1" /> : null}
          Save
        </Button>
      </div>
    </div>
  );

  if (loading) return <div className="space-y-3">{Array.from({length:3}).map((_,i)=><div key={i} className="h-16 bg-muted/20 rounded-lg animate-pulse"/>)}</div>;

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3 flex-wrap">
        <div className="flex items-center gap-2 flex-1 min-w-[200px]">
          <FolderKanban className="w-4 h-4 text-muted-foreground shrink-0" />
          <Select value={selectedProject} onValueChange={setSelectedProject}>
            <SelectTrigger className="h-8 text-sm">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Projects ({slots.length} accounts)</SelectItem>
              {projects.map(p => {
                const count = slots.filter(s => s.project_id === p.id).length;
                return <SelectItem key={p.id} value={p.id}>{p.name} ({count})</SelectItem>;
              })}
            </SelectContent>
          </Select>
        </div>
        <Button size="sm" className="h-8 gap-1.5 shrink-0" onClick={openAdd}>
          <Plus className="w-3.5 h-3.5" /> Add Account
        </Button>
      </div>

      {Object.keys(grouped).length === 0 ? (
        <div className="py-16 text-center border border-dashed border-border rounded-lg">
          <Users className="w-8 h-8 mx-auto mb-2 text-muted-foreground/40" />
          <p className="text-sm font-medium text-muted-foreground">No account slots yet</p>
          <p className="text-xs text-muted-foreground mt-1">Add an account slot per project for multi-account task completion</p>
          <Button size="sm" className="mt-4 gap-1.5" onClick={openAdd}><Plus className="w-3.5 h-3.5" /> Add First Account</Button>
        </div>
      ) : (
        Object.entries(grouped).map(([projectName, projectSlots]) => (
          <div key={projectName}>
            <div className="flex items-center gap-2 mb-2">
              <FolderKanban className="w-3.5 h-3.5 text-muted-foreground" />
              <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">{projectName}</span>
              <Badge variant="outline" className="text-[10px] px-1.5 py-0">{projectSlots.length} slot{projectSlots.length !== 1 ? "s" : ""}</Badge>
            </div>
            <div className="space-y-2">
              {projectSlots.map(slot => (
                <div key={slot.id} className="border border-border rounded-lg p-3 bg-card">
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex items-center gap-2">
                      <div className="w-8 h-8 rounded-md bg-primary/10 flex items-center justify-center text-xs font-black text-primary shrink-0">{slot.slot_name}</div>
                      <div className="min-w-0 space-y-1">
                        {slot.wallet_address && (
                          <div className="flex items-center gap-1.5 text-xs">
                            <Wallet className="w-3 h-3 text-muted-foreground shrink-0" />
                            <code className="font-mono truncate max-w-[200px] text-foreground/80">{slot.wallet_address}</code>
                            <CopyButton value={slot.wallet_address} />
                          </div>
                        )}
                        {slot.twitter_username && (
                          <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                            <Twitter className="w-3 h-3 shrink-0" />
                            {slot.twitter_username}
                          </div>
                        )}
                        {slot.discord_username && (
                          <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                            <span className="w-3 h-3 shrink-0 text-center font-bold text-[10px]">DC</span>
                            {slot.discord_username}
                          </div>
                        )}
                        {!slot.wallet_address && !slot.twitter_username && !slot.discord_username && (
                          <span className="text-xs text-muted-foreground/50 italic">No details yet</span>
                        )}
                      </div>
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                      {slot.completions > 0 && (
                        <Badge variant="outline" className="text-[10px] px-1.5 py-0 text-green-500 border-green-500/30">
                          <CheckCircle2 className="w-2.5 h-2.5 mr-1" />{slot.completions}
                        </Badge>
                      )}
                      <Button variant="ghost" size="sm" className="h-6 w-6 p-0 text-muted-foreground hover:text-foreground" onClick={() => openEdit(slot)}>
                        <RotateCcw className="w-3 h-3" />
                      </Button>
                      <Button variant="ghost" size="sm" className="h-6 w-6 p-0 text-destructive hover:bg-destructive/10" disabled={deleting === slot.id} onClick={() => deleteSlot(slot.id)}>
                        {deleting === slot.id ? <Loader2 className="w-3 h-3 animate-spin" /> : <Trash2 className="w-3 h-3" />}
                      </Button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        ))
      )}

      <Dialog open={showAdd} onOpenChange={setShowAdd}>
        <DialogContent>
          <DialogHeader><DialogTitle className="font-black">Add Account Slot</DialogTitle></DialogHeader>
          <p className="text-xs text-muted-foreground -mt-2">Each slot represents a separate wallet/identity for multi-account task completion.</p>
          <SlotForm onSave={createSlot} onCancel={() => setShowAdd(false)} />
        </DialogContent>
      </Dialog>

      <Dialog open={!!editSlot} onOpenChange={() => setEditSlot(null)}>
        <DialogContent>
          <DialogHeader><DialogTitle className="font-black">Edit Slot — {editSlot?.slot_name}</DialogTitle></DialogHeader>
          <SlotForm onSave={saveEdit} onCancel={() => setEditSlot(null)} />
        </DialogContent>
      </Dialog>
    </div>
  );
}

export default function AccountVault() {
  const [vault, setVault] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  const refresh = async () => {
    setLoading(true);
    try {
      const data = await apiFetch("/vault/");
      setVault(data);
    } catch { /* ignore */ }
    setLoading(false);
  };

  useEffect(() => { refresh(); }, []);

  return (
    <div className="p-4 md:p-6 max-w-3xl">
      <div className="flex items-center gap-3 mb-6">
        <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center">
          <Lock className="w-6 h-6 text-primary" />
        </div>
        <div>
          <h1 className="text-2xl font-black text-foreground">Account Vault</h1>
          <p className="text-xs text-muted-foreground">Secure storage for wallets, socials, and 2FA</p>
        </div>
        <Button variant="ghost" size="icon" className="ml-auto" onClick={refresh} disabled={loading}>
          <RotateCcw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
        </Button>
      </div>

      {loading && !vault ? (
        <div className="space-y-3">
          {Array.from({ length: 3 }).map((_, i) => <div key={i} className="h-16 bg-muted/20 rounded-lg animate-pulse" />)}
        </div>
      ) : (
        <Tabs defaultValue="wallets">
          <TabsList className="mb-6 flex-wrap h-auto">
            <TabsTrigger value="wallets" className="gap-1.5"><Wallet className="w-3.5 h-3.5" />Wallets</TabsTrigger>
            <TabsTrigger value="socials" className="gap-1.5"><Share2 className="w-3.5 h-3.5" />Socials</TabsTrigger>
            <TabsTrigger value="accounts" className="gap-1.5"><Users className="w-3.5 h-3.5" />Accounts</TabsTrigger>
            <TabsTrigger value="2fa" className="gap-1.5"><Shield className="w-3.5 h-3.5" />2FA</TabsTrigger>
            <TabsTrigger value="xp" className="gap-1.5"><Coins className="w-3.5 h-3.5" />XP Wallet</TabsTrigger>
          </TabsList>
          <TabsContent value="wallets"><WalletsTab vault={vault} refresh={refresh} /></TabsContent>
          <TabsContent value="socials"><SocialsTab vault={vault} refresh={refresh} /></TabsContent>
          <TabsContent value="accounts"><AccountsTab /></TabsContent>
          <TabsContent value="2fa"><TwoFATab vault={vault} refresh={refresh} /></TabsContent>
          <TabsContent value="xp"><XPWalletTab /></TabsContent>
        </Tabs>
      )}
    </div>
  );
}
