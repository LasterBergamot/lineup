import { useId, type ComponentProps } from "react";
import { useTranslation } from "react-i18next";
import { Input } from "@/components/ui/input";
import {
  findDirectoryMatch,
  MAX_OPPONENT_LENGTH,
  useOpponentOptions,
} from "@/features/creator/opponent/options";

/**
 * The opponent field of the lineup creator: free text with suggestions from the team's recent
 * opponents and the listed directory. It is a native `<input list>` + `<datalist>`, so phones
 * show their own suggestion UI and screen readers announce it as a combobox. `onChange` gets the
 * text and, when it is exactly a listed team's name, that team's id: send it as
 * `source_opponent_id`, otherwise send the text as `opponent_name`. Spread the props `Field`
 * gives (`id`, `aria-*`) onto it like on any input.
 */
export function OpponentCombobox({
  value,
  onChange,
  teamId,
  ...inputProps
}: {
  value: string;
  onChange: (value: string, match?: { directoryId: string }) => void;
  /** The team the lineup is for: its recent opponents are suggested, the team itself is not. */
  teamId: string;
} & Omit<ComponentProps<"input">, "value" | "onChange" | "list">) {
  const { t } = useTranslation();
  const listId = useId();
  const options = useOpponentOptions(teamId, value);
  return (
    <>
      <Input
        {...inputProps}
        autoComplete="off"
        maxLength={MAX_OPPONENT_LENGTH}
        list={listId}
        value={value}
        onChange={(event) =>
          onChange(event.target.value, findDirectoryMatch(options, event.target.value))
        }
      />
      <datalist id={listId}>
        {options.map((option) => (
          <option
            key={`${option.source}:${option.name}`}
            value={option.name}
            label={t(option.source === "directory" ? "opponent.directory" : "opponent.recent")}
          />
        ))}
      </datalist>
    </>
  );
}
