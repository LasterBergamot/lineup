import { inviteCodeFromInput, inviteLinkSchema } from "@/features/invitations/code";

describe("inviteCodeFromInput", () => {
  const code = "aB3_-xYz9QwErTy0123456789abcdefghijklmnopqr";

  it.each([
    [`https://lineup-kfi.pages.dev/join/${code}`, code],
    [`  https://elsewhere.example/join/${code}?utm=1#top  `, code],
    [`/join/${code}`, code],
    [code, code],
  ])("finds the code in %s", (input, expected) => {
    expect(inviteCodeFromInput(input)).toBe(expected);
  });

  it.each(["", "   ", "hello world", "https://example.com/other/path", "a/b", "<script>", "é"])(
    "rejects %j",
    (input) => {
      expect(inviteCodeFromInput(input)).toBeNull();
    },
  );

  it("rejects a code longer than the API accepts", () => {
    expect(inviteCodeFromInput("a".repeat(201))).toBeNull();
    expect(inviteCodeFromInput("a".repeat(200))).toBe("a".repeat(200));
  });
});

describe("inviteLinkSchema", () => {
  it("accepts a link and flags a blank or odd value with a translatable key", () => {
    expect(inviteLinkSchema.safeParse({ link: " /join/abc " }).success).toBe(true);
    const blank = inviteLinkSchema.safeParse({ link: " " });
    expect(blank.error?.issues[0]?.message).toContain("validation.required");
    const odd = inviteLinkSchema.safeParse({ link: "not a link" });
    expect(odd.error?.issues[0]?.message).toContain("validation.inviteLink");
  });
});
