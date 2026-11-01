import { render, screen } from "@testing-library/react";
import { Badge } from "@/components/ui/badge";

describe("Badge", () => {
  it("is a neutral pill by default", () => {
    render(<Badge>Member</Badge>);
    expect(screen.getByText("Member")).toHaveClass("rounded-pill", "bg-muted");
  });

  it("takes its colours from the variant", () => {
    render(<Badge variant="success">Saved</Badge>);
    expect(screen.getByText("Saved")).toHaveClass(
      "bg-success-soft",
      "text-success-soft-foreground",
    );
  });

  it("hides the icon from screen readers, so the word is the name", () => {
    render(
      <Badge variant="danger" icon={<svg data-testid="icon" />}>
        Failed
      </Badge>,
    );
    expect(screen.getByTestId("icon").parentElement).toHaveAttribute("aria-hidden", "true");
    expect(screen.getByText("Failed")).toBeInTheDocument();
  });
});
