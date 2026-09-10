#!/usr/bin/env python3
"""Rebuild MANUSCRIPT_DRAFT.md from sections/. Edit the section files, not the assembled draft.

Sections are concatenated in filename order with their YAML front matter stripped.
00_title.md is special: its title becomes the H1 and only its **key**: value lines are kept
(the alternative-framing notes stay in the section file).
"""
import datetime
import pathlib
import re

HERE = pathlib.Path(__file__).resolve().parent
SEC = HERE / "sections"
FRONT_MATTER = re.compile(r"\A---\n.*?\n---\n\s*", re.S)


def body(path):
    return FRONT_MATTER.sub("", path.read_text()).strip() + "\n"


title_lines = body(SEC / "00_title.md").splitlines()
title = next(l for l in title_lines[1:] if l.strip() and not l.startswith("#"))
meta = [l for l in title_lines if l.startswith("**")]

out = [f"# {title}", ""] + meta + [
    "",
    f"<!-- Assembled {datetime.date.today()} from sections/ by assemble.py. Edit the section files, not this one. -->",
    "",
    "---",
    "",
]
for path in sorted(SEC.glob("[0-9][0-9]_*.md")):
    if path.name.startswith("00_"):
        continue
    out += [body(path), "---", ""]
out = out[:-2]  # drop the trailing separator
text = "\n".join(out).rstrip() + "\n"
(HERE / "MANUSCRIPT_DRAFT.md").write_text(text)
print(f"MANUSCRIPT_DRAFT.md rebuilt ({len(text.split())} words, {len(text.encode())} bytes)")
