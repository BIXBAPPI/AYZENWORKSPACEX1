import { Link, useLocation } from "wouter";
import { cn } from "@/lib/utils";
import { useAuth } from "@/lib/auth";
import { useLogout } from "@workspace/api-client-react";
import { useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
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

export function AppLayout({ children }: { children: React.ReactNode }) {
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
    <div className="flex h-screen bg-background overflow-hidden">
      <aside className="w-56 shrink-0 border-r border-border flex flex-col bg-sidebar">
        <div className="h-14 border-b border-sidebar-border flex items-center px-4 gap-2">
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
              <Link key={href} href={href}>
                <a
                  className={cn(
                    "flex items-center gap-2.5 px-3 py-2 text-sm font-medium rounded-sm mb-0.5 transition-colors",
                    active
                      ? "bg-sidebar-accent text-sidebar-primary"
                      : "text-sidebar-foreground/70 hover:text-sidebar-foreground hover:bg-sidebar-accent/50"
                  )}
                >
                  <Icon className="w-4 h-4 shrink-0" />
                  {label}
                </a>
              </Link>
            );
          })}
        </nav>

        <div className="border-t border-sidebar-border p-3">
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
            onClick={() => logout({ data: {} })}
          >
            <LogOut className="w-3.5 h-3.5 mr-1.5" />
            Sign out
          </Button>
        </div>
      </aside>

      <main className="flex-1 overflow-y-auto min-w-0">
        {children}
      </main>
    </div>
  );
}
