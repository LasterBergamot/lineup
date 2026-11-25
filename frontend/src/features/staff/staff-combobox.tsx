import { useTranslation } from "react-i18next";
import { Combobox } from "@/components/ui/combobox";
import { staffSuggestions, type Staff, type StaffRole } from "@/features/staff/api";

/**
 * A staff field of the lineup creator and the Quick sheet (#289): free text, with the team's
 * entries for `role` as suggestions (the default first, then alphabetical). The field holds the
 * printed name, not an entry, so a typed name is fine and is never added to the staff list, and a
 * saved lineup does not refer to the entry. Spread the props `Field` gives onto it.
 */
export function StaffCombobox({
  staff,
  role,
  value,
  onChange,
  ...fieldProps
}: {
  staff: readonly Staff[];
  role: StaffRole;
  value: string;
  onChange: (name: string) => void;
  id?: string;
  "aria-invalid"?: boolean;
  "aria-describedby"?: string;
}) {
  const { t } = useTranslation();
  return (
    <Combobox
      {...fieldProps}
      freeText
      value={value}
      onChange={onChange}
      emptyLabel={t("staff.typeOrPick")}
      options={staffSuggestions(staff, role)}
    />
  );
}
