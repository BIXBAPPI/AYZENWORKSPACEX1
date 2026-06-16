import { useState } from "react";
import { useListTasks, getListTasksQueryKey, useCreateTask, useUpdateTask, useDeleteTask, useListOverdueTasks, getListOverdueTasksQueryKey, useListProjects, getListProjectsQueryKey, TaskUpdateStatus, TaskInputPriority } from "@workspace/api-client-react";
import { useQueryClient } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { Skeleton } from "@/components/ui/skeleton";
import { Plus, Trash2, AlertTriangle, Search } from "lucide-react";
import { format } from "date-fns";
import { cn } from "@/lib/utils";

const STATUS_COLORS: Record<string, string> = {
  pending: "bg-muted text-muted-foreground border-muted",
  in_progress: "bg-blue-50 text-blue-700 border-blue-200",
  completed: "bg-green-50 text-green-700 border-green-200",
  cancelled: "bg-red-50 text-red-600 border-red-200",
};
const PRIORITY_DOT: Record<string, string> = {
  low: "bg-muted-foreground",
  normal: "bg-blue-500",
  high: "bg-orange-500",
  urgent: "bg-red-500",
};

export default function TasksPage() {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [priorityFilter, setPriorityFilter] = useState("all");
  const [showCreate, setShowCreate] = useState(false);
  const [showOverdue, setShowOverdue] = useState(false);
  const [newTitle, setNewTitle] = useState("");
  const [newPriority, setNewPriority] = useState("normal");
  const [newProjectId, setNewProjectId] = useState("");

  const params: Record<string, string> = {};
  if (statusFilter !== "all") params.status = statusFilter;
  if (priorityFilter !== "all") params.priority = priorityFilter;

  const { data: tasks, isLoading } = useListTasks(params, {
    query: { queryKey: getListTasksQueryKey(params) },
  });

  const { data: overdue } = useListOverdueTasks({
    query: { queryKey: getListOverdueTasksQueryKey() },
  });

  const { data: projects } = useListProjects({
    query: { queryKey: getListProjectsQueryKey() },
  });

  const { mutate: createTask, isPending: creating } = useCreateTask({
    mutation: {
      onSuccess: () => {
        queryClient.invalidateQueries({ queryKey: getListTasksQueryKey(params) });
        setShowCreate(false);
        setNewTitle("");
      },
    },
  });

  const { mutate: updateTask } = useUpdateTask({
    mutation: {
      onSuccess: () => queryClient.invalidateQueries({ queryKey: getListTasksQueryKey(params) }),
    },
  });

  const { mutate: deleteTask } = useDeleteTask({
    mutation: {
      onSuccess: () => queryClient.invalidateQueries({ queryKey: getListTasksQueryKey(params) }),
    },
  });

  const filtered = (tasks ?? []).filter((t: any) =>
    !search || t.title?.toLowerCase().includes(search.toLowerCase())
  );

  const overdueCount = overdue?.length ?? 0;

  return (
    <div className="p-4 md:p-6 max-w-[1400px]">
      <div className="flex items-center justify-between mb-4 md:mb-6">
        <div>
          <h1 className="text-xl md:text-2xl font-black text-foreground tracking-tight">Tasks</h1>
          <div className="flex items-center gap-2 mt-0.5">
            <p className="text-sm text-muted-foreground">{filtered.length} tasks</p>
            {overdueCount > 0 && (
              <button
                onClick={() => setShowOverdue(true)}
                className="flex items-center gap-1 text-xs font-semibold text-destructive hover:underline"
              >
                <AlertTriangle className="w-3 h-3" />
                {overdueCount} overdue
              </button>
            )}
          </div>
        </div>
        <Button size="sm" className="font-bold" onClick={() => setShowCreate(true)}>
          <Plus className="w-4 h-4 md:mr-1.5" />
          <span className="hidden md:inline">New Task</span>
        </Button>
      </div>

      <div className="flex flex-col sm:flex-row gap-2 mb-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <Input placeholder="Search tasks..." value={search} onChange={(e) => setSearch(e.target.value)} className="pl-9" />
        </div>
        <div className="flex gap-2">
          <Select value={statusFilter} onValueChange={setStatusFilter}>
            <SelectTrigger className="w-full sm:w-32">
              <SelectValue placeholder="Status" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Status</SelectItem>
              <SelectItem value="pending">Pending</SelectItem>
              <SelectItem value="in_progress">In Progress</SelectItem>
              <SelectItem value="completed">Completed</SelectItem>
              <SelectItem value="cancelled">Cancelled</SelectItem>
            </SelectContent>
          </Select>
          <Select value={priorityFilter} onValueChange={setPriorityFilter}>
            <SelectTrigger className="w-full sm:w-32">
              <SelectValue placeholder="Priority" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Priority</SelectItem>
              <SelectItem value="urgent">Urgent</SelectItem>
              <SelectItem value="high">High</SelectItem>
              <SelectItem value="normal">Normal</SelectItem>
              <SelectItem value="low">Low</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      <Card className="border-border">
        <CardContent className="p-0">
          {isLoading ? (
            <div className="p-4 space-y-2">{Array.from({ length: 5 }).map((_, i) => <Skeleton key={i} className="h-12" />)}</div>
          ) : filtered.length === 0 ? (
            <div className="py-16 text-center text-sm text-muted-foreground">No tasks found</div>
          ) : (
            <div className="divide-y divide-border">
              {filtered.map((t: any) => (
                <div key={t.id} className={cn("px-4 py-3 group", t.deadline && new Date(t.deadline) < new Date() && t.status !== "completed" ? "bg-destructive/5" : "")}>
                  <div className="flex items-center gap-3">
                    <div className={cn("w-2 h-2 rounded-full shrink-0", PRIORITY_DOT[t.priority] ?? "bg-muted-foreground")} />
                    <span className="text-sm font-medium text-foreground flex-1 truncate">{t.title}</span>
                    <div className="flex items-center gap-1.5 ml-auto shrink-0">
                      {t.deadline && (
                        <span className={cn("text-[10px] hidden sm:inline", new Date(t.deadline) < new Date() && t.status !== "completed" ? "text-destructive font-semibold" : "text-muted-foreground")}>
                          {format(new Date(t.deadline), "MMM d")}
                        </span>
                      )}
                      <Select
                        value={t.status}
                        onValueChange={(val) => updateTask({ taskId: t.id, data: { status: val as TaskUpdateStatus } })}
                      >
                        <SelectTrigger className={cn("w-24 sm:w-28 h-6 text-[11px] border shrink-0", STATUS_COLORS[t.status])}>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="pending">Pending</SelectItem>
                          <SelectItem value="in_progress">In Progress</SelectItem>
                          <SelectItem value="completed">Completed</SelectItem>
                          <SelectItem value="cancelled">Cancelled</SelectItem>
                        </SelectContent>
                      </Select>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-6 w-6 opacity-100 sm:opacity-0 sm:group-hover:opacity-100 text-muted-foreground hover:text-destructive shrink-0"
                        onClick={() => { if (confirm("Delete task?")) deleteTask({ taskId: t.id }); }}
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </Button>
                    </div>
                  </div>
                  {(t.project_name || t.assignee_name) && (
                    <div className="flex items-center gap-2 mt-1 pl-5">
                      {t.project_name && <Badge variant="outline" className="text-[10px] px-1.5 py-0">{t.project_name}</Badge>}
                      {t.assignee_name && <span className="text-[10px] text-muted-foreground">{t.assignee_name}</span>}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <Dialog open={showOverdue} onOpenChange={setShowOverdue}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle className="font-black flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-destructive" /> Overdue Tasks
            </DialogTitle>
          </DialogHeader>
          <div className="divide-y divide-border max-h-96 overflow-y-auto">
            {overdue?.map((t: any) => (
              <div key={t.id} className="flex items-start gap-3 py-2.5">
                <div className={cn("w-2 h-2 rounded-full mt-1.5 shrink-0", PRIORITY_DOT[t.priority])} />
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-semibold text-foreground">{t.title}</div>
                  <div className="text-[10px] text-destructive mt-0.5">Due {t.deadline ? format(new Date(t.deadline), "MMM d, yyyy") : "—"}</div>
                </div>
              </div>
            ))}
          </div>
        </DialogContent>
      </Dialog>

      <Dialog open={showCreate} onOpenChange={setShowCreate}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="font-black">New Task</DialogTitle>
          </DialogHeader>
          <div className="space-y-3 py-2">
            <div>
              <label className="text-xs font-semibold uppercase tracking-wide text-muted-foreground block mb-1.5">Title</label>
              <Input placeholder="Task title" value={newTitle} onChange={(e) => setNewTitle(e.target.value)} autoFocus />
            </div>
            <div>
              <label className="text-xs font-semibold uppercase tracking-wide text-muted-foreground block mb-1.5">Project</label>
              <Select value={newProjectId} onValueChange={setNewProjectId}>
                <SelectTrigger>
                  <SelectValue placeholder="Select project (optional)" />
                </SelectTrigger>
                <SelectContent>
                  {(projects ?? []).map((p: any) => (
                    <SelectItem key={p.id} value={p.id}>{p.name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <label className="text-xs font-semibold uppercase tracking-wide text-muted-foreground block mb-1.5">Priority</label>
              <Select value={newPriority} onValueChange={setNewPriority}>
                <SelectTrigger><SelectValue /></SelectTrigger>
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
              onClick={() => createTask({ data: { title: newTitle.trim(), priority: newPriority as TaskInputPriority, project_id: newProjectId || undefined } })}
            >
              {creating ? "Creating..." : "Create"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
