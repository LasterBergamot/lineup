import { Link } from "react-router";
import { Button } from "@/components/ui/button";

export function NotFoundPage() {
  return (
    <div className="flex flex-col items-start gap-4">
      <h1 className="text-3xl font-semibold tracking-tight">Page not found</h1>
      <p className="text-muted-foreground">That address doesn&apos;t match anything here.</p>
      <Button asChild>
        <Link to="/">Back to the lineup</Link>
      </Button>
    </div>
  );
}
