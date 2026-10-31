import { roleKey } from "@/features/teams/role";

describe("roleKey", () => {
  it("maps the known roles and falls back for anything else", () => {
    expect(roleKey("owner")).toBe("account.role.owner");
    expect(roleKey("member")).toBe("account.role.member");
    expect(roleKey("admin")).toBe("account.role.unknown");
  });
});
