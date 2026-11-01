import { useTranslation } from "react-i18next";
import { NavLink, Outlet } from "react-router";
import { BackendStatusBanner } from "@/backend-status/banner";
import { SignOutButton, TeamLabel } from "@/components/account-panel";
import { Brand } from "@/components/brand";
import { LanguageSwitch } from "@/components/language-switch";
import { NAV_ITEMS } from "@/components/nav-items";
import { ThemeToggle } from "@/components/theme-toggle";
import { TeamGate } from "@/features/teams/team-gate";
import { cn } from "@/lib/utils";

/**
 * Static page frame: a sidebar from the `md` breakpoint up, a top bar plus bottom navigation
 * below it. It renders without waiting for any API call, so a cold-starting backend never
 * blanks the screen; routed pages fill the `<main>` area (behind the team gate, which shows the
 * onboarding screen to a user with no team), under the backend status banner. The account block
 * shows the current team and signs out.
 */
export function AppShell() {
  const { t } = useTranslation();
  return (
    <div className="min-h-dvh md:grid md:grid-cols-[16rem_1fr]">
      <aside className="sticky top-0 hidden h-dvh flex-col border-r bg-sidebar text-sidebar-foreground md:flex">
        <div className="p-6">
          <Brand />
        </div>
        <nav aria-label={t("nav.sidebar")} className="flex flex-1 flex-col gap-1 px-3">
          {NAV_ITEMS.map(({ to, labelKey, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              end={to === "/"}
              className={({ isActive }) =>
                cn(
                  "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium hover:bg-accent hover:text-accent-foreground",
                  isActive &&
                    "bg-sidebar-accent text-sidebar-accent-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground",
                )
              }
            >
              <Icon className="size-4" />
              {t(labelKey)}
            </NavLink>
          ))}
        </nav>
        <div className="flex flex-col gap-2 border-t p-3">
          <TeamLabel avatar className="min-w-0 px-3" />
          <LanguageSwitch className="px-1" />
          <SignOutButton />
          <ThemeToggle />
        </div>
      </aside>

      <div className="flex min-w-0 flex-col">
        <header className="sticky top-0 z-10 flex items-center justify-between border-b bg-sidebar px-4 pt-[calc(0.5rem+env(safe-area-inset-top))] pb-2 md:hidden">
          <Brand />
          <div className="flex min-w-0 items-center gap-1">
            <TeamLabel className="max-w-24 min-w-0 text-right" />
            <LanguageSwitch />
            <SignOutButton compact />
            <ThemeToggle />
          </div>
        </header>
        <BackendStatusBanner />
        <main className="mx-auto w-full max-w-[1200px] flex-1 p-4 pb-24 md:p-8 md:pb-8">
          <TeamGate>
            <Outlet />
          </TeamGate>
        </main>
      </div>

      <nav
        aria-label={t("nav.bottom")}
        className="fixed inset-x-0 bottom-0 z-10 grid grid-cols-4 border-t bg-sidebar pb-[env(safe-area-inset-bottom)] md:hidden"
      >
        {NAV_ITEMS.map(({ to, labelKey, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            end={to === "/"}
            className={({ isActive }) =>
              cn(
                "flex flex-col items-center gap-1 py-2 text-xs font-medium text-muted-foreground",
                isActive && "text-sidebar-accent-foreground",
              )
            }
          >
            {({ isActive }) => (
              <>
                <span
                  className={cn(
                    "flex h-7 w-14 items-center justify-center rounded-pill transition-colors",
                    isActive && "bg-sidebar-accent",
                  )}
                >
                  <Icon className="size-5" />
                </span>
                {t(labelKey)}
              </>
            )}
          </NavLink>
        ))}
      </nav>
    </div>
  );
}
