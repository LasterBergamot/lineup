import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ApiError } from "@/api/errors";
import { QueryBoundary } from "@/components/query-boundary";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";

const base = { data: undefined, isPending: false, isError: false, error: null, refetch: vi.fn() };

describe("QueryBoundary", () => {
  it("shows the skeleton while loading, announced as busy", () => {
    render(
      <QueryBoundary
        query={{ ...base, isPending: true }}
        skeleton={<Skeleton className="h-4 w-20" />}
      >
        {() => <p>content</p>}
      </QueryBoundary>,
    );
    expect(screen.getByRole("status", { name: "Loading" })).toHaveAttribute("aria-busy", "true");
    expect(screen.queryByText("content")).not.toBeInTheDocument();
  });

  it("renders the content once the data is there", () => {
    render(
      <QueryBoundary query={{ ...base, data: ["a", "b"] }} skeleton={null}>
        {(items) => <p>{items.join(",")}</p>}
      </QueryBoundary>,
    );
    expect(screen.getByText("a,b")).toBeInTheDocument();
  });

  it("shows a friendly message and a retry button on failure", async () => {
    const refetch = vi.fn();
    render(
      <QueryBoundary
        query={{ ...base, isError: true, error: new ApiError(504), refetch }}
        skeleton={null}
      >
        {() => <p>content</p>}
      </QueryBoundary>,
    );
    expect(screen.getByRole("alert")).toHaveTextContent(/took too long/i);
    await userEvent.click(screen.getByRole("button", { name: "Try again" }));
    expect(refetch).toHaveBeenCalledOnce();
  });
});

describe("Button loading", () => {
  it("disables the button and marks it busy while a request runs, so it can't be double-submitted", async () => {
    const onClick = vi.fn();
    render(
      <Button loading onClick={onClick}>
        Save
      </Button>,
    );
    const button = screen.getByRole("button", { name: "Save" });
    expect(button).toBeDisabled();
    expect(button).toHaveAttribute("aria-busy", "true");
    await userEvent.click(button);
    expect(onClick).not.toHaveBeenCalled();
  });

  it("is a normal button when not loading", () => {
    render(<Button>Save</Button>);
    expect(screen.getByRole("button", { name: "Save" })).toBeEnabled();
    expect(screen.getByRole("button", { name: "Save" })).not.toHaveAttribute("aria-busy");
  });
});
