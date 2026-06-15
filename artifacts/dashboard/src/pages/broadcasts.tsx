import { useState } from "react";
import { useListBroadcasts, getListBroadcastsQueryKey, useCreateBroadcast } from "@workspace/api-client-react";
import { useQueryClient } from "@tanstack/react-query";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Megaphone, Plus, CheckCircle, XCircle, Clock } from "lucide-react";
import { format } from "date-fns";

export default function BroadcastsPage() {
  const queryClient = useQueryClient();
  const [showCompose, setShowCompose] = useState(false);
  const [message, setMessage] = useState("");

  const { data: broadcasts, isLoading } = useListBroadcasts({
    query: { queryKey: getListBroadcastsQueryKey() },
  });

  const { mutate: send, isPending: sending } = useCreateBroadcast({
    mutation: {
      onSuccess: () => {
        queryClient.invalidateQueries({ queryKey: getListBroadcastsQueryKey() });
        setShowCompose(false);
        setMessage("");
      },
    },
  });

  return (
    <div className="p-6 max-w-[1400px]">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-black text-foreground tracking-tight">Broadcasts</h1>
          <p className="text-sm text-muted-foreground mt-0.5">Telegram messages sent to your community</p>
        </div>
        <Button size="sm" className="font-bold" onClick={() => setShowCompose(true)}>
          <Plus className="w-4 h-4 mr-1.5" /> Compose
        </Button>
      </div>

      {isLoading ? (
        <div className="space-y-3">{Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-24" />)}</div>
      ) : !broadcasts?.length ? (
        <div className="py-24 text-center">
          <Megaphone className="w-10 h-10 text-muted-foreground/40 mx-auto mb-3" />
          <p className="text-sm font-medium text-muted-foreground">No broadcasts yet</p>
          <p className="text-xs text-muted-foreground mt-1">Send your first message to the community</p>
        </div>
      ) : (
        <div className="space-y-3">
          {broadcasts.map((b: any) => (
            <Card key={b.id} className="border-border">
              <CardContent className="p-4">
                <div className="flex items-start gap-3">
                  <div className="w-8 h-8 bg-primary/10 rounded-sm flex items-center justify-center shrink-0 mt-0.5">
                    <Megaphone className="w-4 h-4 text-primary" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-foreground leading-relaxed line-clamp-3">{b.message}</p>
                    <div className="flex items-center gap-3 mt-2">
                      <span className="flex items-center gap-1 text-[11px] text-muted-foreground">
                        <Clock className="w-3 h-3" />
                        {b.created_at ? format(new Date(b.created_at), "MMM d, yyyy 'at' HH:mm") : "—"}
                      </span>
                    </div>
                  </div>
                  <div className="flex gap-2 shrink-0">
                    <div className="flex items-center gap-1 text-xs font-semibold text-green-600 bg-green-50 border border-green-100 px-2 py-1 rounded-sm">
                      <CheckCircle className="w-3.5 h-3.5" />
                      {b.sent_count ?? 0}
                    </div>
                    {(b.failed_count ?? 0) > 0 && (
                      <div className="flex items-center gap-1 text-xs font-semibold text-red-600 bg-red-50 border border-red-100 px-2 py-1 rounded-sm">
                        <XCircle className="w-3.5 h-3.5" />
                        {b.failed_count}
                      </div>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      <Dialog open={showCompose} onOpenChange={setShowCompose}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="font-black flex items-center gap-2">
              <Megaphone className="w-4 h-4 text-primary" /> Compose Broadcast
            </DialogTitle>
          </DialogHeader>
          <div className="py-2">
            <label className="text-xs font-semibold uppercase tracking-wide text-muted-foreground block mb-1.5">Message</label>
            <Textarea
              placeholder="Write your message to the community..."
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              rows={5}
              className="resize-none"
              autoFocus
            />
            <p className="text-[10px] text-muted-foreground mt-1.5">{message.length} characters</p>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowCompose(false)}>Cancel</Button>
            <Button
              className="font-bold"
              disabled={!message.trim() || sending}
              onClick={() => send({ data: { message: message.trim() } })}
            >
              {sending ? "Sending..." : "Send Broadcast"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
