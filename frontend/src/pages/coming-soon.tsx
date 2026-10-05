import { Card, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

/** Placeholder for an area whose screens are still to be built (see PLAN.md phases 5–6). */
export function ComingSoon({ title, description }: { title: string; description: string }) {
  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-3xl font-semibold tracking-tight">{title}</h1>
      <Card>
        <CardHeader>
          <CardTitle>Coming soon</CardTitle>
          <CardDescription>{description}</CardDescription>
        </CardHeader>
      </Card>
    </div>
  );
}
