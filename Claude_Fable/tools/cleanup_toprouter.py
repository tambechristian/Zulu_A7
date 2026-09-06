"""Remove only wire segments that fail the board clearance checker.

Fusion TopRouter may route new inner-layer wires across existing vias when
optimizing a board that already contains fixed copper. This tool preserves the
conflict-free result and removes the exact wire segments named by
check_board.py so they can be rerouted separately.
"""

from __future__ import annotations

import ast
import os
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
CHECKER = ROOT / "tools" / "check_board.py"
WIRE_VIOLATION = re.compile(
    r"^(?P<net>.+?) wire "
    r"(?P<x1>-?[\d.]+),(?P<y1>-?[\d.]+)-"
    r"(?P<x2>-?[\d.]+),(?P<y2>-?[\d.]+) "
    r"L(?P<layer>\d+) vs "
)
SIGNAL = re.compile(
    r'(<signal name="(?P<name>[^"]+)"[^>]*>)(?P<body>.*?)(</signal>)',
    re.DOTALL,
)
WIRE = re.compile(r"<wire\b[^>]*/>")
ATTRIBUTE = re.compile(r'(\w+)="([^"]*)"')


def checker_violations(board: Path) -> list[str]:
    env = os.environ.copy()
    env["CHECK_FULL_VIOLATIONS"] = "1"
    result = subprocess.run(
        [sys.executable, str(CHECKER), str(board)],
        cwd=ROOT,
        env=env,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    match = re.search(
        r"\*\*\*\*  \d+ clearance violation\(s\): (\[.*\])",
        result.stdout,
    )
    if not match:
        if "clear foreign copper" in result.stdout:
            return []
        raise RuntimeError(
            "check_board.py did not emit a parseable clearance result:\n"
            + result.stdout[-2000:]
        )
    parsed = ast.literal_eval(match.group(1))
    if not isinstance(parsed, list) or not all(isinstance(item, str) for item in parsed):
        raise RuntimeError("Unexpected clearance result shape")
    return parsed


def violation_keys(violations: list[str]) -> set[tuple[str, float, float, float, float, int]]:
    keys = set()
    unhandled = []
    for violation in violations:
        match = WIRE_VIOLATION.match(violation)
        if not match:
            unhandled.append(violation)
            continue
        keys.add(
            (
                match.group("net"),
                round(float(match.group("x1")), 4),
                round(float(match.group("y1")), 4),
                round(float(match.group("x2")), 4),
                round(float(match.group("y2")), 4),
                int(match.group("layer")),
            )
        )
    if unhandled:
        raise RuntimeError(
            "Clearance violations without a removable wire segment:\n"
            + "\n".join(unhandled)
        )
    return keys


def wire_key(net: str, tag: str) -> tuple[str, float, float, float, float, int] | None:
    attrs = dict(ATTRIBUTE.findall(tag))
    needed = ("x1", "y1", "x2", "y2", "layer")
    if not all(name in attrs for name in needed):
        return None
    return (
        net,
        round(float(attrs["x1"]), 4),
        round(float(attrs["y1"]), 4),
        round(float(attrs["x2"]), 4),
        round(float(attrs["y2"]), 4),
        int(attrs["layer"]),
    )


def reverse_key(
    key: tuple[str, float, float, float, float, int]
) -> tuple[str, float, float, float, float, int]:
    net, x1, y1, x2, y2, layer = key
    return net, x2, y2, x1, y1, layer


def remove_violating_wires(
    source: str,
    keys: set[tuple[str, float, float, float, float, int]],
) -> tuple[str, set[tuple[str, float, float, float, float, int]]]:
    removed: set[tuple[str, float, float, float, float, int]] = set()

    def clean_signal(signal_match: re.Match[str]) -> str:
        net = signal_match.group("name")

        def clean_wire(wire_match: re.Match[str]) -> str:
            key = wire_key(net, wire_match.group(0))
            if key is not None and (key in keys or reverse_key(key) in keys):
                removed.add(key)
                return ""
            return wire_match.group(0)

        body = WIRE.sub(clean_wire, signal_match.group("body"))
        return signal_match.group(1) + body + signal_match.group(4)

    return SIGNAL.sub(clean_signal, source), removed


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: cleanup_toprouter.py INPUT.brd OUTPUT.brd", file=sys.stderr)
        return 2

    source_path = Path(sys.argv[1]).resolve()
    output_path = Path(sys.argv[2]).resolve()
    violations = checker_violations(source_path)
    keys = violation_keys(violations)
    cleaned, removed = remove_violating_wires(
        source_path.read_text(encoding="utf-8"),
        keys,
    )

    matched = {key for key in keys if key in removed or reverse_key(key) in removed}
    missing = keys - matched
    if missing:
        raise RuntimeError(f"Could not find {len(missing)} violating wire(s): {sorted(missing)}")

    output_path.write_text(cleaned, encoding="utf-8")
    print(
        f"Removed {len(removed)} unique wire segment(s) responsible for "
        f"{len(violations)} clearance violation(s)."
    )
    print(f"Wrote {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
