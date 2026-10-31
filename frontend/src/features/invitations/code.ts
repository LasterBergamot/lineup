import { z } from "zod";
import { errorKey } from "@/i18n/error-key";

/** The longest code the API accepts in a path (`CodePath` in `invitations/router.py`). */
const MAX_CODE_LENGTH = 200;
/** What `secrets.token_urlsafe` produces: letters, digits, `-` and `_`. */
const CODE = /^[A-Za-z0-9_-]+$/;

/**
 * Pulls the invite code out of what a person pasted: the whole link (`https://…/join/<code>`,
 * from any origin) or the bare code. Returns `null` when it does not look like a code. Only the
 * code is used afterwards, to build a same-site path, so a link to another site cannot send
 * anyone away from here.
 */
export function inviteCodeFromInput(raw: string): string | null {
  const text = raw.trim();
  let candidate = text;
  const marker = text.match(/\/join\/([^/?#\s]+)/);
  if (marker) candidate = marker[1]!;
  return candidate.length <= MAX_CODE_LENGTH && CODE.test(candidate) ? candidate : null;
}

/** The "paste an invite link" field on the onboarding screen. */
export const inviteLinkSchema = z.object({
  link: z
    .string()
    .trim()
    .min(1, errorKey("validation.required", { field: "fields.inviteLink" }))
    .refine((value) => inviteCodeFromInput(value) !== null, errorKey("validation.inviteLink")),
});

export type InviteLinkValues = z.infer<typeof inviteLinkSchema>;
