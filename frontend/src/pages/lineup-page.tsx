import { LineupForm } from "@/features/lineup/lineup-form";

/** One-off lineup: fill in the sheet and download it; nothing is stored. */
export function LineupPage() {
  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-1">
        <h1 className="text-3xl font-semibold tracking-tight">Lineup</h1>
        <p className="text-muted-foreground">
          Fill in the match and the players, then download the lineup sheet as PDF or DOCX. Nothing
          is saved.
        </p>
      </div>
      <LineupForm />
    </div>
  );
}
