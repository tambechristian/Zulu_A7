# -*- coding: utf-8 -*-
"""Restore one signal body from another EAGLE/Fusion board file."""

import io
import os
import re
import xml.etree.ElementTree as ET


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BRD = os.path.join(ROOT, "zulu_a7.brd")


def signal_pattern(net):
    return re.compile(
        r'<signal name="%s"[^>]*>.*?</signal>' % re.escape(net), re.S)


def main():
    net = os.environ["RESTORE_NET"]
    source_path = os.environ["RESTORE_SOURCE"]
    current = io.open(BRD, encoding="utf-8", errors="replace").read()
    source = io.open(source_path, encoding="utf-8", errors="replace").read()
    current_match = signal_pattern(net).search(current)
    source_match = signal_pattern(net).search(source)
    if not current_match or not source_match:
        raise ValueError("signal %s missing from current or source board" % net)
    updated = (current[:current_match.start()] + source_match.group(0) +
               current[current_match.end():])
    ET.fromstring(updated)
    io.open(BRD, "w", encoding="utf-8", newline="").write(updated)
    print("restored %s from %s" % (net, source_path))


if __name__ == "__main__":
    main()
