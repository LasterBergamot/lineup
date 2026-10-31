import { useTranslation } from "react-i18next";
import { InvitePanel } from "@/features/invitations/invite-panel";
import { MembersList } from "@/features/members/members-list";
import { useTeams } from "@/features/teams/context";

/**
 * The current team's people: who is in it and, for an owner, the invite link tools. Members see
 * the list only; the controls an owner has are hidden from them (the server enforces it anyway).
 */
export function MembersPage() {
  const { t } = useTranslation();
  const { current } = useTeams();
  if (!current) return null;
  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-1">
        <h1 className="text-3xl font-semibold tracking-tight">{t("members.title")}</h1>
        <p className="text-muted-foreground">{t("members.description", { team: current.name })}</p>
      </div>
      <div className="grid max-w-3xl gap-6">
        <MembersList team={current} />
        {current.role === "owner" && <InvitePanel team={current} />}
      </div>
    </div>
  );
}
