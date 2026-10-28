import { LogOut } from "lucide-react";
import { useTranslation } from "react-i18next";
import { useAuth } from "@/auth/context";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useTeams } from "@/features/teams/context";

/**
 * The API's role names (`owner`, `member`) as locale keys. A role the UI does not know yet
 * falls back to a neutral label rather than showing the raw API value.
 */
function roleKey(role: string) {
  switch (role) {
    case "owner":
      return "account.role.owner";
    case "member":
      return "account.role.member";
    default:
      return "account.role.unknown";
  }
}

/** The current team's name and the caller's role in it, or a skeleton while it loads. */
export function TeamLabel({ className }: { className?: string }) {
  const { t } = useTranslation();
  const {
    query: { isPending },
    current,
  } = useTeams();
  if (isPending) return <Skeleton className="h-4 w-24" />;
  if (!current) return null;
  return (
    <div className={className}>
      <p className="truncate text-sm font-medium">{current.name}</p>
      <p className="text-xs text-muted-foreground capitalize">{t(roleKey(current.role))}</p>
    </div>
  );
}

/** Ends the session on this device. `compact` is the icon-only form for the mobile header. */
export function SignOutButton({ compact = false }: { compact?: boolean }) {
  const { t } = useTranslation();
  const { signOut } = useAuth();
  if (compact) {
    return (
      <Button
        variant="ghost"
        size="icon"
        aria-label={t("account.signOut")}
        onClick={() => void signOut()}
      >
        <LogOut />
      </Button>
    );
  }
  return (
    <Button variant="ghost" className="justify-start" onClick={() => void signOut()}>
      <LogOut />
      {t("account.signOut")}
    </Button>
  );
}
