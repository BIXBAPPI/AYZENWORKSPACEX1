import { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { useToast } from "@/hooks/use-toast";
import { User, Edit3, Save, X, Flame, Twitter, Github, MessageCircle, Hash, CheckCircle } from "lucide-react";

const TIER_CONFIG: Record<string, { color: string; bg: string; label: string }> = {
  Bronze: { color: "text-amber-700", bg: "bg-amber-500/10 border-amber-500/30", label: "🥉 Bronze" },
  Silver: { color: "text-slate-400", bg: "bg-slate-500/10 border-slate-500/30", label: "🥈 Silver" },
  Gold: { color: "text-yellow-500", bg: "bg-yellow-500/10 border-yellow-500/30", label: "🥇 Gold" },
  Platinum: { color: "text-slate-200", bg: "bg-slate-400/10 border-slate-400/30", label: "💎 Platinum" },
};

const api = (path: string, opts?: RequestInit) =>
  fetch(`/api/v1${path}`, { credentials: "include", ...opts }).then((r) => r.json());

export default function ProfilePage() {
  const { user } = useAuth();
  const { toast } = useToast();
  const [profile, setProfile] = useState<any>(null);
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState({ bio: "", username: "", twitter_handle: "", discord_handle: "", telegram_handle: "", github_handle: "", avatar_url: "" });
  const [saving, setSaving] = useState(false);

  const load = async () => {
    const data = await api("/profile/me");
    setProfile(data);
    setForm({
      bio: data.bio || "",
      username: data.username || "",
      twitter_handle: data.twitter_handle || "",
      discord_handle: data.discord_handle || "",
      telegram_handle: data.telegram_handle || "",
      github_handle: data.github_handle || "",
      avatar_url: data.avatar_url || "",
    });
  };

  useEffect(() => { load(); }, []);

  const save = async () => {
    setSaving(true);
    try {
      await api("/profile/me", {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(form),
      });
      toast({ title: "Profile updated ✅" });
      setEditing(false);
      load();
    } catch {
      toast({ title: "Failed to save", variant: "destructive" });
    } finally { setSaving(false); }
  };

  if (!profile) {
    return <div className="p-6"><div className="h-48 bg-muted/20 rounded-xl animate-pulse" /></div>;
  }

  const tier = TIER_CONFIG[profile.tier] ?? TIER_CONFIG.Bronze;
  const displayName = profile.username || profile.full_name || profile.email?.split("@")[0];

  return (
    <div className="p-4 md:p-6 max-w-2xl">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-black text-foreground">Profile</h1>
        {!editing ? (
          <Button onClick={() => setEditing(true)} variant="outline" size="sm" className="gap-1.5">
            <Edit3 className="w-3.5 h-3.5" /> Edit Profile
          </Button>
        ) : (
          <div className="flex gap-2">
            <Button onClick={() => { setEditing(false); load(); }} variant="ghost" size="sm" className="gap-1.5">
              <X className="w-3.5 h-3.5" /> Cancel
            </Button>
            <Button onClick={save} size="sm" disabled={saving} className="gap-1.5">
              <Save className="w-3.5 h-3.5" /> Save Changes
            </Button>
          </div>
        )}
      </div>

      {/* Avatar + Identity */}
      <Card className="border-border mb-5">
        <CardContent className="p-5">
          <div className="flex items-start gap-5">
            <div className="relative shrink-0">
              {profile.avatar_url ? (
                <img src={profile.avatar_url} alt="avatar" className="w-20 h-20 rounded-full object-cover border-2 border-primary/30" />
              ) : (
                <div className="w-20 h-20 rounded-full bg-primary/10 flex items-center justify-center border-2 border-primary/20">
                  <span className="text-3xl font-black text-primary">{displayName?.[0]?.toUpperCase()}</span>
                </div>
              )}
            </div>
            <div className="flex-1 min-w-0">
              {editing ? (
                <div className="space-y-2">
                  <div>
                    <Label className="text-xs text-muted-foreground">Username</Label>
                    <Input value={form.username} onChange={(e) => setForm((f) => ({ ...f, username: e.target.value }))} placeholder="username" className="h-8 text-sm" />
                  </div>
                  <div>
                    <Label className="text-xs text-muted-foreground">Avatar URL</Label>
                    <Input value={form.avatar_url} onChange={(e) => setForm((f) => ({ ...f, avatar_url: e.target.value }))} placeholder="https://…" className="h-8 text-sm" />
                  </div>
                </div>
              ) : (
                <>
                  <h2 className="text-xl font-black text-foreground">{displayName}</h2>
                  <p className="text-sm text-muted-foreground">{profile.email}</p>
                  <div className="flex items-center gap-2 mt-2 flex-wrap">
                    <Badge variant="outline" className="capitalize text-xs">{profile.role}</Badge>
                    <Badge className={`text-xs border ${tier.bg} ${tier.color}`}>{tier.label}</Badge>
                    <span className="text-xs text-muted-foreground">{profile.xp?.toLocaleString()} XP</span>
                    {profile.two_fa_enabled && (
                      <Badge variant="outline" className="text-xs text-green-500 border-green-500/30 gap-1">
                        <CheckCircle className="w-3 h-3" /> 2FA On
                      </Badge>
                    )}
                  </div>
                </>
              )}
            </div>
          </div>

          {/* Streak */}
          <div className="mt-4 flex items-center gap-2 pt-3 border-t border-border">
            <Flame className="w-5 h-5 text-orange-500" />
            <span className="text-sm font-bold text-foreground">{profile.streak} day streak</span>
          </div>
        </CardContent>
      </Card>

      {/* Bio */}
      <Card className="border-border mb-5">
        <CardContent className="p-5">
          <h3 className="text-sm font-semibold text-foreground mb-3">Bio</h3>
          {editing ? (
            <Textarea value={form.bio} onChange={(e) => setForm((f) => ({ ...f, bio: e.target.value }))} placeholder="Tell the community about yourself…" rows={3} className="text-sm" />
          ) : (
            <p className="text-sm text-muted-foreground">{profile.bio || "No bio yet. Click Edit to add one."}</p>
          )}
        </CardContent>
      </Card>

      {/* Socials */}
      <Card className="border-border mb-5">
        <CardContent className="p-5">
          <h3 className="text-sm font-semibold text-foreground mb-3">Social Handles</h3>
          {editing ? (
            <div className="grid grid-cols-2 gap-3">
              {[
                { key: "twitter_handle", label: "Twitter", icon: Twitter, placeholder: "@username" },
                { key: "discord_handle", label: "Discord", icon: Hash, placeholder: "user#1234" },
                { key: "telegram_handle", label: "Telegram", icon: MessageCircle, placeholder: "@username" },
                { key: "github_handle", label: "GitHub", icon: Github, placeholder: "username" },
              ].map(({ key, label, icon: Icon, placeholder }) => (
                <div key={key}>
                  <Label className="text-xs text-muted-foreground flex items-center gap-1"><Icon className="w-3 h-3" />{label}</Label>
                  <Input value={(form as any)[key]} onChange={(e) => setForm((f) => ({ ...f, [key]: e.target.value }))} placeholder={placeholder} className="h-8 text-sm mt-1" />
                </div>
              ))}
            </div>
          ) : (
            <div className="flex flex-wrap gap-2">
              {profile.twitter_handle && (
                <a href={`https://twitter.com/${profile.twitter_handle.replace("@", "")}`} target="_blank" rel="noopener noreferrer"
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium bg-sky-500/10 text-sky-400 border border-sky-500/20 hover:border-sky-500/50 transition-colors">
                  <Twitter className="w-3 h-3" />{profile.twitter_handle}
                </a>
              )}
              {profile.discord_handle && (
                <span className="flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                  <Hash className="w-3 h-3" />{profile.discord_handle}
                </span>
              )}
              {profile.telegram_handle && (
                <a href={`https://t.me/${profile.telegram_handle.replace("@", "")}`} target="_blank" rel="noopener noreferrer"
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium bg-blue-500/10 text-blue-400 border border-blue-500/20 hover:border-blue-500/50 transition-colors">
                  <MessageCircle className="w-3 h-3" />{profile.telegram_handle}
                </a>
              )}
              {profile.github_handle && (
                <a href={`https://github.com/${profile.github_handle}`} target="_blank" rel="noopener noreferrer"
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium bg-muted text-muted-foreground border border-border hover:border-primary/30 transition-colors">
                  <Github className="w-3 h-3" />{profile.github_handle}
                </a>
              )}
              {!profile.twitter_handle && !profile.discord_handle && !profile.telegram_handle && !profile.github_handle && (
                <p className="text-sm text-muted-foreground">No social handles set. Click Edit to add them.</p>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Stats */}
      <Card className="border-border">
        <CardContent className="p-5">
          <h3 className="text-sm font-semibold text-foreground mb-3">Stats</h3>
          <div className="grid grid-cols-2 gap-3">
            <div className="text-center py-3 rounded-lg bg-muted/30">
              <p className="text-2xl font-black text-foreground">{profile.xp?.toLocaleString()}</p>
              <p className="text-xs text-muted-foreground">Total XP</p>
            </div>
            <div className="text-center py-3 rounded-lg bg-muted/30">
              <p className={`text-2xl font-black ${tier.color}`}>{profile.tier}</p>
              <p className="text-xs text-muted-foreground">Tier</p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
