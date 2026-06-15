import { useParams } from "wouter";
import { useGetProject, getGetProjectQueryKey, useGetProjectStats, getGetProjectStatsQueryKey, useListTasks, getListTasksQueryKey, useCreateTask, useUpdateTask, TaskUpdateStatus, TaskInputPriority } from "@workspace/api-client-react";
import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { Skeleton } from "@/components/ui/skeleton";
import { useQueryClient } from "@tanstack/react-query";
import { CheckSquare, Clock, AlertCircle, Plus, ChevronLeft } from "lucide-react";
import { Link } from "wouter";
import { format } from "date-fns";
import { cn } from "@/lib/utils";

const STATUS_COLORS: Record<string, string> = {
  pending: "bg-muted text-muted-foreground",
  in_progress: "bg-blue-100 text-blue-700",
  completed: "bg-green-100 text-green-700",
  cancelled: "bg-red-100 text-red-600",
};
const PRIORITY_COLORS: Record<string, string> = {
  low: "text-muted-foreground",
  normal: "text-blue-600",
  high: "text-orange-500",
  urgent: "text-red-600",
};

export default function ProjectDetailPage() {
  const params = useParams<{ id: string }>();
  const projectId = params.id;
  const queryClient = useQueryClient();

  const [statusFilter, setStatusFilter] = useState("all");
  const [showCreate, setShowCreate] = useState(false);
  const [newTitle, setNewTitle] = useState("");
  const [newPriority, setNewPriority] = useState("normal");

  const { data: project } = useGetProject(projectId, {
    query: { queryKey: getGetProjectQueryKey(projectId) },
  });

  const { data: stats } = useGetProjectStats(projectId, {
    query: { queryKey: getGetProjectStatsQueryKey(projectId) },
  });

  const queryParams = statusFilter !== "all" ? { project_id: projectId, status: statusFilter } : { project_id: projectId };

  const { data: tasks, isLoading } = useListTasks(queryParams, {
    query: { queryKey: getListTasksQueryKey(queryParams) },
  });

  const { mutate: createTask, isPending: creating } = useCreateTask({
    mutation: {
      onSuccess: () => {
        queryClient.invalidateQueries({ queryKey: getListTasksQueryKey({ project_id: projectId }) });
        setShowCreate(false);
        setNewTitle("");
        setNewPriority("normal");
      },
    },
  });

  const { mutate: updateTask } = useUpdateTask({
    mutation: {
      onSuccess: () => queryClient.invalidateQueries({ queryKey: getListTasksQueryKey({ project_id: projectId }) }),
    },
  });

  return (
    <div className="p-6 max-w-[1400px]">
      <div className="mb-4">
        <Link href="/projects" className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground mb-3">
          <ChevronLeft className="w-3.5 h-3.5" /> Projects
        </Link>
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-black text-foreground tracking-tight">{project?.name ?? "Project"}</h1>
            {project?.description && <p className="text-sm text-muted-foreground mt-0.5">{project.description}</p>}
          </div>
          <Button size="sm" className="font-bold" onClick={() => setShowCreate(true)}>
            <Plus className="w-4 h-4 mr-1.5" /> Add Task
          </Button>
        </div>
      </div>

      {stats && (
        <div className="grid grid-cols-4 gap-3 mb-5">
          {[
            { label: "Total", value: stats.total, icon: CheckSquare },
            { label: "Completed", value: stats.completed, icon: CheckSquare, color: "text-green-600" },
            { label: "In Progress", value: stats.in_progress, icon: Clock, color: "text-blue-600" },
            { label: "Overdue", value: stats.overdue, icon: AlertCircle, color: "text-destructive" },
          ].map(({ label, value, icon: Icon, color }) => (
            <Card key={label} className="border-border">
              <CardContent className="p-4">
                <p className="text-xs text-muted-foreground uppercase tracking-wide font-semibold mb-1">{label}</p>
                <div className="flex items-center gap-1.5">
                  <Icon className={cn("w-4 h-4", color ?? "text-primary")} />
                  <span className="text-2xl font-black">{value ?? 0}</span>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      <Card className="border-border">
        <CardHeader className="pb-3 flex-row items-center justify-between space-y-0">
          <CardTitle className="text-sm font-bold uppercase tracking-wider text-muted-foreground">Tasks</CardTitle>
          <Select value={statusFilter} onValueChange={setStatusFilter}>
            <SelectTrigger className="w-32 h-7 text-xs">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All</SelectItem>
              <SelectItem value="pending">Pending</SelectItem>
              <SelectItem value="in_progress">In Progress</SelectItem>
              <SelectItem value="completed">Completed</SelectItem>
              <SelectItem value="cancelled">Cancelled</SelectItem>
            </SelectContent>
          </Select>
        </CardHeader>
        <CardContent className="pt-0">
          {isLoading ? (
            <div className="space-y-2">{Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} className="h-12" />)}</div>
          ) : !tasks?.length ? (
            <div className="py-10 text-center text-sm text-muted-foreground">No tasks</div>
          ) : (
            <div className="divide-y divide-border">
              {tasks.map((t: any) => (
                <div key={t.id} className="flex items-center gap-3 py-2.5">
                  <Select value={t.status} onValueChange={(val) => updateTask({ taskId: t.id, data: { status: val as TaskUpdateStatus } })}>
                    <SelectTrigger className={cn("w-28 h-6 text-[11px] border-0 px-2", STATUS_COLORS[t.status])}>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="pending">Pending</SelectItem>
                      <SelectItem value="in_progress">In Progress</SelectItem>
                      <SelectItem value="completed">Completed</SelectItem>
                      <SelectItem value="cancelled">Cancelled</SelectItem>
                    </SelectContent>
                  </Select>
                  <span className={cn("text-xs font-black uppercase w-14 shrink-0", PRIORITY_COLORS[t.priority])}>
                    {t.priority}
                  </span>
                  <span className="text-sm text-foreground font-medium flex-1 truncate">{t.title}</span>
                  {t.assignee_name && (
                    <Badge variant="outline" className="text-[10px] px-1.5 py-0 shrink-0">{t.assignee_name}</Badge>
                  )}
                  {t.deadline && (
                    <span className={cn("text-[10px] shrink-0", new Date(t.deadline) < new Date() ? "text-destructive font-semibold" : "text-muted-foreground")}>
                      {format(new Date(t.deadline), "MMM d")}
                    </span>
                  )}
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <Dialog open={showCreate} onOpenChange={setShowCreate}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="font-black">Add Task</DialogTitle>
          </DialogHeader>
          <div className="space-y-3 py-2">
            <div>
              <label className="text-xs font-semibold uppercase tracking-wide text-muted-foreground block mb-1.5">Title</label>
              <Input placeholder="Task title" value={newTitle} onChange={(e) => setNewTitle(e.target.value)} autoFocus />
            </div>
            <div>
              <label className="text-xs font-semibold uppercase tracking-wide text-muted-foreground block mb-1.5">Priority</label>
              <Select value={newPriority} onValueChange={setNewPriority}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="low">Low</SelectItem>
                  <SelectItem value="normal">Normal</SelectItem>
                  <SelectItem value="high">High</SelectItem>
                  <SelectItem value="urgent">Urgent</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowCreate(false)}>Cancel</Button>
            <Button
              className="font-bold"
              disabled={!newTitle.trim() || creating}
              onClick={() => createTask({ data: { title: newTitle.trim(), project_id: projectId, priority: newPriority as TaskInputPriority } })}
            >
              {creating ? "Adding..." : "Add Task"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
