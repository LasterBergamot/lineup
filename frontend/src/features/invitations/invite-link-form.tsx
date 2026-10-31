import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router";
import { Button } from "@/components/ui/button";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import {
  inviteCodeFromInput,
  inviteLinkSchema,
  type InviteLinkValues,
} from "@/features/invitations/code";

const INVITE_EXAMPLE = "https://…/join/…";

/**
 * "Paste your invite link" on the onboarding screen. It takes the whole link or just the code,
 * keeps only the code and opens the same `/join/:code` page as clicking the link would, so there
 * is one joining flow. Only the code is used (never the pasted origin), so a link to another
 * site cannot send anyone away from here.
 */
export function InviteLinkForm() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<InviteLinkValues>({
    resolver: zodResolver(inviteLinkSchema),
    defaultValues: { link: "" },
  });

  return (
    <form
      noValidate
      className="flex flex-col gap-4"
      onSubmit={handleSubmit(({ link }) => {
        navigate(`/join/${encodeURIComponent(inviteCodeFromInput(link)!)}`);
      })}
    >
      <Field label={t("fields.inviteLink")} error={errors.link?.message}>
        {(props) => (
          <Input {...props} autoComplete="off" placeholder={INVITE_EXAMPLE} {...register("link")} />
        )}
      </Field>
      <Button type="submit" variant="secondary" className="self-start">
        {t("teams.onboarding.joinSubmit")}
      </Button>
    </form>
  );
}
