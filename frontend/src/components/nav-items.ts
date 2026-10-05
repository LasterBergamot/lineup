import { Bookmark, FileText, Users, type LucideIcon } from "lucide-react";

export interface NavItem {
  to: string;
  label: string;
  icon: LucideIcon;
}

/** The three top-level areas; shown in the sidebar on desktop and the bottom bar on mobile. */
export const NAV_ITEMS: NavItem[] = [
  { to: "/", label: "Lineup", icon: FileText },
  { to: "/roster", label: "Roster", icon: Users },
  { to: "/saved", label: "Saved", icon: Bookmark },
];
