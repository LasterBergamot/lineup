#!/usr/bin/env python3
"""Mirror documentation/*.md into a checkout of the GitHub wiki (used by wiki-sync.yml).

The wiki page for a file is named after the file's first `# Heading`, with spaces turned into
hyphens (`# Current State: Backend` -> `Current-State:-Backend.md`), which is exactly how a
`[[Current State: Backend]]` link finds it. `Home.md` is the one exception: GitHub's wiki
landing page must be called `Home`, and its title is a sentence. So a new page needs no edit
to the workflow: give it a heading and link it from Home.md.

The mirror is exact: a wiki page with no source file is deleted (so a rename or removal in
`documentation/` shows up in the wiki). Files starting with `_` (`_Sidebar.md`, `_Footer.md`)
are the wiki's own chrome and are left alone. Stdlib only.

    python scripts/sync_wiki.py documentation wiki          # copy and prune
    python scripts/sync_wiki.py documentation --list        # print "source -> wiki page" lines
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path

HOME = "Home.md"
_H1 = re.compile(r"^# +(\S.*?) *$", re.MULTILINE)


def wiki_name(source: Path) -> str:
    """Wiki file name for a documentation page: `Home.md`, else its H1 with hyphens.

    Raises ValueError for a page without an H1, because a page silently published under a guessed
    name would break every `[[link]]` to it.
    """
    if source.name == HOME:
        return HOME
    match = _H1.search(source.read_text())
    if match is None:
        raise ValueError(f"{source}: no '# Title' heading to name the wiki page after")
    return re.sub(r"\s+", "-", match.group(1)) + ".md"


def page_map(docs: Path) -> dict[Path, str]:
    """Every documentation page mapped to its wiki file name.

    Raises ValueError when two pages would get the same name (one would overwrite the other).
    """
    pages = {source: wiki_name(source) for source in sorted(docs.glob("*.md"))}
    seen: dict[str, Path] = {}
    for source, name in pages.items():
        if name in seen:
            raise ValueError(f"{source} and {seen[name]} would both become the wiki page {name}")
        seen[name] = source
    return pages


def sync(docs: Path, wiki: Path) -> tuple[list[str], list[str]]:
    """Copy the pages into `wiki` and delete wiki pages that no longer have a source.

    Returns (written, deleted) wiki file names.
    """
    pages = page_map(docs)
    written = []
    for source, name in pages.items():
        shutil.copyfile(source, wiki / name)
        written.append(name)
    deleted = []
    for existing in sorted(wiki.glob("*.md")):
        if existing.name not in pages.values() and not existing.name.startswith("_"):
            existing.unlink()
            deleted.append(existing.name)
    return written, deleted


def main(argv: list[str] | None = None) -> int:
    """Command-line entry point; returns the process exit code."""
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("docs", type=Path, help="the documentation/ folder")
    parser.add_argument("wiki", type=Path, nargs="?", help="a checkout of the wiki repository")
    parser.add_argument("--list", action="store_true", help="only print the mapping")
    args = parser.parse_args(argv)

    try:
        if args.list:
            for source, name in page_map(args.docs).items():
                print(f"{source.name} -> {name}")
            return 0
        if args.wiki is None:
            parser.error("the wiki folder is required unless --list is given")
        written, deleted = sync(args.docs, args.wiki)
    except ValueError as error:
        print(f"::error::{error}", file=sys.stderr)
        return 1
    print(f"Wrote {len(written)} wiki pages.")
    for name in deleted:
        print(f"Deleted {name} (no source in {args.docs}).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
