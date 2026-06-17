import { useState } from "react";
import { Link, useLocation } from "wouter";
import { cn } from "@/lib/utils";
import { useAuth } from "@/lib/auth";
import { useLogout } from "@workspace/api-client-react";
import { useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Sheet, SheetContent, SheetTrigger } from "@/components/ui/sheet";
import {
  LayoutDashboard,
  FolderKanban,
  CheckSquare,
  Users,
  Megaphone,
  Bell,
  Settings,
  LogOut,
  Zap,
  Menu,
  TrendingUp,
  Code2,
  Activity,
  Lock,
  User,
  Fuel,
  Bot,
  Shield,
  BookOpen,
  Wrench,
  Crown,
  ChevronDown,
  ChevronRight,
  Star,
  MessageSquare,
  BarChart3,
} from "lucide-react";

type NavItem = {
  href?: string;
  label: string;
  icon: React.ElementType;
  children?: { href: string; label: string }[];
  adminOnly?: boolean;
};

const NAV_ITEMS: NavItem[] = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  {
    label: "Projects",
    icon: FolderKanban,
    children: [
      { href: "/projects", label: "All Projects" },
      { href: "/project-analytics", label: "Project Analytics" },
    ],
  },
  { href: "/tasks", label: "Tasks", icon: CheckSquare },
  {
    label: "Tutorials",
    icon: BookOpen,
    children: [
      { href: "/tutorials", label: "Browse Tutorials" },
      { href: "/tutorials?bookmarked=true", label: "My Bookmarks" },
    ],
  },
  {
    label: "Tools",
    icon: Wrench,
    children: [
      { href: "/tools", label: "All Tools" },
      { href: "/gas", label: "Gas Tracker" },
    ],
  },
  { href: "/vault", label: "Vault", icon: Lock },
  { href: "/members", label: "Members", icon: Users },
  { href: "/broadcasts", label: "Broadcasts", icon: Megaphone },
  { href: "/analysis", label: "Analysis", icon: TrendingUp },
  { href: "/notifications", label: "Notifications", icon: Bell },
  { href: "/profile", label: "Profile", icon: User },
  {
    label: "Settings",
    icon: Settings,
    children: [
      { href: "/settings", label: "General" },
      { href: "/subscription", label: "Subscription" },
    ],
  },
];

const NAV_ADMIN: NavItem[] = [
  {
    label: "Admin Panel",
    icon: Shield,
    children: [
      { href: "/admin", label: "User Management" },
      { href: "/telegram-link", label: "Telegram Linking" },
      { href: "/tutorials?admin=true", label: "Slide Generator" },
      { href: "/feedback", label: "Feedback Center" },
      { href: "/analytics", label: "Analytics" },
    ],
  },
  { href: "/ai", label: "AI Assistant", icon: Bot },
  { href: "/developer", label: "Developer", icon: Code2 },
  { href: "/health", label: "Health", icon: Activity },
];

function NavGroup({
  item,
  onNavigate,
}: {
  item: NavItem;
  onNavigate?: () => void;
}) {
  const [location] = useLocation();
  const isChildActive = item.children?.some(
    (c) => location === c.href || location.startsWith(c.href.split("?")[0])
  );
  const [open, setOpen] = useState(isChildActive || false);

  if (!item.children) {
    const active =
      location === item.href ||
      (item.href !== "/dashboard" && location.startsWith(item.href!));
    return (
      <Link
        href={item.href!}
        onClick={onNavigate}
        className={cn(
          "flex items-center gap-2.5 px-3 py-2 text-sm font-medium rounded-sm mb-0.5 transition-colors",
          active
            ? "bg-sidebar-accent text-sidebar-primary"
            : "text-sidebar-foreground/70 hover:text-sidebar-foreground hover:bg-sidebar-accent/50"
        )}
      >
        <item.icon className="w-4 h-4 shrink-0" />
        {item.label}
      </Link>
    );
  }

  return (
    <div>
      <button
        onClick={() => setOpen((v) => !v)}
        className={cn(
          "w-full flex items-center gap-2.5 px-3 py-2 text-sm font-medium rounded-sm mb-0.5 transition-colors",
          isChildActive
            ? "text-sidebar-primary"
            : "text-sidebar-foreground/70 hover:text-sidebar-foreground hover:bg-sidebar-accent/50"
        )}
      >
        <item.icon className="w-4 h-4 shrink-0" />
        <span className="flex-1 text-left">{item.label}</span>
        {open ? (
          <ChevronDown className="w-3.5 h-3.5 opacity-60" />
        ) : (
          <ChevronRight className="w-3.5 h-3.5 opacity-60" />
        )}
      </button>
      {open && (
        <div className="ml-4 pl-3 border-l border-sidebar-border/50 mb-1">
          {item.children.map((child) => {
            const childPath = child.href.split("?")[0];
            const active =
              location === child.href || location === childPath || location.startsWith(childPath + "/");
            return (
              <Link
                key={child.href}
                href={child.href}
                onClick={onNavigate}
                className={cn(
                  "flex items-center px-2 py-1.5 text-xs rounded-sm mb-0.5 transition-colors",
                  active
                    ? "text-sidebar-primary font-medium"
                    : "text-sidebar-foreground/60 hover:text-sidebar-foreground hover:bg-sidebar-accent/30"
                )}
              >
                {child.label}
              </Link>
            );
          })}
        </div>
      )}
    </div>
  );
}

function SidebarContent({ onNavigate }: { onNavigate?: () => void }) {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const { mutate: logout } = useLogout({
    mutation: {
      onSuccess: () => {
        queryClient.clear();
        window.location.href = "/login";
      },
    },
  });

  const isAdmin = user?.role === "owner" || user?.role === "manager";
  const xp = user?.global_xp || 0;
  const tier =
    xp >= 20000 ? "💎" : xp >= 5000 ? "🥇" : xp >= 1000 ? "🥈" : "🥉";

  return (
    <div className="flex flex-col h-full bg-sidebar">
      <div className="h-14 border-b border-sidebar-border flex items-center px-4 gap-2 shrink-0">
        <div
          className="w-7 h-7 flex items-center justify-center rounded-sm"
          style={{ background: "linear-gradient(135deg,#7c3aed,#06b6d4)" }}
        >
          <Zap className="w-4 h-4 text-white" />
        </div>
        <span
          className="font-black text-sidebar-foreground tracking-tight text-sm"
          style={{
            background: "linear-gradient(135deg,#7c3aed,#06b6d4)",
            WebkitBackgroundClip: "text",
            WebkitTextFillColor: "transparent",
          }}
        >
          AYZEN
        </span>
        <Badge
          variant="outline"
          className="ml-auto text-[9px] px-1 py-0 h-4 border-primary/40 text-primary"
        >
          V5
        </Badge>
      </div>

      <nav className="flex-1 overflow-y-auto py-2 px-2">
        {NAV_ITEMS.map((item) => (
          <NavGroup key={item.label} item={item} onNavigate={onNavigate} />
        ))}

        {isAdmin && (
          <>
            <div className="mt-3 mb-1 px-3">
              <span className="text-[9px] font-bold uppercase tracking-widest text-sidebar-foreground/30">
                Admin
              </span>
            </div>
            {NAV_ADMIN.map((item) => (
              <NavGroup key={item.label} item={item} onNavigate={onNavigate} />
            ))}
          </>
        )}
      </nav>

      <div className="border-t border-sidebar-border p-3 shrink-0">
        <div className="flex items-center gap-2 mb-2">
          <div className="w-7 h-7 rounded-sm bg-primary/20 flex items-center justify-center text-xs font-bold text-primary relative">
            {user?.avatar_url ? (
              <img
                src={user.avatar_url}
                alt=""
                className="w-full h-full rounded-sm object-cover"
              />
            ) : (
              user?.full_name?.[0]?.toUpperCase() ??
              user?.email?.[0]?.toUpperCase() ??
              "?"
            )}
          </div>
          <div className="flex-1 min-w-0">
            <div className="text-xs font-medium text-sidebar-foreground truncate flex items-center gap-1">
              {user?.full_name ?? user?.email ?? "User"}
              <span title={`${xp} XP`}>{tier}</span>
            </div>
            <div className="text-[10px] text-sidebar-foreground/50 truncate capitalize">
              {user?.role ?? "member"} · {xp.toLocaleString()} XP
            </div>
          </div>
        </div>
        <Button
          variant="ghost"
          size="sm"
          className="w-full justify-start h-7 px-2 text-xs text-sidebar-foreground/60 hover:text-destructive hover:bg-destructive/10"
          onClick={() => logout()}
        >
          <LogOut className="w-3.5 h-3.5 mr-1.5" />
          Sign out
        </Button>
      </div>
    </div>
  );
}

export function AppLayout({ children }: { children: React.ReactNode }) {
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <div className="flex h-screen bg-background overflow-hidden">
      <aside className="hidden md:flex w-56 shrink-0 border-r border-border flex-col">
        <SidebarContent />
      </aside>

      <div className="flex flex-col flex-1 min-w-0 overflow-hidden">
        <header className="md:hidden h-12 border-b border-border bg-sidebar flex items-center px-3 gap-2 shrink-0">
          <Sheet open={mobileOpen} onOpenChange={setMobileOpen}>
            <SheetTrigger asChild>
              <Button
                variant="ghost"
                size="icon"
                className="h-8 w-8 text-sidebar-foreground"
              >
                <Menu className="w-5 h-5" />
              </Button>
            </SheetTrigger>
            <SheetContent
              side="left"
              className="p-0 w-64 bg-sidebar border-sidebar-border"
            >
              <SidebarContent onNavigate={() => setMobileOpen(false)} />
            </SheetContent>
          </Sheet>
          <div className="flex items-center gap-2">
            <div
              className="w-6 h-6 rounded-sm flex items-center justify-center"
              style={{ background: "linear-gradient(135deg,#7c3aed,#06b6d4)" }}
            >
              <Zap className="w-3.5 h-3.5 text-white" />
            </div>
            <span className="font-black text-sidebar-foreground text-sm tracking-tight">
              AYZEN
            </span>
          </div>
          <Badge
            variant="outline"
            className="ml-auto text-[9px] px-1 py-0 h-4 border-primary/40 text-primary"
          >
            V5
          </Badge>
        </header>

        <main className="flex-1 overflow-y-auto min-w-0">{children}</main>
      </div>
    </div>
  );
}
