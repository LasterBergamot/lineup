import { Bookmark, FileText, Users, type LucideIcon } from "lucide-react";
import type { ParseKeys } from "i18next";

export interface NavItem {
  to: string;
  /** Locale key of the visible label (translated where the item is rendered). */
  labelKey: ParseKeys;
  icon: LucideIcon;
}

/** The three top-level areas; shown in the sidebar on desktop and the bottom bar on mobile. */
export const NAV_ITEMS: NavItem[] = [
  { to: "/", labelKey: "nav.lineup", icon: FileText },
  { to: "/roster", labelKey: "nav.roster", icon: Users },
  { to: "/saved", labelKey: "nav.saved", icon: Bookmark },
];
