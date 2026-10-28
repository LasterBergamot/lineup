import type { ParseKeys, TFunction } from "i18next";
import { i18n } from "@/i18n";

/** Keys under `validation.` and `fields.` that form errors may use; typed by the locale files. */
type ValidationKey = Extract<ParseKeys, `validation.${string}`>;
type FieldLabelKey = Extract<ParseKeys, `fields.${string}`>;

export interface ErrorParams {
  /** A `fields.*` key: the label of the field the error is about, translated when shown. */
  field?: FieldLabelKey;
  max?: number;
}

const PREFIX = "i18n:";

/**
 * Builds a validation message that is translated when it is *shown*, not when it is created.
 * Zod schemas are module-level constants, so they cannot call `t()` at definition time (the
 * language may change later); they emit this encoded key instead and `Field` calls
 * {@link translateError} when it renders, so an error on screen re-translates on a language
 * switch. The encoding is a plain string because that is all Zod's `message` can carry.
 */
export function errorKey(key: ValidationKey, params: ErrorParams = {}): string {
  return PREFIX + JSON.stringify([key, params]);
}

/** Splits a message made by {@link errorKey} back into its key and params; `null` for any other text. */
export function decodeError(message: string): { key: ValidationKey; params: ErrorParams } | null {
  if (!message.startsWith(PREFIX)) return null;
  const [key, params] = JSON.parse(message.slice(PREFIX.length)) as [ValidationKey, ErrorParams];
  return { key, params };
}

/**
 * Turns a form error message into display text. Messages made by {@link errorKey} are
 * translated; anything else (the English sentences a server 422 carries, see `fieldErrors`)
 * is shown as it came. Takes `t` so a React caller re-renders with the language.
 */
export function translateError(message: string, t: TFunction = i18n.t): string {
  const decoded = decodeError(message);
  if (!decoded) return message;
  const { key, params } = decoded;
  return t(key, { ...params, field: params.field ? t(params.field) : undefined });
}
