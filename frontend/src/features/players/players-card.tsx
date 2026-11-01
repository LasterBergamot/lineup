import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { describeError } from "@/api/errors";
import { useAuth } from "@/auth/context";
import { ConfirmButton } from "@/components/confirm-button";
import { QueryBoundary } from "@/components/query-boundary";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  createPlayer,
  deletePlayer,
  listPlayers,
  playersKey,
  updatePlayer,
  type Player,
} from "@/features/players/api";
import { PlayerForm } from "@/features/players/player-form";
import type { Team } from "@/features/teams/api";

/**
 * A team's roster: add a player, then edit or delete each one in place. Every member may do all
 * of it (the API allows it; there is no role check here on purpose). Players are listed in the
 * API's order (oldest first), so a row does not jump after an edit. Each change reloads the list,
 * also after a failure: a 404 usually means another member deleted the player meanwhile. Deleting
 * asks to confirm first and leaves saved lineups as they are (they keep their own copy), which the
 * card says next to the list so nobody expects a deletion to reach old lineups.
 */
export function PlayersCard({ team }: { team: Team }) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const { userId } = useAuth();
  const key = playersKey(userId, team.id);
  const [editing, setEditing] = useState<string | null>(null);

  const players = useQuery({ queryKey: key, queryFn: () => listPlayers(team.id) });
  const refresh = () => queryClient.invalidateQueries({ queryKey: key });

  const remove = useMutation({
    mutationFn: (playerId: string) => deletePlayer(playerId),
    onSettled: refresh,
  });

  return (
    <Card>
      <CardHeader>
        <CardTitle>{t("players.title")}</CardTitle>
        <CardDescription>{t("players.description")}</CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-6">
        <PlayerForm
          label={t("players.addTitle")}
          submitLabel={t("players.add")}
          save={(values) => createPlayer(team.id, values)}
          onSettled={refresh}
          resetOnSuccess
        />
        <QueryBoundary
          query={players}
          skeleton={
            <div className="flex flex-col gap-2">
              <Skeleton className="h-12 w-full" />
              <Skeleton className="h-12 w-full" />
              <Skeleton className="h-12 w-full" />
            </div>
          }
        >
          {(rows) =>
            rows.length === 0 ? (
              <p className="text-sm text-muted-foreground">{t("players.empty")}</p>
            ) : (
              <div className="flex flex-col gap-2">
                <ul
                  aria-label={t("players.listLabel", { team: team.name })}
                  className="flex flex-col divide-y overflow-hidden rounded-lg border"
                >
                  {rows.map((player) => (
                    <li key={player.id} className="p-3">
                      {editing === player.id ? (
                        <PlayerForm
                          label={t("players.editLabel", { name: player.name })}
                          submitLabel={t("players.save")}
                          defaultValues={{ name: player.name, nsszNumber: player.nssz_number }}
                          save={(values) => updatePlayer(player, values)}
                          onSuccess={() => setEditing(null)}
                          onSettled={refresh}
                          onCancel={() => setEditing(null)}
                        />
                      ) : (
                        <PlayerRow
                          player={player}
                          deleting={remove.isPending && remove.variables === player.id}
                          onEdit={() => setEditing(player.id)}
                          onDelete={() => remove.mutate(player.id)}
                        />
                      )}
                    </li>
                  ))}
                </ul>
                <p className="text-xs text-muted-foreground">{t("players.deleteHint")}</p>
              </div>
            )
          }
        </QueryBoundary>
        {remove.isError && (
          <p role="alert" className="text-sm text-destructive">
            {describeError(remove.error, t)}
          </p>
        )}
      </CardContent>
    </Card>
  );
}

/** One roster row when it is not being edited: the player's data and its two actions. */
function PlayerRow({
  player,
  deleting,
  onEdit,
  onDelete,
}: {
  player: Player;
  deleting: boolean;
  onEdit: () => void;
  onDelete: () => void;
}) {
  const { t } = useTranslation();
  return (
    <div className="flex flex-wrap items-center justify-between gap-3">
      <div className="flex min-w-0 flex-col gap-0.5">
        <span className="text-sm font-medium break-words">{player.name}</span>
        <span className="text-xs text-muted-foreground">
          {t("players.nssz", { number: player.nssz_number })}
        </span>
      </div>
      <div className="flex flex-wrap gap-2">
        <Button
          size="sm"
          variant="outline"
          aria-label={t("players.editLabel", { name: player.name })}
          onClick={onEdit}
        >
          {t("players.edit")}
        </Button>
        <ConfirmButton
          label={t("players.delete")}
          confirmLabel={t("players.deleteConfirm")}
          ariaLabel={t("players.deleteLabel", { name: player.name })}
          loading={deleting}
          onConfirm={onDelete}
        />
      </div>
    </div>
  );
}
