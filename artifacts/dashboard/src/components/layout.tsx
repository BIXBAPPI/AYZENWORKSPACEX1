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
  BarChart3,
  Bell,
  Settings,
  LogOut,
  Zap,
  Menu,
} from "lucide-react";

const NAV = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/projects", label: "Projects", icon: FolderKanban },
  { href: "/tasks", label: "Tasks", icon: CheckSquare },
  { href: "/members", label: "Members", icon: Users },
  { href: "/broadcasts", label: "Broadcasts", icon: Megaphone },
  { href: "/analytics", label: "Analytics", icon: BarChart3 },
  { href: "/notifications", label: "Notifications", icon: Bell },
  { href: "/settings", label: "Settings", icon: Settings },
];

function SidebarContent({
  onNavigate,
}: {
  onNavigate?: () => void;
}) {
  const [location] = useLocation();
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

  return (
    <div className="flex flex-col h-full bg-sidebar">
      <div className="h-14 border-b border-sidebar-border flex items-center px-4 gap-2 shrink-0">
        <div className="w-7 h-7 bg-primary rounded-sm flex items-center justify-center">
          <Zap className="w-4 h-4 text-primary-foreground" />
        </div>
        <span className="font-bold text-sidebar-foreground tracking-tight text-sm">AYZEN</span>
        <Badge variant="outline" className="ml-auto text-[9px] px-1 py-0 h-4 border-primary/40 text-primary">
          BETA
        </Badge>
      </div>

      <nav className="flex-1 overflow-y-auto py-3 px-2">
        {NAV.map(({ href, label, icon: Icon }) => {
          const active = location === href || (href !== "/dashboard" && location.startsWith(href));
          return (
            <Link
              key={href}
              href={href}
              onClick={onNavigate}
              className={cn(
                "flex items-center gap-2.5 px-3 py-2.5 text-sm font-medium rounded-sm mb-0.5 transition-colors",
                active
                  ? "bg-sidebar-accent text-sidebar-primary"
                  : "text-sidebar-foreground/70 hover:text-sidebar-foreground hover:bg-sidebar-accent/50"
              )}
            >
              <Icon className="w-4 h-4 shrink-0" />
              {label}
            </Link>
          );
        })}
      </nav>

      <div className="border-t border-sidebar-border p-3 shrink-0">
        <div className="flex items-center gap-2 mb-2">
          <div className="w-7 h-7 rounded-sm bg-primary/20 flex items-center justify-center">
            <span className="text-xs font-bold text-primary">
              {user?.full_name?.[0]?.toUpperCase() ?? user?.email?.[0]?.toUpperCase() ?? "?"}
            </span>
          </div>
          <div className="flex-1 min-w-0">
            <div className="text-xs font-medium text-sidebar-foreground truncate">
              {user?.full_name ?? user?.email ?? "User"}
            </div>
            <div className="text-[10px] text-sidebar-foreground/50 truncate capitalize">{user?.role ?? "member"}</div>
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
      {/* Desktop sidebar — hidden on mobile */}
      <aside className="hidden md:flex w-56 shrink-0 border-r border-border flex-col">
        <SidebarContent />
      </aside>

      {/* Mobile: top bar + sheet drawer */}
      <div className="flex flex-col flex-1 min-w-0 overflow-hidden">
        {/* Mobile top bar — hidden on desktop */}
        <header className="md:hidden h-12 border-b border-border bg-sidebar flex items-center px-3 gap-2 shrink-0">
          <Sheet open={mobileOpen} onOpenChange={setMobileOpen}>
            <SheetTrigger asChild>
              <Button variant="ghost" size="icon" className="h-8 w-8 text-sidebar-foreground">
                <Menu className="w-5 h-5" />
              </Button>
            </SheetTrigger>
            <SheetContent side="left" className="p-0 w-64 bg-sidebar border-sidebar-border">
              <SidebarContent onNavigate={() => setMobileOpen(false)} />
            </SheetContent>
          </Sheet>
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 bg-primary rounded-sm flex items-center justify-center">
              <Zap className="w-3.5 h-3.5 text-primary-foreground" />
            </div>
            <span className="font-bold text-sidebar-foreground text-sm tracking-tight">AYZEN</span>
          </div>
          <Badge variant="outline" className="ml-auto text-[9px] px-1 py-0 h-4 border-primary/40 text-primary">
            BETA
          </Badge>
        </header>

        {/* Page content */}
        <main className="flex-1 overflow-y-auto min-w-0">
          {children}
        </main>
      </div>
    </div>
  );
}
