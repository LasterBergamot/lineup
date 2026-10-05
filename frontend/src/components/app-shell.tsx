import { NavLink, Outlet } from "react-router";
import { BackendStatusBanner } from "@/backend-status/banner";
import { NAV_ITEMS } from "@/components/nav-items";
import { ThemeToggle } from "@/components/theme-toggle";
import { cn } from "@/lib/utils";

function Brand() {
  return (
    <div className="flex items-center gap-2 text-lg font-semibold tracking-tight">
      <img src="/favicon.svg" alt="" className="size-6" />
      Lineup
    </div>
  );
}

/**
 * Static page frame: a sidebar from the `md` breakpoint up, a top bar plus bottom navigation
 * below it. It renders without waiting for any API call, so a cold-starting backend never
 * blanks the screen; routed pages fill the `<main>` area, under the backend status banner.
 */
export function AppShell() {
  return (
    <div className="min-h-dvh md:grid md:grid-cols-[16rem_1fr]">
      <aside className="sticky top-0 hidden h-dvh flex-col border-r bg-sidebar text-sidebar-foreground md:flex">
        <div className="p-6">
          <Brand />
        </div>
        <nav aria-label="Sidebar" className="flex flex-1 flex-col gap-1 px-3">
          {NAV_ITEMS.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              end={to === "/"}
              className={({ isActive }) =>
                cn(
                  "flex items-center gap-3 px-3 py-2 text-sm font-medium hover:bg-sidebar-accent hover:text-sidebar-accent-foreground",
                  isActive &&
                    "bg-sidebar-primary text-sidebar-primary-foreground hover:bg-sidebar-primary",
                )
              }
            >
              <Icon className="size-4" />
              {label}
            </NavLink>
          ))}
        </nav>
        <div className="border-t p-3">
          <ThemeToggle />
        </div>
      </aside>

      <div className="flex min-w-0 flex-col">
        <header className="sticky top-0 z-10 flex items-center justify-between border-b bg-sidebar px-4 py-2 md:hidden">
          <Brand />
          <ThemeToggle />
        </header>
        <BackendStatusBanner />
        <main className="mx-auto w-full max-w-[1200px] flex-1 p-4 pb-24 md:p-8 md:pb-8">
          <Outlet />
        </main>
      </div>

      <nav
        aria-label="Bottom"
        className="fixed inset-x-0 bottom-0 z-10 grid grid-cols-3 border-t bg-sidebar pb-[env(safe-area-inset-bottom)] md:hidden"
      >
        {NAV_ITEMS.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            end={to === "/"}
            className={({ isActive }) =>
              cn(
                "flex flex-col items-center gap-1 py-2 text-xs font-medium text-muted-foreground",
                isActive && "text-primary",
              )
            }
          >
            <Icon className="size-5" />
            {label}
          </NavLink>
        ))}
      </nav>
    </div>
  );
}
