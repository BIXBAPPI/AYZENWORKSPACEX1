import { useState, useEffect, useCallback } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { useToast } from "@/hooks/use-toast";
import { useAuth } from "@/lib/auth";
import {
  BookOpen, Play, Clock, Star, ChevronLeft, ChevronRight, X,
  Search, Plus, Check, Bookmark, BookMarked, Eye, Code2, Image,
  Edit2, Trash2, Send, RefreshCw,
} from "lucide-react";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle
} from "@/components/ui/dialog";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

const api = (path: string, opts?: RequestInit) =>
  fetch(`/api/v1${path}`, { credentials: "include", ...opts });

function DiffBadge({ diff }: { diff: string }) {
  const map: Record<string, string> = {
    beginner: "bg-green-500/10 text-green-400 border-green-500/30",
    intermediate: "bg-yellow-500/10 text-yellow-400 border-yellow-500/30",
    advanced: "bg-red-500/10 text-red-400 border-red-500/30",
  };
  return <Badge className={map[diff] || ""}>{diff}</Badge>;
}

function StarRating({ value, onChange }: { value: number; onChange?: (v: number) => void }) {
  return (
    <div className="flex gap-1">
      {[1, 2, 3, 4, 5].map((s) => (
        <button key={s} onClick={() => onChange?.(s)} type="button">
          <Star className={`w-4 h-4 ${s <= value ? "fill-yellow-400 text-yellow-400" : "text-muted-foreground"}`} />
        </button>
      ))}
    </div>
  );
}

// ── Presentation Mode ──────────────────────────────────────────────────────

function PresentationMode({ tutorial, onClose, onProgress }: {
  tutorial: any; onClose: () => void; onProgress: (idx: number, done: boolean) => void;
}) {
  const [idx, setIdx] = useState(tutorial.user_last_slide || 0);
  const [showFeedback, setShowFeedback] = useState(false);
  const [rating, setRating] = useState(0);
  const [comment, setComment] = useState("");
  const { toast } = useToast();
  const slides = tutorial.slides || [];
  const slide = slides[idx];
  const total = slides.length;

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === "ArrowRight" || e.key === "ArrowDown") setIdx((i: number) => Math.min(i + 1, total - 1));
      if (e.key === "ArrowLeft" || e.key === "ArrowUp") setIdx((i: number) => Math.max(i - 1, 0));
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [total, onClose]);

  useEffect(() => {
    onProgress(idx, idx === total - 1);
  }, [idx]);

  const submitFeedback = async () => {
    if (!rating) return;
    await api(`/tutorials/${tutorial.id}/feedback`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ rating, comment }),
    });
    toast({ title: "Feedback submitted!", description: "Thank you for your rating." });
    setShowFeedback(false);
  };

  return (
    <div className="fixed inset-0 z-50 bg-background flex flex-col">
      <div className="flex items-center justify-between px-6 py-3 border-b border-border shrink-0">
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="icon" onClick={onClose}><X className="w-4 h-4" /></Button>
          <span className="font-semibold text-sm">{tutorial.title}</span>
        </div>
        <div className="flex items-center gap-4">
          <span className="text-xs text-muted-foreground">{idx + 1} / {total}</span>
          <Button variant="ghost" size="sm" onClick={() => setShowFeedback(true)}>
            <Star className="w-4 h-4 mr-1" /> Rate
          </Button>
        </div>
      </div>

      <div className="w-full h-1 bg-muted shrink-0">
        <div
          className="h-full transition-all duration-300"
          style={{ width: `${((idx + 1) / total) * 100}%`, background: "linear-gradient(90deg,#7c3aed,#06b6d4)" }}
        />
      </div>

      <div className="flex-1 overflow-y-auto flex flex-col items-center justify-center p-8">
        {slide ? (
          <div className="w-full max-w-3xl space-y-6">
            <h2 className="text-2xl font-bold text-center">{slide.title}</h2>
            {slide.type === "image" && slide.image_url && (
              <img src={slide.image_url} alt={slide.title} className="w-full rounded-lg max-h-64 object-contain" />
            )}
            {slide.content && (
              <div className="text-muted-foreground text-base leading-relaxed whitespace-pre-wrap text-center">
                {slide.content}
              </div>
            )}
            {slide.type === "code" && slide.code_snippet && (
              <pre className="bg-muted rounded-lg p-4 text-sm font-mono overflow-x-auto text-left border border-border">
                <code>{slide.code_snippet}</code>
              </pre>
            )}
            {slide.type === "video" && slide.image_url && (
              <iframe
                src={slide.image_url}
                className="w-full h-64 rounded-lg"
                allow="autoplay; encrypted-media"
                allowFullScreen
              />
            )}
          </div>
        ) : (
          <div className="text-muted-foreground">No slides</div>
        )}
      </div>

      <div className="flex items-center justify-between px-8 py-4 border-t border-border shrink-0">
        <Button variant="outline" onClick={() => setIdx((i: number) => Math.max(i - 1, 0))} disabled={idx === 0}>
          <ChevronLeft className="w-4 h-4 mr-1" /> Previous
        </Button>
        <div className="flex gap-1">
          {slides.map((_: any, i: number) => (
            <button
              key={i}
              onClick={() => setIdx(i)}
              className={`w-2 h-2 rounded-full transition-all ${i === idx ? "w-4" : ""}`}
              style={{ background: i <= idx ? "#7c3aed" : "#ffffff20" }}
            />
          ))}
        </div>
        {idx < total - 1 ? (
          <Button onClick={() => setIdx((i: number) => Math.min(i + 1, total - 1))}>
            Next <ChevronRight className="w-4 h-4 ml-1" />
          </Button>
        ) : (
          <Button onClick={() => { onProgress(idx, true); onClose(); }} className="bg-green-600 hover:bg-green-700">
            <Check className="w-4 h-4 mr-1" /> Finish
          </Button>
        )}
      </div>

      <Dialog open={showFeedback} onOpenChange={setShowFeedback}>
        <DialogContent>
          <DialogHeader><DialogTitle>Rate this tutorial</DialogTitle></DialogHeader>
          <div className="space-y-4 py-2">
            <div className="space-y-2">
              <Label>Rating</Label>
              <StarRating value={rating} onChange={setRating} />
            </div>
            <div className="space-y-2">
              <Label>Comment (optional)</Label>
              <Textarea value={comment} onChange={(e) => setComment(e.target.value)} placeholder="What did you think?" />
            </div>
          </div>
          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={() => setShowFeedback(false)}>Cancel</Button>
            <Button onClick={submitFeedback} disabled={!rating}><Send className="w-4 h-4 mr-1" /> Submit</Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}

// ── Admin: Create/Edit Tutorial ────────────────────────────────────────────

function TutorialEditor({ tutorial, onSave, onClose }: {
  tutorial?: any; onSave: () => void; onClose: () => void;
}) {
  const { toast } = useToast();
  const isEdit = !!tutorial;
  const [title, setTitle] = useState(tutorial?.title || "");
  const [desc, setDesc] = useState(tutorial?.description || "");
  const [diff, setDiff] = useState(tutorial?.difficulty || "beginner");
  const [est, setEst] = useState(String(tutorial?.estimated_time || 10));
  const [published, setPublished] = useState(tutorial?.published || false);
  const [slides, setSlides] = useState<any[]>(tutorial?.slides || []);
  const [saving, setSaving] = useState(false);

  const addSlide = () => {
    setSlides((prev) => [...prev, {
      id: crypto.randomUUID(), title: "", content: "", image_url: "",
      code_snippet: "", type: "text", order: prev.length,
    }]);
  };

  const updateSlide = (i: number, field: string, val: string) => {
    setSlides((prev) => prev.map((s, idx) => idx === i ? { ...s, [field]: val } : s));
  };

  const removeSlide = (i: number) => {
    setSlides((prev) => prev.filter((_, idx) => idx !== i));
  };

  const moveSlide = (i: number, dir: -1 | 1) => {
    const next = [...slides];
    const j = i + dir;
    if (j < 0 || j >= next.length) return;
    [next[i], next[j]] = [next[j], next[i]];
    setSlides(next);
  };

  const save = async () => {
    if (!title.trim()) { toast({ title: "Title required", variant: "destructive" }); return; }
    setSaving(true);
    const payload = { title, description: desc, difficulty: diff, estimated_time: Number(est), slides, published };
    const r = await api(isEdit ? `/tutorials/${tutorial.id}` : "/tutorials", {
      method: isEdit ? "PUT" : "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    setSaving(false);
    if (r.ok) {
      toast({ title: isEdit ? "Tutorial updated" : "Tutorial created" });
      onSave();
    } else {
      const e = await r.json();
      toast({ title: "Error", description: e.detail, variant: "destructive" });
    }
  };

  return (
    <Dialog open onOpenChange={onClose}>
      <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{isEdit ? "Edit Tutorial" : "Create Tutorial"}</DialogTitle>
        </DialogHeader>
        <div className="space-y-4 py-2">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1.5 col-span-2">
              <Label>Title *</Label>
              <Input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Tutorial title" />
            </div>
            <div className="space-y-1.5 col-span-2">
              <Label>Description</Label>
              <Textarea value={desc} onChange={(e) => setDesc(e.target.value)} rows={2} placeholder="What will users learn?" />
            </div>
            <div className="space-y-1.5">
              <Label>Difficulty</Label>
              <Select value={diff} onValueChange={setDiff}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="beginner">Beginner</SelectItem>
                  <SelectItem value="intermediate">Intermediate</SelectItem>
                  <SelectItem value="advanced">Advanced</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1.5">
              <Label>Est. Time (min)</Label>
              <Input type="number" value={est} onChange={(e) => setEst(e.target.value)} />
            </div>
          </div>

          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <Label>Slides ({slides.length})</Label>
              <Button size="sm" variant="outline" onClick={addSlide}><Plus className="w-3 h-3 mr-1" /> Add Slide</Button>
            </div>
            {slides.map((slide, i) => (
              <Card key={slide.id || i} className="border-border">
                <CardContent className="p-3 space-y-2">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-mono bg-muted px-2 py-0.5 rounded">{i + 1}</span>
                    <Input
                      value={slide.title}
                      onChange={(e) => updateSlide(i, "title", e.target.value)}
                      placeholder="Slide title"
                      className="flex-1 h-7 text-sm"
                    />
                    <Select value={slide.type} onValueChange={(v) => updateSlide(i, "type", v)}>
                      <SelectTrigger className="w-24 h-7 text-xs"><SelectValue /></SelectTrigger>
                      <SelectContent>
                        <SelectItem value="text">Text</SelectItem>
                        <SelectItem value="image">Image</SelectItem>
                        <SelectItem value="code">Code</SelectItem>
                        <SelectItem value="video">Video</SelectItem>
                      </SelectContent>
                    </Select>
                    <Button variant="ghost" size="icon" className="h-7 w-7" onClick={() => moveSlide(i, -1)} disabled={i === 0}>↑</Button>
                    <Button variant="ghost" size="icon" className="h-7 w-7" onClick={() => moveSlide(i, 1)} disabled={i === slides.length - 1}>↓</Button>
                    <Button variant="ghost" size="icon" className="h-7 w-7 text-destructive" onClick={() => removeSlide(i)}><Trash2 className="w-3.5 h-3.5" /></Button>
                  </div>
                  <Textarea
                    value={slide.content}
                    onChange={(e) => updateSlide(i, "content", e.target.value)}
                    placeholder="Slide content / instructions"
                    rows={2}
                    className="text-sm"
                  />
                  {(slide.type === "image" || slide.type === "video") && (
                    <Input
                      value={slide.image_url}
                      onChange={(e) => updateSlide(i, "image_url", e.target.value)}
                      placeholder={slide.type === "video" ? "YouTube embed URL" : "Image URL"}
                      className="text-sm"
                    />
                  )}
                  {slide.type === "code" && (
                    <Textarea
                      value={slide.code_snippet}
                      onChange={(e) => updateSlide(i, "code_snippet", e.target.value)}
                      placeholder="// code block"
                      rows={3}
                      className="text-sm font-mono"
                    />
                  )}
                </CardContent>
              </Card>
            ))}
            {slides.length === 0 && (
              <div className="text-center text-muted-foreground text-sm py-4 border border-dashed border-border rounded-lg">
                No slides yet — add your first slide above
              </div>
            )}
          </div>

          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="published"
              checked={published}
              onChange={(e) => setPublished(e.target.checked)}
              className="rounded"
            />
            <Label htmlFor="published" className="cursor-pointer">Published (visible to all users)</Label>
          </div>
        </div>
        <div className="flex justify-end gap-2 pt-2">
          <Button variant="outline" onClick={onClose}>Cancel</Button>
          <Button onClick={save} disabled={saving}>
            {saving ? <RefreshCw className="w-4 h-4 mr-1 animate-spin" /> : null}
            {isEdit ? "Save Changes" : "Create Tutorial"}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}

// ── Main Tutorials Page ────────────────────────────────────────────────────

export default function TutorialsPage() {
  const { user } = useAuth();
  const { toast } = useToast();
  const isAdmin = user?.role === "owner" || user?.role === "manager";
  const [tutorials, setTutorials] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [filterDiff, setFilterDiff] = useState("all");
  const [presenting, setPresenting] = useState<any>(null);
  const [editing, setEditing] = useState<any | true | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    const r = await api(`/tutorials${isAdmin ? "?published_only=false" : ""}`);
    if (r.ok) setTutorials(await r.json());
    setLoading(false);
  }, [isAdmin]);

  useEffect(() => { load(); }, [load]);

  const openTutorial = async (tut: any) => {
    const r = await api(`/tutorials/${tut.id}`);
    if (r.ok) setPresenting(await r.json());
  };

  const handleProgress = async (tutId: string, lastSlide: number, done: boolean) => {
    await api(`/tutorials/${tutId}/progress`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ last_slide: lastSlide, completed: done }),
    });
    if (done) {
      setTutorials((prev) => prev.map((t) => t.id === tutId ? { ...t, user_completed: true } : t));
      toast({ title: "Tutorial completed! 🎉" });
    }
  };

  const toggleBookmark = async (tut: any) => {
    await api(`/tutorials/${tut.id}/progress`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ bookmarked: !tut.user_bookmarked }),
    });
    setTutorials((prev) => prev.map((t) => t.id === tut.id ? { ...t, user_bookmarked: !t.user_bookmarked } : t));
  };

  const deleteTutorial = async (id: string) => {
    if (!confirm("Delete this tutorial?")) return;
    await api(`/tutorials/${id}`, { method: "DELETE" });
    setTutorials((prev) => prev.filter((t) => t.id !== id));
    toast({ title: "Tutorial deleted" });
  };

  const filtered = tutorials.filter((t) => {
    if (search && !t.title.toLowerCase().includes(search.toLowerCase())) return false;
    if (filterDiff !== "all" && t.difficulty !== filterDiff) return false;
    return true;
  });

  const stats = {
    total: tutorials.length,
    completed: tutorials.filter((t) => t.user_completed).length,
    bookmarked: tutorials.filter((t) => t.user_bookmarked).length,
  };

  return (
    <div className="p-6 space-y-6 max-w-5xl mx-auto">
      {presenting && (
        <PresentationMode
          tutorial={presenting}
          onClose={() => setPresenting(null)}
          onProgress={(idx, done) => handleProgress(presenting.id, idx, done)}
        />
      )}
      {editing && (
        <TutorialEditor
          tutorial={editing === true ? undefined : editing}
          onSave={() => { setEditing(null); load(); }}
          onClose={() => setEditing(null)}
        />
      )}

      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <BookOpen className="w-6 h-6 text-primary" /> Tutorials
          </h1>
          <p className="text-muted-foreground text-sm mt-0.5">Step-by-step guides for airdrop farming</p>
        </div>
        {isAdmin && (
          <Button onClick={() => setEditing(true)}>
            <Plus className="w-4 h-4 mr-1.5" /> Create Tutorial
          </Button>
        )}
      </div>

      <div className="grid grid-cols-3 gap-3">
        {[
          { label: "Total Tutorials", value: stats.total, color: "text-primary" },
          { label: "Completed", value: stats.completed, color: "text-green-400" },
          { label: "Bookmarked", value: stats.bookmarked, color: "text-yellow-400" },
        ].map(({ label, value, color }) => (
          <Card key={label} className="border-border">
            <CardContent className="p-4">
              <div className={`text-2xl font-bold ${color}`}>{value}</div>
              <div className="text-xs text-muted-foreground">{label}</div>
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="flex gap-3">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <Input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search tutorials..."
            className="pl-9"
          />
        </div>
        <Select value={filterDiff} onValueChange={setFilterDiff}>
          <SelectTrigger className="w-36"><SelectValue placeholder="Difficulty" /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All levels</SelectItem>
            <SelectItem value="beginner">Beginner</SelectItem>
            <SelectItem value="intermediate">Intermediate</SelectItem>
            <SelectItem value="advanced">Advanced</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {loading ? (
        <div className="text-center py-16 text-muted-foreground">Loading tutorials...</div>
      ) : filtered.length === 0 ? (
        <div className="text-center py-16 space-y-3">
          <BookOpen className="w-12 h-12 text-muted-foreground mx-auto" />
          <p className="text-muted-foreground">
            {tutorials.length === 0
              ? isAdmin ? "No tutorials yet. Create the first one!" : "No tutorials published yet."
              : "No tutorials match your search."}
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filtered.map((tut) => (
            <Card
              key={tut.id}
              className={`border-border hover:border-primary/40 transition-colors cursor-pointer group ${tut.user_completed ? "opacity-80" : ""}`}
            >
              <CardContent className="p-4 space-y-3">
                <div className="flex items-start justify-between gap-2">
                  <h3 className="font-semibold text-sm leading-tight line-clamp-2">{tut.title}</h3>
                  <div className="flex gap-1 shrink-0">
                    <Button
                      variant="ghost" size="icon" className="h-7 w-7"
                      onClick={(e) => { e.stopPropagation(); toggleBookmark(tut); }}
                    >
                      {tut.user_bookmarked
                        ? <BookMarked className="w-3.5 h-3.5 text-yellow-400" />
                        : <Bookmark className="w-3.5 h-3.5 text-muted-foreground" />}
                    </Button>
                    {isAdmin && (
                      <>
                        <Button variant="ghost" size="icon" className="h-7 w-7"
                          onClick={(e) => { e.stopPropagation(); setEditing(tut); }}>
                          <Edit2 className="w-3.5 h-3.5" />
                        </Button>
                        <Button variant="ghost" size="icon" className="h-7 w-7 text-destructive"
                          onClick={(e) => { e.stopPropagation(); deleteTutorial(tut.id); }}>
                          <Trash2 className="w-3.5 h-3.5" />
                        </Button>
                      </>
                    )}
                  </div>
                </div>

                {tut.description && (
                  <p className="text-xs text-muted-foreground line-clamp-2">{tut.description}</p>
                )}

                <div className="flex items-center gap-2 flex-wrap">
                  <DiffBadge diff={tut.difficulty} />
                  {!tut.published && isAdmin && (
                    <Badge variant="outline" className="text-[10px] border-orange-500/30 text-orange-400">Draft</Badge>
                  )}
                  {tut.user_completed && (
                    <Badge className="bg-green-500/10 text-green-400 border-green-500/30">
                      <Check className="w-2.5 h-2.5 mr-0.5" /> Done
                    </Badge>
                  )}
                </div>

                <div className="flex items-center gap-3 text-xs text-muted-foreground">
                  <span className="flex items-center gap-1"><Clock className="w-3 h-3" /> {tut.estimated_time}m</span>
                  <span className="flex items-center gap-1"><Eye className="w-3 h-3" /> {tut.view_count}</span>
                  <span className="flex items-center gap-1"><Code2 className="w-3 h-3" /> {tut.slide_count} slides</span>
                </div>

                <Button
                  className="w-full"
                  size="sm"
                  variant={tut.user_completed ? "outline" : "default"}
                  onClick={() => openTutorial(tut)}
                >
                  <Play className="w-3.5 h-3.5 mr-1.5" />
                  {tut.user_completed ? "Review" : "Start"}
                </Button>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
