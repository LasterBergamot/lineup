import { LogOut } from "lucide-react";
import { useTranslation } from "react-i18next";
import { useAuth } from "@/auth/context";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useTeams } from "@/features/teams/context";
import { roleKey } from "@/features/teams/role";
import { cn } from "@/lib/utils";

/** Up to two initials of a team name, for the avatar. */
function initials(name: string): string {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((word) => word[0]!.toUpperCase())
    .join("");
}

/**
 * The current team's name and the caller's role in it, or a skeleton while it loads. `avatar`
 * adds a round initials badge before the text (decorative: the name is already beside it).
 */
export function TeamLabel({ className, avatar = false }: { className?: string; avatar?: boolean }) {
  const { t } = useTranslation();
  const {
    query: { isPending },
    current,
  } = useTeams();
  if (isPending) return <Skeleton className="h-4 w-24" />;
  if (!current) return null;
  const text = (
    <div className="min-w-0">
      <p className="truncate text-sm font-medium">{current.name}</p>
      <p className="text-xs text-muted-foreground capitalize">{t(roleKey(current.role))}</p>
    </div>
  );
  if (!avatar) return <div className={className}>{text}</div>;
  return (
    <div className={cn("flex items-center gap-3", className)}>
      <span
        aria-hidden="true"
        className="flex size-8 shrink-0 items-center justify-center rounded-pill bg-primary text-xs font-semibold text-primary-foreground"
      >
        {initials(current.name)}
      </span>
      {text}
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
