import { useListNotifications, getListNotificationsQueryKey, useMarkNotificationRead } from "@workspace/api-client-react";
import { useQueryClient } from "@tanstack/react-query";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Bell, Check } from "lucide-react";
import { format } from "date-fns";
import { cn } from "@/lib/utils";

export default function NotificationsPage() {
  const queryClient = useQueryClient();

  const { data: notifications, isLoading } = useListNotifications(
    {},
    { query: { queryKey: getListNotificationsQueryKey({}) } }
  );

  const { mutate: markRead } = useMarkNotificationRead({
    mutation: {
      onSuccess: () => queryClient.invalidateQueries({ queryKey: getListNotificationsQueryKey({}) }),
    },
  });

  const unread = (notifications ?? []).filter((n: any) => !n.read).length;

  return (
    <div className="p-6 max-w-[900px]">
      <div className="mb-6">
        <div className="flex items-center gap-3">
          <h1 className="text-2xl font-black text-foreground tracking-tight">Notifications</h1>
          {unread > 0 && (
            <span className="bg-primary text-primary-foreground text-xs font-bold px-2 py-0.5 rounded-sm">{unread}</span>
          )}
        </div>
        <p className="text-sm text-muted-foreground mt-0.5">{notifications?.length ?? 0} total</p>
      </div>

      {isLoading ? (
        <div className="space-y-2">{Array.from({ length: 5 }).map((_, i) => <Skeleton key={i} className="h-16" />)}</div>
      ) : !notifications?.length ? (
        <div className="py-24 text-center">
          <Bell className="w-10 h-10 text-muted-foreground/40 mx-auto mb-3" />
          <p className="text-sm font-medium text-muted-foreground">No notifications</p>
        </div>
      ) : (
        <div className="space-y-1">
          {notifications.map((n: any) => (
            <div
              key={n.id}
              className={cn(
                "flex items-start gap-3 p-4 border rounded-sm transition-colors",
                !n.read ? "bg-primary/5 border-primary/20" : "bg-background border-border"
              )}
            >
              <div className={cn("w-2 h-2 rounded-full mt-1.5 shrink-0", !n.read ? "bg-primary" : "bg-muted")} />
              <div className="flex-1 min-w-0">
                <p className={cn("text-sm", !n.read ? "font-semibold text-foreground" : "text-foreground/70")}>{n.message}</p>
                <p className="text-[10px] text-muted-foreground mt-1">
                  {n.created_at ? format(new Date(n.created_at), "MMM d, yyyy 'at' HH:mm") : ""}
                </p>
              </div>
              {!n.read && (
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-7 w-7 shrink-0 text-muted-foreground hover:text-primary"
                  onClick={() => markRead({ notificationId: n.id })}
                >
                  <Check className="w-3.5 h-3.5" />
                </Button>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
