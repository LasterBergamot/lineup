import { useTranslation } from "react-i18next";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { CreateTeamForm } from "@/features/teams/create-team-form";

const INVITE_EXAMPLE = "https://…/join/…";

/**
 * First-run screen for a signed-in user who belongs to no team yet. Everything in the app
 * (roster, lineups) lives inside a team, so the two ways in are offered: create one, or join
 * an existing one from an invite link. Invitations do not exist in the API yet (#51), so the
 * link field is visible but disabled, to say where that path will be rather than hide it.
 */
export function Onboarding() {
  const { t } = useTranslation();
  return (
    <div className="mx-auto flex max-w-xl flex-col gap-6">
      <div className="flex flex-col gap-1">
        <h1 className="text-3xl font-semibold tracking-tight">{t("teams.onboarding.title")}</h1>
        <p className="text-muted-foreground">{t("teams.onboarding.intro")}</p>
      </div>
      <Card>
        <CardHeader>
          <CardTitle>{t("teams.onboarding.createTitle")}</CardTitle>
          <CardDescription>{t("teams.onboarding.createDescription")}</CardDescription>
        </CardHeader>
        <CardContent>
          <CreateTeamForm />
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle>{t("teams.onboarding.joinTitle")}</CardTitle>
          <CardDescription>{t("teams.onboarding.joinDescription")}</CardDescription>
        </CardHeader>
        <CardContent>
          <Field label={t("fields.inviteLink")}>
            {(props) => (
              <Input {...props} disabled placeholder={INVITE_EXAMPLE} aria-disabled="true" />
            )}
          </Field>
        </CardContent>
      </Card>
    </div>
  );
}
