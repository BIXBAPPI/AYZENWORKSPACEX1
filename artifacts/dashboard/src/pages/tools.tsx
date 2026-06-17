import { useState, useEffect, useRef } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useToast } from "@/hooks/use-toast";
import {
  Wallet, Key, Hash, QrCode, User, Lock, RefreshCw, Copy, Check,
  Zap, Calculator, Shuffle, Timer, FileText, Wrench,
} from "lucide-react";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

const api = (path: string, opts?: RequestInit) =>
  fetch(`/api/v1${path}`, { credentials: "include", ...opts });

function CopyBtn({ value }: { value: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <Button
      variant="ghost" size="icon" className="h-7 w-7 shrink-0"
      onClick={() => { navigator.clipboard.writeText(value); setCopied(true); setTimeout(() => setCopied(false), 1500); }}
    >
      {copied ? <Check className="w-3.5 h-3.5 text-green-500" /> : <Copy className="w-3.5 h-3.5" />}
    </Button>
  );
}

// ── 2FA TOTP Generator ─────────────────────────────────────────────────────

function TOTPTool() {
  const { toast } = useToast();
  const [entries, setEntries] = useState<{ label: string; secret: string; code: string; remaining: number }[]>([]);
  const [newLabel, setNewLabel] = useState("");
  const [newSecret, setNewSecret] = useState("");

  const fetchCodes = async (list: typeof entries) => {
    const updated = await Promise.all(
      list.map(async (e) => {
        try {
          const r = await api("/tools/totp-code", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ secret: e.secret }),
          });
          const d = await r.json();
          return { ...e, code: d.code || "ERROR", remaining: d.remaining_seconds || 30 };
        } catch {
          return { ...e, code: "ERR", remaining: 0 };
        }
      })
    );
    setEntries(updated);
  };

  useEffect(() => {
    if (entries.length === 0) return;
    fetchCodes(entries);
    const t = setInterval(() => fetchCodes(entries), 1000);
    return () => clearInterval(t);
  }, [entries.length]);

  const add = () => {
    if (!newSecret.trim()) return;
    const entry = { label: newLabel || "Account", secret: newSecret.trim().toUpperCase(), code: "...", remaining: 30 };
    const next = [...entries, entry];
    setEntries(next);
    fetchCodes(next);
    setNewLabel(""); setNewSecret("");
  };

  const remove = (i: number) => setEntries((prev) => prev.filter((_, idx) => idx !== i));

  return (
    <div className="space-y-4">
      <div className="flex gap-2">
        <Input value={newLabel} onChange={(e) => setNewLabel(e.target.value)} placeholder="Label (e.g. Binance)" className="w-36" />
        <Input value={newSecret} onChange={(e) => setNewSecret(e.target.value)} placeholder="TOTP secret key" className="flex-1 font-mono" />
        <Button onClick={add}><Key className="w-4 h-4 mr-1" /> Add</Button>
      </div>

      {entries.length === 0 ? (
        <div className="text-center text-muted-foreground py-8 border border-dashed border-border rounded-lg text-sm">
          Add a TOTP secret to generate live 2FA codes
        </div>
      ) : (
        <div className="space-y-2">
          {entries.map((e, i) => (
            <div key={i} className="flex items-center gap-3 p-3 bg-muted/40 rounded-lg border border-border">
              <div className="flex-1 min-w-0">
                <div className="font-medium text-sm">{e.label}</div>
                <div className="font-mono text-2xl font-bold tracking-[0.3em] text-primary">{e.code}</div>
              </div>
              <div className="w-24 space-y-1">
                <div className="text-xs text-muted-foreground text-right">{e.remaining}s</div>
                <div className="h-1.5 bg-muted rounded-full overflow-hidden">
                  <div
                    className="h-full rounded-full transition-all"
                    style={{
                      width: `${(e.remaining / 30) * 100}%`,
                      background: e.remaining > 10 ? "#22c55e" : e.remaining > 5 ? "#eab308" : "#ef4444",
                    }}
                  />
                </div>
              </div>
              <CopyBtn value={e.code} />
              <Button variant="ghost" size="icon" className="h-7 w-7 text-destructive" onClick={() => remove(i)}>✕</Button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Wallet Generator ───────────────────────────────────────────────────────

function WalletTool() {
  const { toast } = useToast();
  const [count, setCount] = useState("5");
  const [chain, setChain] = useState("evm");
  const [wallets, setWallets] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [showKeys, setShowKeys] = useState(false);

  const generate = async () => {
    setLoading(true);
    const r = await api("/tools/generate-wallets", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ count: Number(count), chain }),
    });
    setLoading(false);
    if (r.ok) {
      const d = await r.json();
      setWallets(d.wallets);
    } else {
      const e = await r.json();
      toast({ title: "Error", description: e.detail, variant: "destructive" });
    }
  };

  const copyAll = () => {
    const text = wallets.map((w) => `${w.address},${w.private_key}`).join("\n");
    navigator.clipboard.writeText(text);
    toast({ title: "Copied!", description: `${wallets.length} wallets copied as CSV` });
  };

  return (
    <div className="space-y-4">
      <div className="flex gap-2 items-end">
        <div className="space-y-1.5">
          <Label className="text-xs">Chain</Label>
          <Select value={chain} onValueChange={setChain}>
            <SelectTrigger className="w-28"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="evm">EVM</SelectItem>
              <SelectItem value="sol">Solana</SelectItem>
              <SelectItem value="btc">Bitcoin</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-1.5">
          <Label className="text-xs">Count (1-100)</Label>
          <Input type="number" value={count} onChange={(e) => setCount(e.target.value)} className="w-24" min={1} max={100} />
        </div>
        <Button onClick={generate} disabled={loading}>
          {loading ? <RefreshCw className="w-4 h-4 mr-1 animate-spin" /> : <Wallet className="w-4 h-4 mr-1" />}
          Generate
        </Button>
        {wallets.length > 0 && (
          <>
            <Button variant="outline" onClick={() => setShowKeys(!showKeys)}>
              {showKeys ? "Hide Keys" : "Show Keys"}
            </Button>
            <Button variant="outline" onClick={copyAll}>
              <Copy className="w-4 h-4 mr-1" /> Copy CSV
            </Button>
          </>
        )}
      </div>

      {wallets.length > 0 && (
        <div className="space-y-1.5 max-h-72 overflow-y-auto">
          {wallets.map((w, i) => (
            <div key={i} className="flex items-center gap-2 p-2 bg-muted/40 rounded-lg text-xs font-mono border border-border">
              <span className="text-muted-foreground w-5 shrink-0">{i + 1}</span>
              <div className="flex-1 min-w-0">
                <div className="truncate text-foreground">{w.address}</div>
                {showKeys && <div className="truncate text-muted-foreground">{w.private_key}</div>}
              </div>
              <CopyBtn value={showKeys ? `${w.address},${w.private_key}` : w.address} />
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Username Generator ─────────────────────────────────────────────────────

function UsernameTool() {
  const { toast } = useToast();
  const [count, setCount] = useState("10");
  const [prefix, setPrefix] = useState("");
  const [style, setStyle] = useState("random");
  const [usernames, setUsernames] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);

  const generate = async () => {
    setLoading(true);
    const r = await api("/tools/generate-usernames", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ count: Number(count), prefix, style }),
    });
    setLoading(false);
    if (r.ok) setUsernames((await r.json()).usernames);
  };

  return (
    <div className="space-y-4">
      <div className="flex gap-2 items-end flex-wrap">
        <div className="space-y-1.5">
          <Label className="text-xs">Style</Label>
          <Select value={style} onValueChange={setStyle}>
            <SelectTrigger className="w-28"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="random">Random</SelectItem>
              <SelectItem value="crypto">Crypto</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-1.5">
          <Label className="text-xs">Prefix</Label>
          <Input value={prefix} onChange={(e) => setPrefix(e.target.value)} placeholder="Optional" className="w-28" />
        </div>
        <div className="space-y-1.5">
          <Label className="text-xs">Count</Label>
          <Input type="number" value={count} onChange={(e) => setCount(e.target.value)} className="w-20" min={1} max={20} />
        </div>
        <Button onClick={generate} disabled={loading}>
          {loading ? <RefreshCw className="w-4 h-4 animate-spin" /> : <User className="w-4 h-4" />}
          <span className="ml-1">Generate</span>
        </Button>
      </div>
      {usernames.length > 0 && (
        <div className="grid grid-cols-2 gap-1.5 max-h-64 overflow-y-auto">
          {usernames.map((u, i) => (
            <div key={i} className="flex items-center justify-between p-2 bg-muted/40 rounded border border-border text-sm font-mono">
              <span className="truncate">{u}</span>
              <CopyBtn value={u} />
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Password Generator ─────────────────────────────────────────────────────

function PasswordTool() {
  const [length, setLength] = useState("16");
  const [count, setCount] = useState("5");
  const [syms, setSyms] = useState(true);
  const [nums, setNums] = useState(true);
  const [upper, setUpper] = useState(true);
  const [passwords, setPasswords] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);

  const generate = async () => {
    setLoading(true);
    const r = await api("/tools/generate-passwords", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ length: Number(length), count: Number(count), include_symbols: syms, include_numbers: nums, include_uppercase: upper }),
    });
    setLoading(false);
    if (r.ok) setPasswords((await r.json()).passwords);
  };

  return (
    <div className="space-y-4">
      <div className="flex gap-3 flex-wrap items-end">
        <div className="space-y-1.5">
          <Label className="text-xs">Length</Label>
          <Input type="number" value={length} onChange={(e) => setLength(e.target.value)} className="w-20" min={8} max={64} />
        </div>
        <div className="space-y-1.5">
          <Label className="text-xs">Count</Label>
          <Input type="number" value={count} onChange={(e) => setCount(e.target.value)} className="w-20" min={1} max={20} />
        </div>
        <div className="flex gap-3 text-sm">
          {[["Symbols", syms, setSyms], ["Numbers", nums, setNums], ["Uppercase", upper, setUpper]].map(([label, val, set]) => (
            <label key={String(label)} className="flex items-center gap-1.5 cursor-pointer">
              <input type="checkbox" checked={val as boolean} onChange={(e) => (set as any)(e.target.checked)} />
              {String(label)}
            </label>
          ))}
        </div>
        <Button onClick={generate} disabled={loading}>
          {loading ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Lock className="w-4 h-4" />}
          <span className="ml-1">Generate</span>
        </Button>
      </div>
      {passwords.length > 0 && (
        <div className="space-y-1.5">
          {passwords.map((p, i) => (
            <div key={i} className="flex items-center justify-between p-2 bg-muted/40 rounded border border-border font-mono text-sm">
              <span className="truncate">{p}</span>
              <CopyBtn value={p} />
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Hash Converter ─────────────────────────────────────────────────────────

function HashTool() {
  const [value, setValue] = useState("");
  const [result, setResult] = useState<Record<string, string> | null>(null);
  const [loading, setLoading] = useState(false);

  const convert = async () => {
    if (!value.trim()) return;
    setLoading(true);
    const r = await api("/tools/hash-convert", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ value }),
    });
    setLoading(false);
    if (r.ok) setResult(await r.json());
  };

  return (
    <div className="space-y-4">
      <div className="flex gap-2">
        <Input value={value} onChange={(e) => setValue(e.target.value)} placeholder="Hex, decimal, or string..." className="flex-1 font-mono" onKeyDown={(e) => e.key === "Enter" && convert()} />
        <Button onClick={convert} disabled={loading}>
          {loading ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Hash className="w-4 h-4" />}
          <span className="ml-1">Convert</span>
        </Button>
      </div>
      {result && (
        <div className="space-y-1.5">
          {Object.entries(result).map(([k, v]) => (
            <div key={k} className="flex items-center justify-between p-2.5 bg-muted/40 rounded border border-border">
              <span className="text-xs text-muted-foreground uppercase w-20 shrink-0">{k}</span>
              <span className="font-mono text-sm flex-1 truncate">{v}</span>
              <CopyBtn value={String(v)} />
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ── QR Generator ───────────────────────────────────────────────────────────

function QRTool() {
  const [data, setData] = useState("");
  const [label, setLabel] = useState("");
  const [qrUrl, setQrUrl] = useState("");
  const [loading, setLoading] = useState(false);

  const generate = async () => {
    if (!data.trim()) return;
    setLoading(true);
    const r = await api("/tools/generate-qr", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ data, label }),
    });
    setLoading(false);
    if (r.ok) setQrUrl((await r.json()).qr_url);
  };

  return (
    <div className="space-y-4">
      <div className="space-y-2">
        <div className="flex gap-2">
          <Input value={data} onChange={(e) => setData(e.target.value)} placeholder="Wallet address, URL, or any text" className="flex-1" />
          <Button onClick={generate} disabled={loading}>
            {loading ? <RefreshCw className="w-4 h-4 animate-spin" /> : <QrCode className="w-4 h-4" />}
            <span className="ml-1">Generate</span>
          </Button>
        </div>
        <Input value={label} onChange={(e) => setLabel(e.target.value)} placeholder="Label (optional)" />
      </div>
      {qrUrl && (
        <div className="flex flex-col items-center gap-3">
          <img src={qrUrl} alt="QR Code" className="w-48 h-48 rounded-lg bg-white p-2" />
          <Button variant="outline" onClick={() => window.open(qrUrl, "_blank")} size="sm">
            Download QR
          </Button>
        </div>
      )}
    </div>
  );
}

// ── Profile Randomizer ─────────────────────────────────────────────────────

function ProfileTool() {
  const { toast } = useToast();
  const [profile, setProfile] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  const generate = async () => {
    setLoading(true);
    const r = await api("/tools/profile-randomizer");
    setLoading(false);
    if (r.ok) setProfile(await r.json());
  };

  return (
    <div className="space-y-4">
      <Button onClick={generate} disabled={loading}>
        {loading ? <RefreshCw className="w-4 h-4 mr-1 animate-spin" /> : <Shuffle className="w-4 h-4 mr-1" />}
        Generate Random Profile
      </Button>
      {profile && (
        <div className="p-4 bg-muted/40 rounded-lg border border-border space-y-3">
          <div className="flex items-center gap-3">
            <img src={profile.avatar_url} alt="avatar" className="w-12 h-12 rounded-full bg-muted" />
            <div>
              <div className="font-semibold">{profile.name}</div>
              <div className="text-muted-foreground text-sm font-mono">@{profile.username}</div>
            </div>
          </div>
          <p className="text-sm text-muted-foreground">{profile.bio}</p>
          <div className="grid grid-cols-2 gap-1.5">
            {[["Name", profile.name], ["Username", profile.username], ["Bio", profile.bio]].map(([k, v]) => (
              <div key={String(k)} className="flex items-center justify-between p-2 bg-background rounded border border-border">
                <span className="text-xs text-muted-foreground">{k}</span>
                <span className="text-sm truncate max-w-[120px]">{String(v)}</span>
                <CopyBtn value={String(v)} />
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ── Tool Card ──────────────────────────────────────────────────────────────

const TOOL_GROUPS = [
  {
    id: "security",
    label: "2FA & Security",
    icon: Key,
    tools: [
      { id: "totp", label: "2FA Code Generator", icon: Key, desc: "Live TOTP codes with countdown", component: <TOTPTool /> },
    ],
  },
  {
    id: "wallet",
    label: "Wallet Tools",
    icon: Wallet,
    tools: [
      { id: "walletgen", label: "Wallet Generator", icon: Wallet, desc: "Bulk generate ETH/SOL/BTC wallets", component: <WalletTool /> },
      { id: "qrcode", label: "QR Code Generator", icon: QrCode, desc: "QR from wallet address or text", component: <QRTool /> },
      { id: "hash", label: "Hash / Converter", icon: Hash, desc: "Convert hex, decimal, hash strings", component: <HashTool /> },
    ],
  },
  {
    id: "account",
    label: "Account Tools",
    icon: User,
    tools: [
      { id: "usernames", label: "Username Generator", icon: User, desc: "Unique crypto-style usernames", component: <UsernameTool /> },
      { id: "passwords", label: "Password Generator", icon: Lock, desc: "Strong random passwords", component: <PasswordTool /> },
      { id: "profile", label: "Profile Randomizer", icon: Shuffle, desc: "Random name, bio, and avatar", component: <ProfileTool /> },
    ],
  },
];

export default function ToolsPage() {
  const [activeGroup, setActiveGroup] = useState("security");
  const [activeTool, setActiveTool] = useState("totp");

  const allTools = TOOL_GROUPS.flatMap((g) => g.tools);
  const currentTool = allTools.find((t) => t.id === activeTool);
  const totalTools = 30;
  const builtTools = allTools.length;

  return (
    <div className="p-6 space-y-6 max-w-5xl mx-auto">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <Wrench className="w-6 h-6 text-primary" /> Airdrop Tools
          </h1>
          <p className="text-muted-foreground text-sm mt-0.5">
            {builtTools} of {totalTools} tools — wallets, 2FA, utilities and more
          </p>
        </div>
        <Badge className="bg-primary/10 text-primary border-primary/30">
          {builtTools}/{totalTools} Tools
        </Badge>
      </div>

      <div className="flex gap-6">
        <div className="w-48 shrink-0 space-y-1">
          {TOOL_GROUPS.map((group) => (
            <div key={group.id}>
              <button
                onClick={() => { setActiveGroup(group.id); if (group.tools[0]) setActiveTool(group.tools[0].id); }}
                className={`w-full flex items-center gap-2 px-3 py-1.5 rounded text-xs font-bold uppercase tracking-widest transition-colors ${
                  activeGroup === group.id ? "text-primary" : "text-muted-foreground hover:text-foreground"
                }`}
              >
                <group.icon className="w-3.5 h-3.5" /> {group.label}
              </button>
              {activeGroup === group.id && group.tools.map((tool) => (
                <button
                  key={tool.id}
                  onClick={() => setActiveTool(tool.id)}
                  className={`w-full flex items-center gap-2 px-3 py-2 rounded text-sm transition-colors ml-2 ${
                    activeTool === tool.id
                      ? "bg-sidebar-accent text-sidebar-primary"
                      : "text-sidebar-foreground/70 hover:text-foreground hover:bg-muted/50"
                  }`}
                >
                  <tool.icon className="w-3.5 h-3.5 shrink-0" />
                  <span className="truncate">{tool.label}</span>
                </button>
              ))}
            </div>
          ))}

          <div className="pt-3 border-t border-border mt-3">
            <p className="text-[10px] text-muted-foreground px-3 uppercase tracking-widest font-bold mb-2">Coming Soon</p>
            {[
              "Wallet Checker", "Gas Estimator", "Token Approvals", "Email OTP Fetch",
              "Referral Manager", "Points Tracker", "Proxy Manager", "CSV Importer",
              "Airdrop Calendar", "ROI Calculator",
            ].map((name) => (
              <div key={name} className="flex items-center gap-2 px-3 py-1.5 text-xs text-muted-foreground/50">
                <div className="w-1.5 h-1.5 rounded-full bg-muted-foreground/30" />
                {name}
              </div>
            ))}
          </div>
        </div>

        <div className="flex-1 min-w-0">
          {currentTool ? (
            <Card className="border-border">
              <CardHeader className="pb-3">
                <CardTitle className="flex items-center gap-2 text-base">
                  <currentTool.icon className="w-5 h-5 text-primary" />
                  {currentTool.label}
                </CardTitle>
                <p className="text-sm text-muted-foreground">{currentTool.desc}</p>
              </CardHeader>
              <CardContent>{currentTool.component}</CardContent>
            </Card>
          ) : (
            <div className="text-center text-muted-foreground py-16">Select a tool from the left</div>
          )}
        </div>
      </div>
    </div>
  );
}
