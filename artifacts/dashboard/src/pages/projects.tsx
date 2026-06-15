import { useState } from "react";
import { useListProjects, getListProjectsQueryKey, useCreateProject, useDeleteProject } from "@workspace/api-client-react";
import { useQueryClient } from "@tanstack/react-query";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { Skeleton } from "@/components/ui/skeleton";
import { Link } from "wouter";
import { Plus, Search, FolderKanban, ChevronRight, Trash2 } from "lucide-react";

export default function ProjectsPage() {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const [newName, setNewName] = useState("");
  const [newDesc, setNewDesc] = useState("");

  const { data: projects, isLoading } = useListProjects({
    query: { queryKey: getListProjectsQueryKey() },
  });

  const { mutate: createProject, isPending: creating } = useCreateProject({
    mutation: {
      onSuccess: () => {
        queryClient.invalidateQueries({ queryKey: getListProjectsQueryKey() });
        setShowCreate(false);
        setNewName("");
        setNewDesc("");
      },
    },
  });

  const { mutate: deleteProject } = useDeleteProject({
    mutation: {
      onSuccess: () => queryClient.invalidateQueries({ queryKey: getListProjectsQueryKey() }),
    },
  });

  const filtered = (projects ?? []).filter((p: any) =>
    !search || p.name?.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="p-6 max-w-[1400px]">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-black text-foreground tracking-tight">Projects</h1>
          <p className="text-sm text-muted-foreground mt-0.5">{filtered.length} project{filtered.length !== 1 ? "s" : ""}</p>
        </div>
        <Button size="sm" className="font-bold" onClick={() => setShowCreate(true)}>
          <Plus className="w-4 h-4 mr-1.5" /> New Project
        </Button>
      </div>

      <div className="mb-4 relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
        <Input
          placeholder="Search projects..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="pl-9"
        />
      </div>

      {isLoading ? (
        <div className="space-y-2">
          {Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-20" />)}
        </div>
      ) : filtered.length === 0 ? (
        <div className="py-20 text-center">
          <FolderKanban className="w-10 h-10 text-muted-foreground/50 mx-auto mb-3" />
          <p className="text-sm font-medium text-muted-foreground">No projects yet</p>
          <p className="text-xs text-muted-foreground mt-1">Create your first project to get started</p>
        </div>
      ) : (
        <div className="space-y-2">
          {filtered.map((p: any) => (
            <Card key={p.id} className="border-border hover:border-primary/30 transition-colors group">
              <CardContent className="p-4">
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 bg-primary/10 rounded-sm flex items-center justify-center shrink-0">
                    <FolderKanban className="w-4 h-4 text-primary" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-bold text-foreground">{p.name}</span>
                      <Badge variant="outline" className="text-[10px] px-1.5 py-0">
                        {p.task_count ?? 0} tasks
                      </Badge>
                    </div>
                    {p.description && (
                      <p className="text-xs text-muted-foreground mt-0.5 truncate">{p.description}</p>
                    )}
                  </div>
                  <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-7 w-7 text-muted-foreground hover:text-destructive"
                      onClick={(e) => {
                        e.preventDefault();
                        if (confirm("Delete this project?")) deleteProject({ projectId: p.id });
                      }}
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </Button>
                    <Link href={`/projects/${p.id}`} className="flex items-center">
                      <Button variant="ghost" size="icon" className="h-7 w-7">
                        <ChevronRight className="w-4 h-4" />
                      </Button>
                    </Link>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      <Dialog open={showCreate} onOpenChange={setShowCreate}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="font-black">New Project</DialogTitle>
          </DialogHeader>
          <div className="space-y-3 py-2">
            <div>
              <label className="text-xs font-semibold uppercase tracking-wide text-muted-foreground block mb-1.5">Name</label>
              <Input placeholder="Project name" value={newName} onChange={(e) => setNewName(e.target.value)} autoFocus />
            </div>
            <div>
              <label className="text-xs font-semibold uppercase tracking-wide text-muted-foreground block mb-1.5">Description (optional)</label>
              <Input placeholder="Short description..." value={newDesc} onChange={(e) => setNewDesc(e.target.value)} />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowCreate(false)}>Cancel</Button>
            <Button
              className="font-bold"
              disabled={!newName.trim() || creating}
              onClick={() => createProject({ data: { name: newName.trim(), description: newDesc || undefined } })}
            >
              {creating ? "Creating..." : "Create"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
