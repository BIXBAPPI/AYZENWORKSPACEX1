import { Switch, Route, Router as WouterRouter, Redirect } from "wouter";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "@/components/ui/toaster";
import { TooltipProvider } from "@/components/ui/tooltip";
import { AuthProvider, AuthGuard } from "@/lib/auth";
import NotFound from "@/pages/not-found";
import Login from "@/pages/login";
import Register from "@/pages/register";
import VerifyEmail from "@/pages/verify-email";
import DashboardPage from "@/pages/dashboard";
import ProjectsPage from "@/pages/projects";
import ProjectDetailPage from "@/pages/project-detail";
import TasksPage from "@/pages/tasks";
import MembersPage from "@/pages/members";
import BroadcastsPage from "@/pages/broadcasts";
import AnalyticsPage from "@/pages/analytics";
import AnalysisPage from "@/pages/analysis";
import DeveloperPage from "@/pages/developer";
import HealthPage from "@/pages/health";
import AccountsPage from "@/pages/accounts";
import NotificationsPage from "@/pages/notifications";
import SettingsPage from "@/pages/settings";
import AccountVaultPage from "@/pages/account-vault";
import ProfilePage from "@/pages/profile";
import GasTrackerPage from "@/pages/gas-tracker";
import AIAssistantPage from "@/pages/ai-assistant";
import HomePage from "@/pages/home";
import { AppLayout } from "@/components/layout";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      staleTime: 30_000,
    },
  },
});

function ProtectedRoute({ component: Component }: { component: React.ComponentType }) {
  return (
    <AuthGuard>
      <AppLayout>
        <Component />
      </AppLayout>
    </AuthGuard>
  );
}

function Router() {
  return (
    <Switch>
      <Route path="/" component={HomePage} />
      <Route path="/login" component={Login} />
      <Route path="/register" component={Register} />
      <Route path="/verify-email" component={VerifyEmail} />
      <Route path="/dashboard" component={() => <ProtectedRoute component={DashboardPage} />} />
      <Route path="/projects" component={() => <ProtectedRoute component={ProjectsPage} />} />
      <Route path="/projects/:id" component={() => <ProtectedRoute component={ProjectDetailPage} />} />
      <Route path="/tasks" component={() => <ProtectedRoute component={TasksPage} />} />
      <Route path="/members" component={() => <ProtectedRoute component={MembersPage} />} />
      <Route path="/broadcasts" component={() => <ProtectedRoute component={BroadcastsPage} />} />
      <Route path="/analytics" component={() => <ProtectedRoute component={AnalyticsPage} />} />
      <Route path="/analysis" component={() => <ProtectedRoute component={AnalysisPage} />} />
      <Route path="/accounts" component={() => <ProtectedRoute component={AccountsPage} />} />
      <Route path="/developer" component={() => <ProtectedRoute component={DeveloperPage} />} />
      <Route path="/health" component={() => <ProtectedRoute component={HealthPage} />} />
      <Route path="/notifications" component={() => <ProtectedRoute component={NotificationsPage} />} />
      <Route path="/settings" component={() => <ProtectedRoute component={SettingsPage} />} />
      <Route path="/vault" component={() => <ProtectedRoute component={AccountVaultPage} />} />
      <Route path="/profile" component={() => <ProtectedRoute component={ProfilePage} />} />
      <Route path="/gas" component={() => <ProtectedRoute component={GasTrackerPage} />} />
      <Route path="/ai" component={() => <ProtectedRoute component={AIAssistantPage} />} />
      <Route component={NotFound} />
    </Switch>
  );
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <TooltipProvider>
        <WouterRouter base={import.meta.env.BASE_URL.replace(/\/$/, "")}>
          <AuthProvider>
            <Router />
          </AuthProvider>
        </WouterRouter>
        <Toaster />
      </TooltipProvider>
    </QueryClientProvider>
  );
}

export default App;
