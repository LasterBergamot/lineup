import { LogOut } from "lucide-react";
import { useAuth } from "@/auth/context";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useTeams } from "@/features/teams/context";

/** The current team's name and the caller's role in it, or a skeleton while it loads. */
export function TeamLabel({ className }: { className?: string }) {
  const {
    query: { isPending },
    current,
  } = useTeams();
  if (isPending) return <Skeleton className="h-4 w-24" />;
  if (!current) return null;
  return (
    <div className={className}>
      <p className="truncate text-sm font-medium">{current.name}</p>
      <p className="text-xs text-muted-foreground capitalize">{current.role}</p>
    </div>
  );
}

/** Ends the session on this device. `compact` is the icon-only form for the mobile header. */
export function SignOutButton({ compact = false }: { compact?: boolean }) {
  const { signOut } = useAuth();
  if (compact) {
    return (
      <Button variant="ghost" size="icon" aria-label="Sign out" onClick={() => void signOut()}>
        <LogOut />
      </Button>
    );
  }
  return (
    <Button variant="ghost" className="justify-start" onClick={() => void signOut()}>
      <LogOut />
      Sign out
    </Button>
  );
}
