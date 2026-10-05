try {
  var saved = localStorage.getItem("lineup-theme");
  var dark =
    saved === "dark" || (saved !== "light" && matchMedia("(prefers-color-scheme: dark)").matches);
  if (dark) document.documentElement.classList.add("dark");
} catch (e) {
  // Storage can be blocked; fall back to the default (light) theme.
}
