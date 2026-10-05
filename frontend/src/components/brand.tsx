/** The logo and name, shared by the app shell and the sign-in page. */
export function Brand() {
  return (
    <div className="flex items-center gap-2 text-lg font-semibold tracking-tight">
      <img src="/favicon.svg" alt="" className="size-6" />
      Lineup
    </div>
  );
}
