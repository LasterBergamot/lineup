import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { CreateTeamForm } from "@/features/teams/create-team-form";

/**
 * First-run screen for a signed-in user who belongs to no team yet. Everything in the app
 * (roster, lineups) lives inside a team, so the two ways in are offered: create one, or join
 * an existing one from an invite link. Invitations do not exist in the API yet (#51), so the
 * link field is visible but disabled, to say where that path will be rather than hide it.
 */
export function Onboarding() {
  return (
    <div className="mx-auto flex max-w-xl flex-col gap-6">
      <div className="flex flex-col gap-1">
        <h1 className="text-3xl font-semibold tracking-tight">Welcome to Lineup</h1>
        <p className="text-muted-foreground">
          You&apos;re not in a team yet. Create your team to start, or join one you&apos;ve been
          invited to.
        </p>
      </div>
      <Card>
        <CardHeader>
          <CardTitle>Create a team</CardTitle>
          <CardDescription>
            A team is your club&apos;s shared workspace: its roster and saved lineups. You become
            its owner.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <CreateTeamForm />
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle>Join with an invite link</CardTitle>
          <CardDescription>
            Coming soon: open the link your team owner sent you, or paste it here.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Field label="Invite link">
            {(props) => (
              <Input {...props} disabled placeholder="https://…/join/…" aria-disabled="true" />
            )}
          </Field>
        </CardContent>
      </Card>
    </div>
  );
}
