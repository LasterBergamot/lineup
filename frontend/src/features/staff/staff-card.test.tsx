import { QueryClientProvider } from "@tanstack/react-query";
import { act, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { ApiError } from "@/api/errors";
import { useAuth } from "@/auth/context";
import { AuthProvider } from "@/auth/provider";
import type { Player } from "@/features/players/api";
import type { Staff } from "@/features/staff/api";
import { StaffCard } from "@/features/staff/staff-card";
import type { Team } from "@/features/teams/api";
import { i18n } from "@/i18n";
import { fakeAuthClient, fakeSession, teamsPage, testQueryClient } from "@/test/auth";
import { unsavedProbe } from "@/test/unsaved";

const mocks = vi.hoisted(() => ({
  listStaff: vi.fn(),
  createStaff: vi.fn(),
  updateStaff: vi.fn(),
  deleteStaff: vi.fn(),
  listPlayers: vi.fn(),
}));
vi.mock("@/features/staff/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/features/staff/api")>()),
  listStaff: mocks.listStaff,
  createStaff: mocks.createStaff,
  updateStaff: mocks.updateStaff,
  deleteStaff: mocks.deleteStaff,
}));
vi.mock("@/features/players/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/features/players/api")>()),
  listPlayers: mocks.listPlayers,
}));

const TEAM = "00000000-0000-4000-8000-000000000001";
const BELA: Player = {
  id: "p-bela",
  team_id: TEAM,
  name: "Kovács Béla",
  nssz_number: "MVLSZ1",
  created_at: "2026-10-05T10:00:00",
};

function entry(name: string, role: Staff["role"], extra: Partial<Staff> = {}): Staff {
  return {
    id: `st-${name}`,
    team_id: TEAM,
    role,
    name,
    source_player_id: null,
    is_default: false,
    created_at: "2026-11-01T10:00:00",
    ...extra,
  };
}

const EDE = entry("Edző Ede", "coach", { is_default: true });
const ADAM = entry("Ács Ádám", "coach");
const LEADER = entry("Kovács Béla", "team_leader", { source_player_id: BELA.id });

/** A 422 as FastAPI sends it, pointing at one body field. */
function rejected(field: string, msg: string) {
  return new ApiError(422, { detail: [{ loc: ["body", field], msg, type: "value_error" }] });
}

function SignedIn({ team }: { team: Team }) {
  return useAuth().status === "signed-in" ? <StaffCard team={team} /> : null;
}

function renderCard(
  Wrapper: (props: { children: ReactNode }) => ReactNode = ({ children }) => children,
) {
  const team = { ...teamsPage("SZVTK").items[0]!, role: "member" } as Team;
  render(
    <QueryClientProvider client={testQueryClient()}>
      <AuthProvider client={fakeAuthClient(fakeSession()).client}>
        <Wrapper>
          <SignedIn team={team} />
        </Wrapper>
      </AuthProvider>
    </QueryClientProvider>,
  );
}

const addForm = () => screen.getByRole("form", { name: "Add a staff member" });
const group = (name: string) => screen.getByRole("region", { name });

beforeEach(() => {
  for (const mock of Object.values(mocks)) mock.mockReset();
  mocks.listStaff.mockResolvedValue([ADAM, EDE, LEADER]);
  mocks.listPlayers.mockResolvedValue([BELA]);
  mocks.deleteStaff.mockResolvedValue(undefined);
});

describe("staff card", () => {
  it("lists the entries by role, the default first and marked", async () => {
    renderCard();
    expect(await screen.findByRole("status", { name: "Loading" })).toBeInTheDocument();
    await screen.findByRole("region", { name: "Coach" });
    const coaches = within(group("Coach")).getAllByRole("listitem");
    expect(coaches.map((row) => row.textContent)).toEqual([
      expect.stringContaining("Edző Ede"),
      expect.stringContaining("Ács Ádám"),
    ]);
    expect(within(coaches[0]!).getByText("Default")).toBeInTheDocument();
    expect(
      within(coaches[0]!).queryByRole("button", { name: /^Make default/ }),
    ).not.toBeInTheDocument();
    expect(within(group("Team leader")).getByText("Kovács Béla")).toBeInTheDocument();
    // Roles without entries get no group.
    expect(screen.queryByRole("region", { name: "Ball thrower" })).not.toBeInTheDocument();
    expect(mocks.listStaff).toHaveBeenCalledWith(TEAM);
    expect(screen.getByText(/does not change lineups you have already saved/)).toBeInTheDocument();
  });

  it("says when there is no staff yet", async () => {
    mocks.listStaff.mockResolvedValue([]);
    renderCard();
    expect(await screen.findByText("No staff yet. Add the first one above.")).toBeInTheDocument();
  });

  it("offers a retry when the staff cannot be loaded", async () => {
    mocks.listStaff.mockRejectedValueOnce(new ApiError(503));
    renderCard();
    expect(await screen.findByText(/busy or starting up/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Try again" }));
    expect(await screen.findByRole("region", { name: "Coach" })).toBeInTheDocument();
  });

  it("still lets a name be typed in when the roster cannot be loaded", async () => {
    mocks.listPlayers.mockRejectedValue(new ApiError(503));
    mocks.createStaff.mockResolvedValue(EDE);
    renderCard();
    await screen.findByRole("region", { name: "Coach" });
    await userEvent.type(within(addForm()).getByLabelText("Name"), "Új Edző");
    await userEvent.click(screen.getByRole("button", { name: "Add staff member" }));
    expect(mocks.createStaff).toHaveBeenCalledWith(TEAM, {
      role: "coach",
      playerId: "",
      name: "Új Edző",
      isDefault: false,
    });
  });

  it("speaks Hungarian", async () => {
    renderCard();
    await screen.findByRole("region", { name: "Coach" });
    await act(async () => {
      await i18n.changeLanguage("hu");
    });
    expect(screen.getByRole("heading", { name: "Stáb" })).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "Csapatvezető" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Törlés: Ács Ádám (Edző)" })).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Legyen alapértelmezett: Ács Ádám (Edző)" }),
    ).toBeInTheDocument();
    await act(async () => {
      await i18n.changeLanguage("en");
    });
  });
});

describe("adding", () => {
  it("adds a typed-in default, keeps the role for the next one and reloads the list", async () => {
    mocks.createStaff.mockResolvedValue(EDE);
    renderCard();
    await screen.findByRole("region", { name: "Coach" });
    const form = addForm();
    await userEvent.selectOptions(within(form).getByLabelText("Role"), "Ball thrower");
    await userEvent.type(within(form).getByLabelText("Name"), "  Dobó Dóra ");
    await userEvent.click(within(form).getByLabelText("Default for this role"));
    await userEvent.click(screen.getByRole("button", { name: "Add staff member" }));
    expect(mocks.createStaff).toHaveBeenCalledWith(TEAM, {
      role: "ball_thrower",
      playerId: "",
      name: "Dobó Dóra",
      isDefault: true,
    });
    await waitFor(() => expect(mocks.listStaff).toHaveBeenCalledTimes(2));
    expect(within(form).getByLabelText("Name")).toHaveValue("");
    expect(within(form).getByLabelText("Default for this role")).not.toBeChecked();
    expect(within(form).getByLabelText("Role")).toHaveValue("ball_thrower");
  });

  it("copies a picked roster player's name and sends the player's id", async () => {
    mocks.createStaff.mockResolvedValue(LEADER);
    const user = userEvent.setup();
    renderCard();
    await screen.findByRole("region", { name: "Coach" });
    const form = addForm();
    await user.selectOptions(within(form).getByLabelText("Role"), "Team leader");
    await user.click(within(form).getByRole("combobox", { name: "Player from the roster" }));
    await user.click(within(form).getByRole("option", { name: /Kovács Béla/ }));
    const name = within(form).getByLabelText("Name");
    expect(name).toHaveValue("Kovács Béla");
    expect(name).toHaveAttribute("readonly");
    await user.click(screen.getByRole("button", { name: "Add staff member" }));
    expect(mocks.createStaff).toHaveBeenCalledWith(TEAM, {
      role: "team_leader",
      playerId: BELA.id,
      name: "Kovács Béla",
      isDefault: false,
    });
  });

  it("frees the name again for 'Type in by hand' and keeps what was copied", async () => {
    const user = userEvent.setup();
    renderCard();
    await screen.findByRole("region", { name: "Coach" });
    const form = addForm();
    const picker = within(form).getByRole("combobox", { name: "Player from the roster" });
    await user.click(picker);
    await user.click(within(form).getByRole("option", { name: /Kovács Béla/ }));
    await user.click(picker);
    await user.click(within(form).getByRole("option", { name: "Type in by hand" }));
    const name = within(form).getByLabelText("Name");
    expect(name).not.toHaveAttribute("readonly");
    expect(name).toHaveValue("Kovács Béla");
  });

  it("checks the name before sending anything", async () => {
    renderCard();
    await screen.findByRole("region", { name: "Coach" });
    await userEvent.click(screen.getByRole("button", { name: "Add staff member" }));
    expect(await within(addForm()).findByText("Name is required")).toBeInTheDocument();
    expect(mocks.createStaff).not.toHaveBeenCalled();
  });

  it("shows a server 422 on the field it names", async () => {
    mocks.createStaff.mockRejectedValue(rejected("name", "too odd"));
    renderCard();
    await screen.findByRole("region", { name: "Coach" });
    await userEvent.type(within(addForm()).getByLabelText("Name"), "Edző Ede");
    await userEvent.click(screen.getByRole("button", { name: "Add staff member" }));
    expect(await within(addForm()).findByText("too odd")).toBeInTheDocument();
    expect(within(addForm()).getByLabelText("Name")).toHaveAttribute("aria-invalid", "true");
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("explains a 422 on another field and a 404 in general words, and reloads", async () => {
    mocks.createStaff
      .mockRejectedValueOnce(rejected("team_id", "bad team"))
      .mockRejectedValueOnce(new ApiError(404));
    renderCard();
    await screen.findByRole("region", { name: "Coach" });
    await userEvent.type(within(addForm()).getByLabelText("Name"), "Edző Ede");
    await userEvent.click(screen.getByRole("button", { name: "Add staff member" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("were rejected");
    await userEvent.click(screen.getByRole("button", { name: "Add staff member" }));
    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent("no longer exists"));
    expect(mocks.listStaff).toHaveBeenCalledTimes(3);
  });

  it("explains a 409 (a default set by someone else at the same moment)", async () => {
    mocks.createStaff.mockRejectedValue(new ApiError(409));
    renderCard();
    await screen.findByRole("region", { name: "Coach" });
    await userEvent.type(within(addForm()).getByLabelText("Name"), "Edző Ede");
    await userEvent.click(screen.getByRole("button", { name: "Add staff member" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(/changed this role's default/);
  });

  it("keeps staff names in memory only", async () => {
    mocks.createStaff.mockResolvedValue(EDE);
    renderCard();
    await screen.findByRole("region", { name: "Coach" });
    await userEvent.type(within(addForm()).getByLabelText("Name"), "Edző Ede");
    await userEvent.click(screen.getByRole("button", { name: "Add staff member" }));
    await waitFor(() => expect(mocks.createStaff).toHaveBeenCalled());
    expect(localStorage.length).toBe(0);
    expect(sessionStorage.length).toBe(0);
  });

  it("reports typed-in input to the unsaved-changes guard", async () => {
    const probe = unsavedProbe();
    renderCard(probe.Wrapper);
    await screen.findByRole("region", { name: "Coach" });
    expect(probe.isDirty()).toBe(false);
    await userEvent.type(within(addForm()).getByLabelText("Name"), "E");
    expect(probe.isDirty()).toBe(true);
  });
});

describe("editing", () => {
  it("edits an entry in place, sending every field, and closes the form", async () => {
    mocks.updateStaff.mockResolvedValue(ADAM);
    renderCard();
    await screen.findByRole("region", { name: "Coach" });
    await userEvent.click(screen.getByRole("button", { name: "Edit Ács Ádám (Coach)" }));
    const form = screen.getByRole("form", { name: "Edit Ács Ádám (Coach)" });
    expect(within(form).getByLabelText("Role")).toHaveValue("coach");
    expect(within(form).getByLabelText("Default for this role")).not.toBeChecked();
    await userEvent.selectOptions(within(form).getByLabelText("Role"), "Assistant coach");
    await userEvent.clear(within(form).getByLabelText("Name"));
    await userEvent.type(within(form).getByLabelText("Name"), "Ács Ádám Jr.");
    await userEvent.click(within(form).getByRole("button", { name: "Save" }));
    expect(mocks.updateStaff).toHaveBeenCalledWith(ADAM, {
      role: "assistant_coach",
      playerId: "",
      name: "Ács Ádám Jr.",
      isDefault: false,
    });
    await waitFor(() =>
      expect(screen.queryByRole("form", { name: "Edit Ács Ádám (Coach)" })).not.toBeInTheDocument(),
    );
    expect(mocks.listStaff).toHaveBeenCalledTimes(2);
  });

  it("starts from the roster player an entry was picked from, while they are on the roster", async () => {
    renderCard();
    await screen.findByRole("region", { name: "Coach" });
    await userEvent.click(screen.getByRole("button", { name: "Edit Kovács Béla (Team leader)" }));
    const form = screen.getByRole("form", { name: "Edit Kovács Béla (Team leader)" });
    expect(within(form).getByRole("combobox", { name: "Player from the roster" })).toHaveValue(
      "Kovács Béla",
    );
    expect(within(form).getByLabelText("Name")).toHaveAttribute("readonly");
    await userEvent.click(within(form).getByRole("button", { name: "Cancel" }));
    expect(
      screen.queryByRole("form", { name: "Edit Kovács Béla (Team leader)" }),
    ).not.toBeInTheDocument();
  });

  it("treats an entry whose player has left the roster as typed in", async () => {
    mocks.listPlayers.mockResolvedValue([]);
    renderCard();
    await screen.findByRole("region", { name: "Coach" });
    await userEvent.click(screen.getByRole("button", { name: "Edit Kovács Béla (Team leader)" }));
    const form = screen.getByRole("form", { name: "Edit Kovács Béla (Team leader)" });
    expect(within(form).getByRole("combobox", { name: "Player from the roster" })).toHaveValue("");
    expect(within(form).getByLabelText("Name")).not.toHaveAttribute("readonly");
  });
});

describe("default and delete", () => {
  it("makes an entry its role's default, keeping its other fields", async () => {
    mocks.updateStaff.mockResolvedValue({ ...ADAM, is_default: true });
    renderCard();
    await screen.findByRole("region", { name: "Coach" });
    mocks.listStaff.mockResolvedValue([
      { ...ADAM, is_default: true },
      { ...EDE, is_default: false },
    ]);
    await userEvent.click(screen.getByRole("button", { name: "Make default: Ács Ádám (Coach)" }));
    expect(mocks.updateStaff).toHaveBeenCalledWith(ADAM, {
      role: "coach",
      playerId: "",
      name: "Ács Ádám",
      isDefault: true,
    });
    await waitFor(() =>
      expect(within(group("Coach")).getAllByRole("listitem")[0]).toHaveTextContent("Ács Ádám"),
    );
    expect(
      screen.getByRole("button", { name: "Make default: Edző Ede (Coach)" }),
    ).toBeInTheDocument();
  });

  it("shows only the row being changed as busy", async () => {
    let finishDefault!: (entry: Staff) => void;
    let finishDelete!: () => void;
    mocks.updateStaff.mockReturnValue(new Promise((r) => (finishDefault = r)));
    mocks.deleteStaff.mockReturnValue(new Promise<void>((r) => (finishDelete = r)));
    renderCard();
    await screen.findByRole("region", { name: "Coach" });
    await userEvent.click(screen.getByRole("button", { name: "Make default: Ács Ádám (Coach)" }));
    expect(screen.getByRole("button", { name: "Make default: Ács Ádám (Coach)" })).toHaveAttribute(
      "aria-busy",
      "true",
    );
    expect(screen.getByRole("button", { name: "Delete Ács Ádám (Coach)" })).not.toHaveAttribute(
      "aria-busy",
    );
    await act(async () => finishDefault(ADAM));
    await userEvent.click(screen.getByRole("button", { name: "Delete Kovács Béla (Team leader)" }));
    await userEvent.click(screen.getByRole("button", { name: "Yes, delete" }));
    expect(screen.getByRole("button", { name: "Yes, delete" })).toHaveAttribute(
      "aria-busy",
      "true",
    );
    expect(
      screen.getByRole("button", { name: "Make default: Ács Ádám (Coach)" }),
    ).not.toHaveAttribute("aria-busy");
    await act(async () => finishDelete());
  });

  it("shows why making a default failed", async () => {
    mocks.updateStaff.mockRejectedValue(new ApiError(404));
    renderCard();
    await screen.findByRole("region", { name: "Coach" });
    await userEvent.click(screen.getByRole("button", { name: "Make default: Ács Ádám (Coach)" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("no longer exists");
  });

  it("deletes an entry after a confirmation and reloads the list", async () => {
    renderCard();
    await screen.findByRole("region", { name: "Coach" });
    await userEvent.click(screen.getByRole("button", { name: "Delete Edző Ede (Coach)" }));
    expect(mocks.deleteStaff).not.toHaveBeenCalled();
    mocks.listStaff.mockResolvedValue([ADAM, LEADER]);
    await userEvent.click(screen.getByRole("button", { name: "Yes, delete" }));
    expect(mocks.deleteStaff).toHaveBeenCalledWith(EDE);
    // Nobody is promoted: the remaining coach is not the default.
    await waitFor(() => expect(screen.queryByText("Edző Ede")).not.toBeInTheDocument());
    expect(screen.queryByText("Default")).not.toBeInTheDocument();
  });

  it("shows why a delete failed", async () => {
    mocks.deleteStaff.mockRejectedValue(new ApiError(503));
    renderCard();
    await screen.findByRole("region", { name: "Coach" });
    await userEvent.click(screen.getByRole("button", { name: "Delete Edző Ede (Coach)" }));
    await userEvent.click(screen.getByRole("button", { name: "Yes, delete" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(/busy or starting up/);
  });
});
