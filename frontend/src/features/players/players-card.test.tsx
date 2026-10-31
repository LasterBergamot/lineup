import { QueryClientProvider } from "@tanstack/react-query";
import { act, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ApiError } from "@/api/errors";
import { useAuth } from "@/auth/context";
import { AuthProvider } from "@/auth/provider";
import type { Player } from "@/features/players/api";
import { PlayersCard } from "@/features/players/players-card";
import type { Team } from "@/features/teams/api";
import { i18n } from "@/i18n";
import { fakeAuthClient, fakeSession, teamsPage, testQueryClient } from "@/test/auth";

const mocks = vi.hoisted(() => ({
  listPlayers: vi.fn(),
  createPlayer: vi.fn(),
  updatePlayer: vi.fn(),
  deletePlayer: vi.fn(),
}));
vi.mock("@/features/players/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/features/players/api")>()),
  ...mocks,
}));

const TEAM = "00000000-0000-4000-8000-000000000001";
const ANN: Player = {
  id: "p-ann",
  team_id: TEAM,
  name: "Kovács Anna",
  nssz_number: "MVLSZ1",
  created_at: "2026-10-05T10:00:00",
};
const BEN: Player = { ...ANN, id: "p-ben", name: "Nagy Bence", nssz_number: "MVLSZ2" };

/** A 422 as FastAPI sends it, pointing at one body field. */
function rejected(field: string, msg: string) {
  return new ApiError(422, { detail: [{ loc: ["body", field], msg, type: "value_error" }] });
}

/** Renders the card once the fake session is in, as `RequireAuth` does in the app. */
function SignedIn({ team }: { team: Team }) {
  return useAuth().status === "signed-in" ? <PlayersCard team={team} /> : null;
}

function renderCard(role: "owner" | "member" = "member") {
  const team = { ...teamsPage("SZVTK").items[0]!, role } as Team;
  const queryClient = testQueryClient();
  render(
    <QueryClientProvider client={queryClient}>
      <AuthProvider client={fakeAuthClient(fakeSession()).client}>
        <SignedIn team={team} />
      </AuthProvider>
    </QueryClientProvider>,
  );
  return { queryClient };
}

const addForm = () => screen.getByRole("form", { name: "Add a player" });

async function fill(form: HTMLElement, name: string, nssz: string) {
  const nameInput = within(form).getByLabelText("Name");
  const nsszInput = within(form).getByLabelText("NSSZ number");
  await userEvent.clear(nameInput);
  if (name) await userEvent.type(nameInput, name);
  await userEvent.clear(nsszInput);
  if (nssz) await userEvent.type(nsszInput, nssz);
}

beforeEach(() => {
  for (const mock of Object.values(mocks)) mock.mockReset();
  mocks.listPlayers.mockResolvedValue([ANN, BEN]);
  mocks.deletePlayer.mockResolvedValue(undefined);
});

describe("players card", () => {
  it("shows a skeleton, then the roster in the API's order", async () => {
    let resolve!: (players: Player[]) => void;
    mocks.listPlayers.mockReturnValue(new Promise((r) => (resolve = r)));
    renderCard();
    expect(await screen.findByRole("status", { name: "Loading" })).toBeInTheDocument();
    await act(async () => resolve([BEN, ANN]));
    const list = await screen.findByRole("list", { name: "Players of SZVTK" });
    const rows = within(list).getAllByRole("listitem");
    expect(rows.map((row) => row.textContent)).toEqual([
      expect.stringContaining("Nagy Bence"),
      expect.stringContaining("Kovács Anna"),
    ]);
    expect(within(rows[0]!).getByText("NSSZ number: MVLSZ2")).toBeInTheDocument();
    expect(mocks.listPlayers).toHaveBeenCalledWith(TEAM);
    expect(screen.getByText(/does not change lineups you have already saved/)).toBeInTheDocument();
  });

  it("says when the roster is empty", async () => {
    mocks.listPlayers.mockResolvedValue([]);
    renderCard();
    expect(await screen.findByText("No players yet. Add the first one above.")).toBeInTheDocument();
    expect(screen.queryByRole("list")).not.toBeInTheDocument();
  });

  it("offers a retry when the roster cannot be loaded", async () => {
    mocks.listPlayers.mockRejectedValueOnce(new ApiError(503));
    renderCard();
    expect(await screen.findByText(/busy or starting up/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Try again" }));
    expect(await screen.findByText("Kovács Anna")).toBeInTheDocument();
  });

  it("lets a plain member do everything (no role gate)", async () => {
    renderCard("member");
    await screen.findByText("Kovács Anna");
    expect(screen.getByRole("button", { name: "Add player" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Edit Kovács Anna" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Delete Kovács Anna" })).toBeInTheDocument();
  });

  it("speaks Hungarian", async () => {
    renderCard();
    await screen.findByText("Kovács Anna");
    await act(async () => {
      await i18n.changeLanguage("hu");
    });
    expect(screen.getByRole("heading", { name: "Játékosok" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Kovács Anna törlése" })).toBeInTheDocument();
    expect(screen.getByText("NSSZ-szám: MVLSZ1")).toBeInTheDocument();
  });
});

describe("adding", () => {
  it("adds a trimmed player, empties the form and reloads the roster", async () => {
    mocks.createPlayer.mockResolvedValue({ ...ANN, id: "p-new" });
    renderCard();
    await screen.findByText("Kovács Anna");
    await fill(addForm(), "  Kiss Csaba ", "MVLSZ3");
    await userEvent.click(screen.getByRole("button", { name: "Add player" }));
    expect(mocks.createPlayer).toHaveBeenCalledWith(TEAM, {
      name: "Kiss Csaba",
      nsszNumber: "MVLSZ3",
    });
    await waitFor(() => expect(mocks.listPlayers).toHaveBeenCalledTimes(2));
    expect(within(addForm()).getByLabelText("Name")).toHaveValue("");
    expect(within(addForm()).getByLabelText("NSSZ number")).toHaveValue("");
  });

  it("checks the fields before sending anything", async () => {
    renderCard();
    await screen.findByText("Kovács Anna");
    await userEvent.click(screen.getByRole("button", { name: "Add player" }));
    expect(await within(addForm()).findByText("Name is required")).toBeInTheDocument();
    expect(within(addForm()).getByText("NSSZ number is required")).toBeInTheDocument();
    expect(mocks.createPlayer).not.toHaveBeenCalled();
  });

  it("shows a server 422 on the field it names and keeps the input", async () => {
    mocks.createPlayer.mockRejectedValue(rejected("nssz_number", "Value error, too odd"));
    renderCard();
    await screen.findByText("Kovács Anna");
    await fill(addForm(), "Kiss Csaba", "MVLSZ3");
    await userEvent.click(screen.getByRole("button", { name: "Add player" }));
    const nssz = within(addForm()).getByLabelText("NSSZ number");
    expect(await within(addForm()).findByText("too odd")).toBeInTheDocument();
    expect(nssz).toHaveAttribute("aria-invalid", "true");
    expect(nssz).toHaveValue("MVLSZ3");
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("maps a 422 on the name too", async () => {
    mocks.createPlayer.mockRejectedValue(rejected("name", "bad name"));
    renderCard();
    await screen.findByText("Kovács Anna");
    await fill(addForm(), "Kiss Csaba", "MVLSZ3");
    await userEvent.click(screen.getByRole("button", { name: "Add player" }));
    expect(await within(addForm()).findByText("bad name")).toBeInTheDocument();
    expect(within(addForm()).getByLabelText("Name")).toHaveAttribute("aria-invalid", "true");
  });

  it("explains a 422 on another field in general words", async () => {
    mocks.createPlayer.mockRejectedValue(rejected("team_id", "bad team"));
    renderCard();
    await screen.findByText("Kovács Anna");
    await fill(addForm(), "Kiss Csaba", "MVLSZ3");
    await userEvent.click(screen.getByRole("button", { name: "Add player" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("were rejected");
    expect(screen.queryByText("bad team")).not.toBeInTheDocument();
  });

  it.each([
    [404, "no longer exists"],
    [403, "don't have permission"],
    [500, "went wrong on our side"],
  ])("explains a %i in plain words", async (status, text) => {
    mocks.createPlayer.mockRejectedValue(new ApiError(status, { detail: "server text" }));
    renderCard();
    await screen.findByText("Kovács Anna");
    await fill(addForm(), "Kiss Csaba", "MVLSZ3");
    await userEvent.click(screen.getByRole("button", { name: "Add player" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(text);
    expect(screen.queryByText("server text")).not.toBeInTheDocument();
  });
});

describe("editing", () => {
  it("edits a row in place and reloads the roster", async () => {
    mocks.updatePlayer.mockResolvedValue({ ...ANN, name: "Kovács Anikó" });
    renderCard();
    await userEvent.click(await screen.findByRole("button", { name: "Edit Kovács Anna" }));
    const form = screen.getByRole("form", { name: "Edit Kovács Anna" });
    expect(within(form).getByLabelText("Name")).toHaveValue("Kovács Anna");
    expect(within(form).getByLabelText("NSSZ number")).toHaveValue("MVLSZ1");
    await fill(form, "Kovács Anikó", "MVLSZ9");
    await userEvent.click(within(form).getByRole("button", { name: "Save" }));
    expect(mocks.updatePlayer).toHaveBeenCalledWith(ANN, {
      name: "Kovács Anikó",
      nsszNumber: "MVLSZ9",
    });
    await waitFor(() =>
      expect(screen.queryByRole("form", { name: "Edit Kovács Anna" })).not.toBeInTheDocument(),
    );
    await waitFor(() => expect(mocks.listPlayers).toHaveBeenCalledTimes(2));
  });

  it("cancels without saving", async () => {
    renderCard();
    await userEvent.click(await screen.findByRole("button", { name: "Edit Nagy Bence" }));
    const form = screen.getByRole("form", { name: "Edit Nagy Bence" });
    await fill(form, "Changed", "X");
    await userEvent.click(within(form).getByRole("button", { name: "Cancel" }));
    expect(screen.queryByRole("form", { name: "Edit Nagy Bence" })).not.toBeInTheDocument();
    expect(screen.getByText("Nagy Bence")).toBeInTheDocument();
    expect(mocks.updatePlayer).not.toHaveBeenCalled();
  });

  it("validates the edit form", async () => {
    renderCard();
    await userEvent.click(await screen.findByRole("button", { name: "Edit Nagy Bence" }));
    const form = screen.getByRole("form", { name: "Edit Nagy Bence" });
    await fill(form, "", "MVLSZ2");
    await userEvent.click(within(form).getByRole("button", { name: "Save" }));
    expect(await within(form).findByText("Name is required")).toBeInTheDocument();
    expect(mocks.updatePlayer).not.toHaveBeenCalled();
  });

  it("keeps the form open with the server's 422 on the field", async () => {
    mocks.updatePlayer.mockRejectedValue(rejected("name", "bad name"));
    renderCard();
    await userEvent.click(await screen.findByRole("button", { name: "Edit Nagy Bence" }));
    const form = screen.getByRole("form", { name: "Edit Nagy Bence" });
    await userEvent.click(within(form).getByRole("button", { name: "Save" }));
    expect(await within(form).findByText("bad name")).toBeInTheDocument();
  });

  it("says when the player was deleted meanwhile and reloads the roster", async () => {
    mocks.updatePlayer.mockRejectedValue(new ApiError(404));
    renderCard();
    await userEvent.click(await screen.findByRole("button", { name: "Edit Nagy Bence" }));
    const form = screen.getByRole("form", { name: "Edit Nagy Bence" });
    await userEvent.click(within(form).getByRole("button", { name: "Save" }));
    expect(await within(form).findByRole("alert")).toHaveTextContent("no longer exists");
    await waitFor(() => expect(mocks.listPlayers).toHaveBeenCalledTimes(2));
  });
});

describe("deleting", () => {
  it("deletes only after confirming, then reloads the roster", async () => {
    renderCard();
    await userEvent.click(await screen.findByRole("button", { name: "Delete Nagy Bence" }));
    expect(mocks.deletePlayer).not.toHaveBeenCalled();
    await userEvent.click(screen.getByRole("button", { name: "Yes, delete" }));
    expect(mocks.deletePlayer).toHaveBeenCalledWith("p-ben");
    await waitFor(() => expect(mocks.listPlayers).toHaveBeenCalledTimes(2));
  });

  it("can be called off", async () => {
    renderCard();
    await userEvent.click(await screen.findByRole("button", { name: "Delete Nagy Bence" }));
    await userEvent.click(screen.getByRole("button", { name: "Cancel" }));
    expect(screen.getByRole("button", { name: "Delete Nagy Bence" })).toBeInTheDocument();
    expect(mocks.deletePlayer).not.toHaveBeenCalled();
  });

  it.each([
    [403, "don't have permission"],
    [404, "no longer exists"],
    [0, "Can't reach the server"],
  ])("explains a failed delete (%i) and reloads the roster", async (status, text) => {
    mocks.deletePlayer.mockRejectedValue(new ApiError(status));
    renderCard();
    await userEvent.click(await screen.findByRole("button", { name: "Delete Nagy Bence" }));
    await userEvent.click(screen.getByRole("button", { name: "Yes, delete" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(text);
    expect(mocks.listPlayers).toHaveBeenCalledTimes(2);
  });
});

describe("privacy", () => {
  it("stores nothing in the browser and keeps names out of the query key", async () => {
    mocks.createPlayer.mockResolvedValue(ANN);
    const { queryClient } = renderCard();
    await screen.findByText("Kovács Anna");
    await fill(addForm(), "Kiss Csaba", "MVLSZ3");
    await userEvent.click(screen.getByRole("button", { name: "Add player" }));
    await waitFor(() => expect(mocks.createPlayer).toHaveBeenCalled());
    expect(localStorage.length).toBe(0);
    expect(sessionStorage.length).toBe(0);
    const keys = JSON.stringify(
      queryClient
        .getQueryCache()
        .getAll()
        .map((q) => q.queryKey),
    );
    expect(keys).not.toMatch(/Kiss|Kovács|MVLSZ/);
  });
});
