/**
 * The API's role names (`owner`, `member`) as locale keys. A role the UI does not know yet
 * falls back to a neutral label rather than showing the raw API value.
 */
export function roleKey(role: string) {
  switch (role) {
    case "owner":
      return "account.role.owner";
    case "member":
      return "account.role.member";
    default:
      return "account.role.unknown";
  }
}
