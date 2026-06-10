#!/usr/bin/env python3
"""
split_specifications.py
=======================

Splits the EDM Master Specification document into 11 separate, numbered
specification files based on the top-level numbered sections (H2 markers
of the form ``## 1. ...`` through ``## 11. ...``).

The master document lives at:
    docs/specifications/EDM_Master_Specification.md

The 11 sections are:
    1.  Functional Specification            -> 01_Functional_Specification.md
    2.  Domain Model                        -> 02_Domain_Model.md
    3.  Entity Definitions                  -> 03_Entity_Definitions.md
    4.  Event Specification                 -> 04_Event_Specification.md
    5.  Database Design                     -> 05_Database_Design.md
    6.  API Contracts                       -> 06_API_Contracts.md
    7.  Review Queue Specification          -> 07_Review_Queue_Specification.md
    8.  Supplier Rule Engine Specification  -> 08_Supplier_Rule_Engine_Specification.md
    9.  Parsing Strategy                    -> 09_Parsing_Strategy.md
    10. UI/UX Specification                 -> 10_UIUX_Specification.md
    11. Implementation Roadmap              -> 11_Implementation_Roadmap.md

NOTE:
    The master specification is a living document. Some numbered sections may
    not yet be fully written. This script splits whatever numbered sections it
    finds; sections that are missing from the master file are simply skipped
    (a warning is printed). Re-run the script after the master document grows
    to regenerate the per-section files.

USAGE
-----
    # Run from the repository root with default paths:
    python split_specifications.py

    # Or specify a custom input file and/or output directory:
    python split_specifications.py --input path/to/master.md --output-dir path/to/out

    # Preview what would be written without creating files:
    python split_specifications.py --dry-run

EXIT CODES
----------
    0  success (at least one section written, or dry-run)
    1  master specification file not found
    2  no numbered H2 sections detected in the master file
"""

import argparse
import re
import sys
from pathlib import Path

# Default location of the master specification, relative to this script.
DEFAULT_INPUT = Path("docs/specifications/EDM_Master_Specification.md")
DEFAULT_OUTPUT_DIR = Path("docs/specifications")

# Canonical file-name slug for each numbered section. The key is the section
# number as it appears in the document ("## <n>. <title>").
SECTION_SLUGS = {
    1: "Functional_Specification",
    2: "Domain_Model",
    3: "Entity_Definitions",
    4: "Event_Specification",
    5: "Database_Design",
    6: "API_Contracts",
    7: "Review_Queue_Specification",
    8: "Supplier_Rule_Engine_Specification",
    9: "Parsing_Strategy",
    10: "UIUX_Specification",
    11: "Implementation_Roadmap",
}

# Matches a top-level numbered section header, e.g. "## 1. Functional Specification".
SECTION_RE = re.compile(r"^##\s+(\d+)\.\s+(.+?)\s*$")


def slugify_title(title: str) -> str:
    """Build a safe filename slug from a section title (fallback helper)."""
    slug = re.sub(r"[^0-9A-Za-z]+", "_", title).strip("_")
    return slug or "Section"


def split_specification(text: str):
    """
    Parse the master document text and return a list of
    (section_number, title, body_text) tuples for each numbered H2 section.

    The body of a section spans from its own header line up to (but not
    including) the next numbered H2 header.
    """
    lines = text.splitlines(keepends=True)

    # Collect indices and metadata for every numbered section header.
    headers = []  # list of (line_index, section_number, title)
    for idx, line in enumerate(lines):
        m = SECTION_RE.match(line.rstrip("\n"))
        if m:
            headers.append((idx, int(m.group(1)), m.group(2).strip()))

    sections = []
    for i, (start_idx, number, title) in enumerate(headers):
        end_idx = headers[i + 1][0] if i + 1 < len(headers) else len(lines)
        body = "".join(lines[start_idx:end_idx]).rstrip() + "\n"
        sections.append((number, title, body))
    return sections


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Split the EDM Master Specification into numbered section files."
    )
    parser.add_argument(
        "--input", "-i", type=Path, default=DEFAULT_INPUT,
        help=f"Path to the master specification (default: {DEFAULT_INPUT})",
    )
    parser.add_argument(
        "--output-dir", "-o", type=Path, default=DEFAULT_OUTPUT_DIR,
        help=f"Directory for the split files (default: {DEFAULT_OUTPUT_DIR})",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Show what would be written without creating any files.",
    )
    args = parser.parse_args(argv)

    if not args.input.is_file():
        print(f"ERROR: master specification not found: {args.input}", file=sys.stderr)
        return 1

    text = args.input.read_text(encoding="utf-8")
    sections = split_specification(text)

    if not sections:
        print("ERROR: no numbered '## <n>. <title>' sections found.", file=sys.stderr)
        return 2

    args.output_dir.mkdir(parents=True, exist_ok=True)

    found_numbers = {num for num, _, _ in sections}
    written = 0
    for number, title, body in sections:
        slug = SECTION_SLUGS.get(number, slugify_title(title))
        filename = f"{number:02d}_{slug}.md"
        out_path = args.output_dir / filename
        if args.dry_run:
            print(f"[dry-run] would write {out_path} ({len(body)} chars)")
        else:
            out_path.write_text(body, encoding="utf-8")
            print(f"Wrote {out_path} ({len(body)} chars)")
        written += 1

    # Warn about any expected sections that were not present in the master doc.
    missing = sorted(set(SECTION_SLUGS) - found_numbers)
    if missing:
        names = ", ".join(f"{n} ({SECTION_SLUGS[n]})" for n in missing)
        print(f"\nWARNING: {len(missing)} expected section(s) not yet in the "
              f"master document and were skipped: {names}", file=sys.stderr)

    print(f"\nDone. {written} section file(s) processed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
