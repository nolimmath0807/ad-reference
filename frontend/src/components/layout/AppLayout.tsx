import type { ReactNode } from "react";
import { SidebarProvider, SidebarInset, SidebarTrigger } from "@/components/ui/sidebar";
import { Separator } from "@/components/ui/separator";
import {
  Breadcrumb,
  BreadcrumbList,
  BreadcrumbItem,
  BreadcrumbPage,
} from "@/components/ui/breadcrumb";
import { useLocation } from "react-router-dom";
import { AppSidebar } from "./AppSidebar";
import { ActivityPanel } from "@/components/activity/ActivityPanel";

const pageTitles: Record<string, string> = {
  "/dashboard": "Dashboard",
  "/boards": "Boards",
  "/competitors": "Competitors",
  "/settings": "Settings",
};

export function AppLayout({ children }: { children: ReactNode }) {
  const location = useLocation();
  const currentTitle = pageTitles[location.pathname] ?? "Dashboard";

  return (
    <SidebarProvider>
      <AppSidebar />
      <SidebarInset>
        <header className="flex h-14 shrink-0 items-center gap-2 border-b px-4">
          <SidebarTrigger className="-ml-1" />
          <Separator orientation="vertical" className="mr-2 h-4" />
          <Breadcrumb>
            <BreadcrumbList>
              <BreadcrumbItem>
                <BreadcrumbPage>{currentTitle}</BreadcrumbPage>
              </BreadcrumbItem>
            </BreadcrumbList>
          </Breadcrumb>
        </header>
        <main className="flex-1 overflow-auto p-6">{children}</main>
      </SidebarInset>
      <ActivityPanel />
    </SidebarProvider>
  );
}
