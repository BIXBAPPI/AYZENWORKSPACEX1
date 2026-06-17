import { useState, useMemo } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Skeleton } from "@/components/ui/skeleton";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useToast } from "@/hooks/use-toast";
import {
  KeyRound, Plus, Eye, EyeOff, Copy, Trash2, Edit3, FolderOpen,
  Mail, Globe, Smartphone, CreditCard, Shield, Lock, Search, X
} from "lucide-react";

const ICONS = [
  { value: "key", label: "Key", Icon: KeyRound },
  { value: "mail", label: "Email", Icon: Mail },
  { value: "globe", label: "Website", Icon: Globe },
  { value: "phone", label: "Phone", Icon: Smartphone },
  { value: "card", label: "Payment", Icon: CreditCard },
  { value: "shield", label: "Security", Icon: Shield },
];

const COLORS = [
  "#6366f1", "#8b5cf6", "#ec4899", "#f43f5e", "#f97316",
  "#eab308", "#22c55e", "#06b6d4", "#3b82f6", "#64748b",
];

const DEFAULT_CATEGORIES = [
  { name: "Email Accounts", color: "#3b82f6", icon: "mail" },
  { name: "Social Media", color: "#8b5cf6", icon: "globe" },
  { name: "Banking & Finance", color: "#22c55e", icon: "card" },
  { name: "Security & 2FA", color: "#f43f5e", icon: "shield" },
  { name: "Other Passwords", color: "#64748b", icon: "key" },
];

function getIcon(name: string) {
  return ICONS.find(i => i.value === name)?.Icon ?? KeyRound;
}

async function apiFetch(path: string, opts?: RequestInit) {
  const res = await fetch(`/api/v1/accounts${path}`, {
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    ...opts,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Request failed" }));
    throw new Error(err.detail ?? "Request failed");
  }
  if (res.status === 204) return null;
  return res.json();
}

export default function AccountsPage() {
  const qc = useQueryClient();
  const { toast } = useToast();
  const [search, setSearch] = useState("");
  const [selectedCat, setSelectedCat] = useState<string | null>(null);
  const [revealedIds, setRevealedIds] = useState<Set<string>>(new Set());
  const [showAddCat, setShowAddCat] = useState(false);
  const [showAddAcc, setShowAddAcc] = useState(false);
  const [editAcc, setEditAcc] = useState<any | null>(null);

  const { data: categories, isLoading: catLoading } = useQuery({
    queryKey: ["account-categories"],
    queryFn: () => apiFetch("/categories"),
  });

  const { data: accounts, isLoading: accLoading } = useQuery({
    queryKey: ["accounts", selectedCat],
    queryFn: () => apiFetch(selectedCat ? `/?category_id=${selectedCat}` : "/"),
  });

  const deleteCatMut = useMutation({
    mutationFn: (id: string) => apiFetch(`/categories/${id}`, { method: "DELETE" }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["account-categories"] }); qc.invalidateQueries({ queryKey: ["accounts"] }); },
    onError: (e: any) => toast({ title: "Error", description: e.message, variant: "destructive" }),
  });

  const deleteAccMut = useMutation({
    mutationFn: (id: string) => apiFetch(`/${id}`, { method: "DELETE" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["accounts"] }),
    onError: (e: any) => toast({ title: "Error", description: e.message, variant: "destructive" }),
  });

  const filteredAccounts = useMemo(() => {
    if (!accounts) return [];
    if (!search) return accounts;
    const q = search.toLowerCase();
    return accounts.filter((a: any) =>
      a.label.toLowerCase().includes(q) ||
      a.email.toLowerCase().includes(q) ||
      a.username.toLowerCase().includes(q) ||
      a.url.toLowerCase().includes(q)
    );
  }, [accounts, search]);

  const copyToClipboard = (text: string, label: string) => {
    navigator.clipboard.writeText(text);
    toast({ title: `Copied ${label}`, description: "Copied to clipboard" });
  };

  const toggleReveal = (id: string) => {
    setRevealedIds(prev => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  };

  if (catLoading) {
    return (
      <div className="p-4 md:p-6 space-y-4">
        <Skeleton className="h-8 w-48" />
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
          {[1,2,3,4,5].map(i => <Skeleton key={i} className="h-20" />)}
        </div>
        <Skeleton className="h-64" />
      </div>
    );
  }

  const cats: any[] = categories ?? [];

  return (
    <div className="p-4 md:p-6 max-w-[1200px]">
      <div className="flex items-center justify-between mb-5">
        <div>
          <h1 className="text-xl md:text-2xl font-black text-foreground tracking-tight">Account Vault</h1>
          <p className="text-sm text-muted-foreground mt-0.5">Secure password &amp; access storage</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={() => setShowAddCat(true)}>
            <Plus className="w-3.5 h-3.5 mr-1.5" /> Category
          </Button>
          <Button size="sm" onClick={() => setShowAddAcc(true)} disabled={cats.length === 0}>
            <Plus className="w-3.5 h-3.5 mr-1.5" /> Account
          </Button>
        </div>
      </div>

      {/* Categories */}
      {cats.length === 0 ? (
        <EmptyCategories onAdd={() => setShowAddCat(true)} />
      ) : (
        <>
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-2 mb-5">
            <button
              onClick={() => setSelectedCat(null)}
              className={`rounded-sm border p-3 text-left transition-colors ${selectedCat === null ? "border-primary bg-primary/5" : "border-border hover:border-primary/40"}`}
            >
              <div className="w-7 h-7 rounded-sm bg-muted flex items-center justify-center mb-2">
                <FolderOpen className="w-3.5 h-3.5 text-muted-foreground" />
              </div>
              <div className="text-xs font-semibold text-foreground truncate">All</div>
              <div className="text-[10px] text-muted-foreground">{accounts?.length ?? 0} accounts</div>
            </button>
            {cats.map((cat: any) => {
              const Icon = getIcon(cat.icon);
              return (
                <button
                  key={cat.id}
                  onClick={() => setSelectedCat(selectedCat === cat.id ? null : cat.id)}
                  className={`rounded-sm border p-3 text-left transition-colors group relative ${selectedCat === cat.id ? "border-primary bg-primary/5" : "border-border hover:border-primary/40"}`}
                >
                  <div className="w-7 h-7 rounded-sm flex items-center justify-center mb-2" style={{ background: cat.color + "22" }}>
                    <Icon className="w-3.5 h-3.5" style={{ color: cat.color }} />
                  </div>
                  <div className="text-xs font-semibold text-foreground truncate pr-5">{cat.name}</div>
                  <div className="text-[10px] text-muted-foreground">{cat.account_count} accounts</div>
                  <button
                    className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity text-muted-foreground hover:text-destructive"
                    onClick={e => { e.stopPropagation(); if (confirm(`Delete "${cat.name}" and all its accounts?`)) deleteCatMut.mutate(cat.id); }}
                  >
                    <Trash2 className="w-3 h-3" />
                  </button>
                </button>
              );
            })}
          </div>

          {/* Search */}
          <div className="relative mb-4">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-muted-foreground" />
            <Input
              placeholder="Search accounts..."
              value={search}
              onChange={e => setSearch(e.target.value)}
              className="pl-8 h-8 text-sm"
            />
            {search && (
              <button onClick={() => setSearch("")} className="absolute right-2.5 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground">
                <X className="w-3.5 h-3.5" />
              </button>
            )}
          </div>

          {/* Accounts list */}
          {accLoading ? (
            <div className="space-y-2">{[1,2,3].map(i => <Skeleton key={i} className="h-20" />)}</div>
          ) : filteredAccounts.length === 0 ? (
            <div className="text-center py-16 text-sm text-muted-foreground">
              {search ? "No accounts match your search." : "No accounts yet — add one above."}
            </div>
          ) : (
            <div className="space-y-2">
              {filteredAccounts.map((acc: any) => (
                <AccountCard
                  key={acc.id}
                  acc={acc}
                  revealed={revealedIds.has(acc.id)}
                  onToggleReveal={() => toggleReveal(acc.id)}
                  onCopy={copyToClipboard}
                  onEdit={() => setEditAcc(acc)}
                  onDelete={() => { if (confirm(`Delete "${acc.label}"?`)) deleteAccMut.mutate(acc.id); }}
                />
              ))}
            </div>
          )}
        </>
      )}

      {/* Dialogs */}
      <AddCategoryDialog
        open={showAddCat}
        onClose={() => setShowAddCat(false)}
        onCreated={() => { qc.invalidateQueries({ queryKey: ["account-categories"] }); setShowAddCat(false); }}
      />
      {cats.length > 0 && (
        <AddAccountDialog
          open={showAddAcc}
          categories={cats}
          onClose={() => setShowAddAcc(false)}
          onCreated={() => { qc.invalidateQueries({ queryKey: ["accounts"] }); setShowAddAcc(false); }}
        />
      )}
      {editAcc && (
        <EditAccountDialog
          acc={editAcc}
          onClose={() => setEditAcc(null)}
          onSaved={() => { qc.invalidateQueries({ queryKey: ["accounts"] }); setEditAcc(null); }}
        />
      )}
    </div>
  );
}

function AccountCard({ acc, revealed, onToggleReveal, onCopy, onEdit, onDelete }: any) {
  const Icon = getIcon(
    // find icon from category_color
    "key"
  );
  return (
    <Card className="border-border">
      <CardContent className="p-4">
        <div className="flex items-start gap-3">
          <div className="w-9 h-9 rounded-sm flex items-center justify-center shrink-0" style={{ background: acc.category_color + "22" }}>
            <Lock className="w-4 h-4" style={{ color: acc.category_color }} />
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <span className="text-sm font-semibold text-foreground">{acc.label}</span>
              <Badge variant="outline" className="text-[9px] px-1 py-0" style={{ borderColor: acc.category_color + "60", color: acc.category_color }}>
                {acc.category_name}
              </Badge>
              {acc.url && (
                <a href={acc.url} target="_blank" rel="noopener noreferrer" className="text-[10px] text-muted-foreground hover:text-primary truncate max-w-[120px]">
                  <Globe className="w-3 h-3 inline mr-0.5" />{new URL(acc.url.startsWith("http") ? acc.url : "https://" + acc.url).hostname}
                </a>
              )}
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-x-4 gap-y-1">
              {acc.email && (
                <FieldRow label="Email" value={acc.email} onCopy={() => onCopy(acc.email, "email")} />
              )}
              {acc.username && (
                <FieldRow label="Username" value={acc.username} onCopy={() => onCopy(acc.username, "username")} />
              )}
              <div className="flex items-center gap-1.5">
                <span className="text-[10px] text-muted-foreground w-16 shrink-0">Password</span>
                <code className="text-xs font-mono text-foreground flex-1 truncate">
                  {revealed ? acc.password : "••••••••"}
                </code>
                <button onClick={onToggleReveal} className="text-muted-foreground hover:text-foreground shrink-0">
                  {revealed ? <EyeOff className="w-3 h-3" /> : <Eye className="w-3 h-3" />}
                </button>
                <button onClick={() => onCopy(acc.password, "password")} className="text-muted-foreground hover:text-foreground shrink-0">
                  <Copy className="w-3 h-3" />
                </button>
              </div>
            </div>
            {(acc.recovery_email || acc.recovery_phone || acc.recovery_codes) && (
              <div className="mt-2 pt-2 border-t border-border/60 grid grid-cols-1 sm:grid-cols-3 gap-x-4 gap-y-1">
                {acc.recovery_email && <FieldRow label="Recovery Email" value={acc.recovery_email} onCopy={() => onCopy(acc.recovery_email, "recovery email")} />}
                {acc.recovery_phone && <FieldRow label="Recovery Phone" value={acc.recovery_phone} onCopy={() => onCopy(acc.recovery_phone, "recovery phone")} />}
                {acc.recovery_codes && (
                  <div className="flex items-center gap-1.5">
                    <span className="text-[10px] text-muted-foreground w-16 shrink-0">Rec. Codes</span>
                    <code className="text-[10px] font-mono text-muted-foreground flex-1 truncate">{acc.recovery_codes}</code>
                    <button onClick={() => onCopy(acc.recovery_codes, "recovery codes")} className="text-muted-foreground hover:text-foreground shrink-0">
                      <Copy className="w-3 h-3" />
                    </button>
                  </div>
                )}
              </div>
            )}
            {acc.notes && (
              <p className="text-[10px] text-muted-foreground mt-1.5 italic">{acc.notes}</p>
            )}
          </div>
          <div className="flex flex-col gap-1 shrink-0">
            <button onClick={onEdit} className="text-muted-foreground hover:text-foreground transition-colors">
              <Edit3 className="w-3.5 h-3.5" />
            </button>
            <button onClick={onDelete} className="text-muted-foreground hover:text-destructive transition-colors">
              <Trash2 className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function FieldRow({ label, value, onCopy }: { label: string; value: string; onCopy: () => void }) {
  return (
    <div className="flex items-center gap-1.5">
      <span className="text-[10px] text-muted-foreground w-16 shrink-0">{label}</span>
      <span className="text-xs text-foreground flex-1 truncate">{value}</span>
      <button onClick={onCopy} className="text-muted-foreground hover:text-foreground shrink-0">
        <Copy className="w-3 h-3" />
      </button>
    </div>
  );
}

function EmptyCategories({ onAdd }: { onAdd: () => void }) {
  return (
    <div className="text-center py-16">
      <KeyRound className="w-10 h-10 text-muted-foreground/30 mx-auto mb-3" />
      <p className="text-sm font-medium text-foreground mb-1">No categories yet</p>
      <p className="text-xs text-muted-foreground mb-4">Create a category to start storing account passwords</p>
      <Button size="sm" onClick={onAdd}><Plus className="w-3.5 h-3.5 mr-1.5" /> Create Category</Button>
    </div>
  );
}

function AddCategoryDialog({ open, onClose, onCreated }: any) {
  const { toast } = useToast();
  const [name, setName] = useState("");
  const [color, setColor] = useState(COLORS[0]);
  const [icon, setIcon] = useState("key");
  const [preset, setPreset] = useState<number | null>(null);

  const mut = useMutation({
    mutationFn: (body: any) => apiFetch("/categories", { method: "POST", body: JSON.stringify(body) }),
    onSuccess: () => { onCreated(); setName(""); setColor(COLORS[0]); setIcon("key"); },
    onError: (e: any) => toast({ title: "Error", description: e.message, variant: "destructive" }),
  });

  const applyPreset = (i: number) => {
    const p = DEFAULT_CATEGORIES[i];
    setName(p.name); setColor(p.color); setIcon(p.icon); setPreset(i);
  };

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle className="text-base font-bold">New Category</DialogTitle>
        </DialogHeader>
        <div className="space-y-4 py-2">
          <div>
            <Label className="text-xs mb-1.5 block">Quick presets</Label>
            <div className="flex flex-wrap gap-1.5">
              {DEFAULT_CATEGORIES.map((p, i) => {
                const Icon = getIcon(p.icon);
                return (
                  <button key={i} onClick={() => applyPreset(i)}
                    className={`flex items-center gap-1.5 px-2 py-1 rounded-sm border text-xs transition-colors ${preset === i ? "border-primary bg-primary/5" : "border-border hover:border-primary/40"}`}
                  >
                    <Icon className="w-3 h-3" style={{ color: p.color }} />
                    {p.name}
                  </button>
                );
              })}
            </div>
          </div>
          <div>
            <Label htmlFor="cat-name" className="text-xs">Name</Label>
            <Input id="cat-name" value={name} onChange={e => setName(e.target.value)} placeholder="e.g. Social Media" className="mt-1 h-8 text-sm" />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label className="text-xs mb-1.5 block">Icon</Label>
              <div className="flex flex-wrap gap-1.5">
                {ICONS.map(({ value, Icon: I }) => (
                  <button key={value} onClick={() => setIcon(value)}
                    className={`w-8 h-8 rounded-sm border flex items-center justify-center transition-colors ${icon === value ? "border-primary bg-primary/5" : "border-border hover:border-primary/40"}`}
                  >
                    <I className="w-3.5 h-3.5 text-muted-foreground" />
                  </button>
                ))}
              </div>
            </div>
            <div>
              <Label className="text-xs mb-1.5 block">Color</Label>
              <div className="flex flex-wrap gap-1.5">
                {COLORS.map(c => (
                  <button key={c} onClick={() => setColor(c)}
                    className={`w-6 h-6 rounded-sm border-2 transition-all ${color === c ? "border-foreground scale-110" : "border-transparent"}`}
                    style={{ background: c }}
                  />
                ))}
              </div>
            </div>
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" size="sm" onClick={onClose}>Cancel</Button>
          <Button size="sm" disabled={!name || mut.isPending} onClick={() => mut.mutate({ name, color, icon })}>
            {mut.isPending ? "Creating..." : "Create"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function AddAccountDialog({ open, categories, onClose, onCreated }: any) {
  const { toast } = useToast();
  const [form, setForm] = useState({ category_id: categories[0]?.id ?? "", label: "", username: "", email: "", password: "", recovery_email: "", recovery_phone: "", recovery_codes: "", notes: "", url: "" });
  const [showPass, setShowPass] = useState(false);

  const mut = useMutation({
    mutationFn: (body: any) => apiFetch("/", { method: "POST", body: JSON.stringify(body) }),
    onSuccess: () => { onCreated(); setForm({ category_id: categories[0]?.id ?? "", label: "", username: "", email: "", password: "", recovery_email: "", recovery_phone: "", recovery_codes: "", notes: "", url: "" }); },
    onError: (e: any) => toast({ title: "Error", description: e.message, variant: "destructive" }),
  });

  const set = (k: string) => (e: any) => setForm(f => ({ ...f, [k]: e.target.value }));

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-lg max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="text-base font-bold">Add Account</DialogTitle>
        </DialogHeader>
        <div className="space-y-3 py-2">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label className="text-xs">Category *</Label>
              <Select value={form.category_id} onValueChange={v => setForm(f => ({ ...f, category_id: v }))}>
                <SelectTrigger className="h-8 text-sm mt-1"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {categories.map((c: any) => <SelectItem key={c.id} value={c.id}>{c.name}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label className="text-xs">Label *</Label>
              <Input value={form.label} onChange={set("label")} placeholder="e.g. Gmail Personal" className="h-8 text-sm mt-1" />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label className="text-xs">Email</Label>
              <Input type="email" value={form.email} onChange={set("email")} placeholder="user@example.com" className="h-8 text-sm mt-1" />
            </div>
            <div>
              <Label className="text-xs">Username</Label>
              <Input value={form.username} onChange={set("username")} placeholder="@username" className="h-8 text-sm mt-1" />
            </div>
          </div>
          <div>
            <Label className="text-xs">Password *</Label>
            <div className="relative mt-1">
              <Input type={showPass ? "text" : "password"} value={form.password} onChange={set("password")} placeholder="Password" className="h-8 text-sm pr-8" />
              <button type="button" onClick={() => setShowPass(v => !v)} className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground">
                {showPass ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
              </button>
            </div>
          </div>
          <div>
            <Label className="text-xs">URL</Label>
            <Input value={form.url} onChange={set("url")} placeholder="https://..." className="h-8 text-sm mt-1" />
          </div>
          <div className="pt-2 border-t border-border">
            <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground mb-2">Recovery Access</p>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label className="text-xs">Recovery Email</Label>
                <Input type="email" value={form.recovery_email} onChange={set("recovery_email")} placeholder="backup@example.com" className="h-8 text-sm mt-1" />
              </div>
              <div>
                <Label className="text-xs">Recovery Phone</Label>
                <Input value={form.recovery_phone} onChange={set("recovery_phone")} placeholder="+1 234 567 8900" className="h-8 text-sm mt-1" />
              </div>
            </div>
            <div className="mt-2">
              <Label className="text-xs">Recovery Codes</Label>
              <Textarea value={form.recovery_codes} onChange={set("recovery_codes")} placeholder="One code per line..." className="text-xs mt-1 font-mono h-16 resize-none" />
            </div>
          </div>
          <div>
            <Label className="text-xs">Notes</Label>
            <Textarea value={form.notes} onChange={set("notes")} placeholder="Any extra notes..." className="text-xs mt-1 h-14 resize-none" />
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" size="sm" onClick={onClose}>Cancel</Button>
          <Button size="sm" disabled={!form.label || !form.password || !form.category_id || mut.isPending} onClick={() => mut.mutate(form)}>
            {mut.isPending ? "Saving..." : "Save Account"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function EditAccountDialog({ acc, onClose, onSaved }: any) {
  const { toast } = useToast();
  const [form, setForm] = useState({ label: acc.label, username: acc.username, email: acc.email, password: acc.password, recovery_email: acc.recovery_email, recovery_phone: acc.recovery_phone, recovery_codes: acc.recovery_codes, notes: acc.notes, url: acc.url });
  const [showPass, setShowPass] = useState(false);

  const mut = useMutation({
    mutationFn: (body: any) => apiFetch(`/${acc.id}`, { method: "PATCH", body: JSON.stringify(body) }),
    onSuccess: () => onSaved(),
    onError: (e: any) => toast({ title: "Error", description: e.message, variant: "destructive" }),
  });

  const set = (k: string) => (e: any) => setForm(f => ({ ...f, [k]: e.target.value }));

  return (
    <Dialog open onOpenChange={onClose}>
      <DialogContent className="max-w-lg max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="text-base font-bold">Edit Account</DialogTitle>
        </DialogHeader>
        <div className="space-y-3 py-2">
          <div>
            <Label className="text-xs">Label</Label>
            <Input value={form.label} onChange={set("label")} className="h-8 text-sm mt-1" />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label className="text-xs">Email</Label>
              <Input type="email" value={form.email} onChange={set("email")} className="h-8 text-sm mt-1" />
            </div>
            <div>
              <Label className="text-xs">Username</Label>
              <Input value={form.username} onChange={set("username")} className="h-8 text-sm mt-1" />
            </div>
          </div>
          <div>
            <Label className="text-xs">Password</Label>
            <div className="relative mt-1">
              <Input type={showPass ? "text" : "password"} value={form.password} onChange={set("password")} className="h-8 text-sm pr-8" />
              <button type="button" onClick={() => setShowPass(v => !v)} className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground">
                {showPass ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
              </button>
            </div>
          </div>
          <div>
            <Label className="text-xs">URL</Label>
            <Input value={form.url} onChange={set("url")} className="h-8 text-sm mt-1" />
          </div>
          <div className="pt-2 border-t border-border">
            <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground mb-2">Recovery Access</p>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label className="text-xs">Recovery Email</Label>
                <Input type="email" value={form.recovery_email} onChange={set("recovery_email")} className="h-8 text-sm mt-1" />
              </div>
              <div>
                <Label className="text-xs">Recovery Phone</Label>
                <Input value={form.recovery_phone} onChange={set("recovery_phone")} className="h-8 text-sm mt-1" />
              </div>
            </div>
            <div className="mt-2">
              <Label className="text-xs">Recovery Codes</Label>
              <Textarea value={form.recovery_codes} onChange={set("recovery_codes")} className="text-xs mt-1 font-mono h-16 resize-none" />
            </div>
          </div>
          <div>
            <Label className="text-xs">Notes</Label>
            <Textarea value={form.notes} onChange={set("notes")} className="text-xs mt-1 h-14 resize-none" />
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" size="sm" onClick={onClose}>Cancel</Button>
          <Button size="sm" disabled={mut.isPending} onClick={() => mut.mutate(form)}>
            {mut.isPending ? "Saving..." : "Save Changes"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
