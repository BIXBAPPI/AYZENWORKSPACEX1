import { useGetSettings, getGetSettingsQueryKey, useUpdateSettings } from "@workspace/api-client-react";
import { useQueryClient } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { useState, useEffect } from "react";
import { Settings, Bell, Globe, Moon } from "lucide-react";

export default function SettingsPage() {
  const queryClient = useQueryClient();
  const { data: settings, isLoading } = useGetSettings({
    query: { queryKey: getGetSettingsQueryKey() },
  });

  const [language, setLanguage] = useState("en");
  const [quietStart, setQuietStart] = useState("");
  const [quietEnd, setQuietEnd] = useState("");
  const [notifyDeadline, setNotifyDeadline] = useState(true);
  const [notifyAssignments, setNotifyAssignments] = useState(true);

  useEffect(() => {
    if (settings) {
      setLanguage(settings.language ?? "en");
      setQuietStart(settings.quiet_start ?? "");
      setQuietEnd(settings.quiet_end ?? "");
      setNotifyDeadline(settings.notify_deadline ?? true);
      setNotifyAssignments(settings.notify_assignments ?? true);
    }
  }, [settings]);

  const { mutate: save, isPending: saving } = useUpdateSettings({
    mutation: {
      onSuccess: () => queryClient.invalidateQueries({ queryKey: getGetSettingsQueryKey() }),
    },
  });

  function handleSave() {
    save({ data: { language, quiet_start: quietStart || undefined, quiet_end: quietEnd || undefined, notify_deadline: notifyDeadline, notify_assignments: notifyAssignments } });
  }

  if (isLoading) return <div className="p-6"><Skeleton className="h-64" /></div>;

  return (
    <div className="p-6 max-w-2xl">
      <div className="mb-6">
        <h1 className="text-2xl font-black text-foreground tracking-tight">Settings</h1>
        <p className="text-sm text-muted-foreground mt-0.5">Preferences and notification settings</p>
      </div>

      <div className="space-y-4">
        <Card className="border-border">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-2">
              <Globe className="w-4 h-4" /> Language
            </CardTitle>
          </CardHeader>
          <CardContent className="pt-0">
            <Select value={language} onValueChange={setLanguage}>
              <SelectTrigger className="w-48">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="en">English</SelectItem>
                <SelectItem value="bn">Bengali</SelectItem>
                <SelectItem value="hi">Hindi</SelectItem>
                <SelectItem value="ar">Arabic</SelectItem>
              </SelectContent>
            </Select>
          </CardContent>
        </Card>

        <Card className="border-border">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-2">
              <Bell className="w-4 h-4" /> Notifications
            </CardTitle>
          </CardHeader>
          <CardContent className="pt-0 space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-foreground">Deadline reminders</p>
                <p className="text-xs text-muted-foreground">Get notified when tasks are due soon</p>
              </div>
              <Switch checked={notifyDeadline} onCheckedChange={setNotifyDeadline} />
            </div>
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-foreground">Task assignments</p>
                <p className="text-xs text-muted-foreground">Get notified when tasks are assigned to you</p>
              </div>
              <Switch checked={notifyAssignments} onCheckedChange={setNotifyAssignments} />
            </div>
          </CardContent>
        </Card>

        <Card className="border-border">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-2">
              <Moon className="w-4 h-4" /> Quiet Hours
            </CardTitle>
          </CardHeader>
          <CardContent className="pt-0">
            <p className="text-xs text-muted-foreground mb-3">No notifications during these hours</p>
            <div className="flex items-center gap-3">
              <div>
                <label className="text-xs text-muted-foreground block mb-1">Start</label>
                <input
                  type="time"
                  value={quietStart}
                  onChange={(e) => setQuietStart(e.target.value)}
                  className="h-9 px-3 border border-input rounded-sm text-sm bg-background text-foreground"
                />
              </div>
              <span className="text-muted-foreground mt-5">—</span>
              <div>
                <label className="text-xs text-muted-foreground block mb-1">End</label>
                <input
                  type="time"
                  value={quietEnd}
                  onChange={(e) => setQuietEnd(e.target.value)}
                  className="h-9 px-3 border border-input rounded-sm text-sm bg-background text-foreground"
                />
              </div>
            </div>
          </CardContent>
        </Card>

        <Button className="font-bold" onClick={handleSave} disabled={saving}>
          {saving ? "Saving..." : "Save Settings"}
        </Button>
      </div>
    </div>
  );
}
