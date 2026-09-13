"""Just enough of R's `DESCRIPTION` format to answer two questions.

`Package` and `Version`, from a file at the root of a repository or from CRAN.
Deliberately not a parser for the format: the fields that matter here are single-line, and a
partial implementation that says so beats depending on R being installed to read two strings.
"""

from __future__ import annotations


def parse_dcf(text: str) -> dict[str, str]:
    """Field names to values, with continuation lines joined by a space.

    A continuation line is an indented one, which is how the format wraps `Imports` and friends.
    """
    fields: dict[str, str] = {}
    name: str | None = None
    for line in text.splitlines():
        if not line.strip():
            name = None
            continue
        if line[0] in " \t" and name is not None:
            fields[name] = f"{fields[name]} {line.strip()}".strip()
            continue
        if ":" not in line:
            name = None
            continue
        key, _, value = line.partition(":")
        name = key.strip()
        fields[name] = value.strip()
    return fields


def compare_versions(left: str | None, right: str | None) -> int | None:
    """R's version ordering, for the one comparison that matters: development against CRAN.

    `-` and `.` separate components alike, which is what makes `1.2.3.9000` sort above `1.2.3`.
    Returns 1, 0 or -1, or None when either side is missing or not a version.
    """
    if not left or not right:
        return None
    try:
        left_parts = [int(part) for part in left.replace("-", ".").split(".")]
        right_parts = [int(part) for part in right.replace("-", ".").split(".")]
    except ValueError:
        return None
    length = max(len(left_parts), len(right_parts))
    left_parts += [0] * (length - len(left_parts))
    right_parts += [0] * (length - len(right_parts))
    return (left_parts > right_parts) - (left_parts < right_parts)
