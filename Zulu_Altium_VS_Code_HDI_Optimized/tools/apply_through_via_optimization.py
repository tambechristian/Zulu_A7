"""Apply the verified HDI-to-through-via conversion plan to the copied board.

The generated board is an intermediate: open it in Altium, repour all
polygons, run a full DRC, and save it before releasing the design.
"""

from __future__ import annotations

import hashlib
import json
import os
import struct
from collections import Counter, defaultdict
from pathlib import Path

import olefile
from altium_monkey import AltiumPcbDoc


ROOT = Path(__file__).resolve().parents[1]
PCB = ROOT / "Imported zulu_a7.PrjPcb" / "zulu_a7_hdi_optimized.PcbDoc"
PLAN = Path(__file__).with_name("through_conversion_plan.json")
SOURCE_SHA256 = "72E9A716E03616D9464C0040A7B1187561E740C551104720DD288EA147B4E30B"
UNIT_MM = 2.54e-6
LAYER_NAMES = {
    1: "Top",
    4: "L2-GND",
    2: "L3-SIG",
    3: "L4-SIG",
    5: "L5-VCC3V3",
    32: "Bottom",
}
THROUGH_SPAN = ("Top", "L2-GND", "L3-SIG", "L4-SIG", "L5-VCC3V3", "Bottom")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def stream_hashes(path: Path) -> dict[str, tuple[int, str]]:
    streams: dict[str, tuple[int, str]] = {}
    with olefile.OleFileIO(str(path)) as pcb:
        for entry in pcb.listdir(streams=True, storages=False):
            name = "/".join(entry)
            data = pcb.openstream(entry).read()
            streams[name] = (len(data), hashlib.sha256(data).hexdigest())
    return streams


def span(via: object) -> tuple[str, ...]:
    start = LAYER_NAMES[getattr(via, "layer_start")]
    end = LAYER_NAMES[getattr(via, "layer_end")]
    order = tuple(LAYER_NAMES[layer] for layer in (1, 4, 2, 3, 5, 32))
    i, j = sorted((order.index(start), order.index(end)))
    return order[i : j + 1]


def via_key(via: object, net_names: dict[int, str]) -> tuple[str, float, float]:
    net_index = getattr(via, "net_index")
    return (
        net_names[net_index],
        round(getattr(via, "x") * UNIT_MM, 4),
        round(getattr(via, "y") * UNIT_MM, 4),
    )


def load_plan() -> tuple[
    set[tuple[str, float, float]],
    dict[tuple[str, float, float], Counter[tuple[str, ...]]],
]:
    payload = json.loads(PLAN.read_text(encoding="utf-8"))
    plan = payload["plan"]
    selected = {
        (via["net"], round(via["x"], 4), round(via["y"], 4))
        for via in plan["vias"]
    }
    expected: dict[tuple[str, float, float], Counter[tuple[str, ...]]] = defaultdict(
        Counter
    )
    for via in plan["remove"]["vias"]:
        key = (via["net"], round(via["x"], 4), round(via["y"], 4))
        expected[key][tuple(via["span"])] += 1
    if selected != set(expected):
        raise ValueError("conversion plan additions and removals name different sites")
    return selected, expected


def main() -> None:
    if sha256(PCB) != SOURCE_SHA256:
        raise ValueError(
            "refusing to modify a board that does not match the routed source hash"
        )

    selected, expected_spans = load_plan()
    before_streams = stream_hashes(PCB)
    document = AltiumPcbDoc.from_file(PCB)
    net_names = {index: net.name for index, net in enumerate(document.nets)}

    groups: dict[tuple[str, float, float], list[object]] = defaultdict(list)
    for via in document.vias:
        key = via_key(via, net_names)
        if key in selected:
            groups[key].append(via)

    if set(groups) != selected:
        missing = sorted(selected - set(groups))
        raise ValueError(f"planned sites missing from copied board: {missing}")

    for key, vias in groups.items():
        actual = Counter(span(via) for via in vias)
        if actual != expected_spans[key]:
            raise ValueError(
                f"{key} span mismatch: found {dict(actual)}, "
                f"expected {dict(expected_spans[key])}"
            )

    through_template = next(
        via for via in document.vias if span(via) == THROUGH_SPAN
    )
    retained: list[object] = []
    emitted: set[tuple[str, float, float]] = set()
    for via in document.vias:
        key = via_key(via, net_names)
        if key not in selected:
            retained.append(via)
            continue
        if key in emitted:
            continue

        emitted.add(key)
        via.layer_start = through_template.layer_start
        via.layer_end = through_template.layer_end
        via.diameter = through_template.diameter
        via.hole_size = through_template.hole_size
        via.diameter_by_layer = [through_template.diameter] * 32
        via.via_mode = through_template.via_mode
        via.external_stack_entries = []
        via.drill_layer_pair_type = 0
        retained.append(via)

    old_count = len(document.vias)
    document.vias = retained
    document._raw_streams["Vias6/Header"] = struct.pack("<I", len(retained))

    temporary = PCB.with_suffix(".optimized.tmp.PcbDoc")
    document.save(temporary)

    after = AltiumPcbDoc.from_file(temporary)
    after_net_names = {index: net.name for index, net in enumerate(after.nets)}
    converted_counts: Counter[tuple[str, float, float]] = Counter()
    for via in after.vias:
        key = via_key(via, after_net_names)
        if key in selected:
            if span(via) != THROUGH_SPAN:
                raise ValueError(f"{key} did not serialize as a through via")
            if via.diameter != through_template.diameter:
                raise ValueError(f"{key} has the wrong through-via diameter")
            if via.hole_size != through_template.hole_size:
                raise ValueError(f"{key} has the wrong through-via drill")
            if via.drill_layer_pair_type != 0:
                raise ValueError(f"{key} retained a microvia drill marker")
            converted_counts[key] += 1

    if converted_counts != Counter({key: 1 for key in selected}):
        raise ValueError("optimized board does not contain one through via per planned site")
    if len(after.vias) != old_count - sum(map(len, groups.values())) + len(selected):
        raise ValueError("optimized via count does not match the conversion plan")

    after_streams = stream_hashes(temporary)
    changed_streams = {
        name
        for name in set(before_streams) | set(after_streams)
        if before_streams.get(name) != after_streams.get(name)
    }
    if changed_streams != {"Vias6/Data", "Vias6/Header"}:
        raise ValueError(
            "unexpected streams changed during optimization: "
            + ", ".join(sorted(changed_streams))
        )

    os.replace(temporary, PCB)
    print(f"converted HDI sites: {len(selected)}")
    print(f"via objects: {old_count} -> {len(after.vias)}")
    print(f"optimized SHA-256: {sha256(PCB)}")
    print("NEXT: open in Altium, repour all polygons, run full DRC, and save")


if __name__ == "__main__":
    main()
