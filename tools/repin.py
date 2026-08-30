# -*- coding: utf-8 -*-
"""Re-assign U1's signal balls so each net leaves the package on the side its
far end is actually on.

The balls themselves do not move and neither does the set of balls carrying a
signal -- this only PERMUTES which net sits on which ball, among balls that
already carry a movable net. Per-side signal counts are therefore invariant, so
the escape has exactly the same job to do afterwards as before.

    python tools/repin.py           propose, print, write board/ball-remap.json
    python tools/repin.py --apply   also rewrite the <connect> map in zulu_a7.sch

ONE-SHOT. This edits zulu_a7.sch, which is a SOURCE file, not a generated one --
it is not part of the make_board -> escape -> ground -> power pipeline and must
not be re-run as though it were. Running it twice just re-optimises an already
optimised assignment, but the record of what moved lives in git, so commit
zulu_a7.sch and board/ball-remap.json together.
"""
import sys, os, re, io, csv, json, math, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCH = os.path.join(ROOT, "zulu_a7.sch")
BRD = os.path.join(ROOT, "zulu_a7.brd")
HERE = os.path.dirname(os.path.abspath(__file__))
DEVSET = "XC7A35T-CPG236"

# WHAT MAY NOT MOVE.
#
# Truly dedicated pins (TCK, TDO, DONE, PROGRAM_B, CCLK, M0-M2, CFGBVS, VP/VN,
# ...) need no list here: Vivado gives them a site type that does not begin
# "IO_", and the site filter below drops them. That filter is the robust half of
# this and it is deliberately doing the heavy lifting.
#
# What DOES need naming is the other kind: a general-purpose IO_ site carrying a
# second function this particular design depends on. Those look ordinary and the
# site filter waves them through. Getting this list from gate NAMES was a
# mistake -- the flash gates are called SPI_D00_MOSI / SPI_FCS_B, not the
# FLASH_* I guessed, so five of them sailed through as permutable and Master-SPI
# boot from U4 would have quietly stopped working. Key off the net, and assert
# every entry actually matched something.
PINNED_NETS = set("""
FLASH-D00 FLASH-D01 FLASH-D02 FLASH-D03 FLASH-CS#
PUDC_B
AIN15_P AIN15_N AIN16_P AIN16_N
""".split())

# THE CLOCK INPUTS ARE PINNED, and not by a rule of my own devising.
#
# First attempt let CHAN-CLK move anywhere matching r"_[MS]RCC_" and did not
# hold CLK-12M-FPGA at all. Both were wrong. "_[MS]RCC_" matches the N half of a
# differential CCIO pair, and a single-ended clock may only sit on the P half --
# vivado_io_check's own header records losing that argument once already. Worse,
# CLK-12M-FPGA moved to T18, IO_L17N_T2_A13_D29_14, which is not clock-capable
# at all, and place_design failed with "IOB driving a BUFG must use a CCIO".
#
# The lesson is not "write a better regex". Clock legality here depends on CCIO
# pairing, device half, and where the placer can put the BUFGs -- none of which
# is visible in the site-type string, and all of which Vivado decides. So take
# the clock list from the one place that is authoritative about which nets are
# clocks in this design, and refuse to move them at all. Two nets out of 96;
# moving them buys almost nothing and risks the whole placement.
def clock_nets():
    """the nets vivado_io_check drives through a BUFG, read from that file"""
    src = io.open(os.path.join(ROOT, "tools", "vivado_io_check.py"),
                  encoding="utf-8", errors="replace").read()
    ports = re.findall(r"BUFG\s+u_bufg\d+\s*\(\.I\(([A-Za-z0-9_]+)\)", src)
    assert ports, "no BUFG instantiation found in vivado_io_check.py"
    # the harness mangles net names into Verilog identifiers; undo it by
    # matching against the real net names later, so keep both forms
    return set(ports)


def is_clock(nm, ck):
    return re.sub(r"[^A-Za-z0-9]", "_", nm).upper() in ck


# ---------------------------------------------------------------- inputs
def sch_connects(s):
    d = re.search(r'<deviceset name="%s"[^>]*>(.*?)</deviceset>' % re.escape(DEVSET),
                  s, re.S).group(1)
    return re.findall(r'<connect gate="([^"]+)" pin="([^"]+)" pad="([^"]+)"/>', d)


def vivado_sites():
    rows = list(csv.reader(io.open(os.path.join(ROOT, "vivado", "zulu_a7_io.csv"),
                                   encoding="utf-8", errors="replace")))
    h = next(i for i, r in enumerate(rows) if r and "Pin Number" in r and "IO Bank" in r)
    H = {k: i for i, k in enumerate(rows[h])}
    out = {}
    for r in rows[h + 1:]:
        if len(r) < len(rows[h]) or not r[H["Pin Number"]].strip():
            continue
        out[r[H["Pin Number"]].strip()] = dict(
            bank=r[H["IO Bank"]].strip(), site=r[H["Site Type"]].strip(),
            sig=r[H["Signal Name"]].strip())
    return out


def brd_geometry():
    """ball centres for U1, and the centroid of every net's non-U1 pads.

    Pad coordinates come from E.board_copper, which power.py already relies on
    to hit real pads -- re-deriving the element transform here would just be a
    second, less-tested copy of it (Eagle's mirrored rotations are easy to get
    subtly wrong, and nothing downstream would catch it).
    """
    sys.path.insert(0, os.path.join(ROOT, "tools"))
    import escape as E
    b, pos, land, net, clr = E.load(BRD)
    acc = collections.defaultdict(list)
    for onet, x, y, hx, hy, side in E.board_copper(b, skip=("U1",)):
        acc[onet].append((x, y))
    target = {k: (sum(p[0] for p in v) / len(v), sum(p[1] for p in v) / len(v))
              for k, v in acc.items()}
    return pos, net, target


# ------------------------------------------------------- Hungarian (JV)
def hungarian(cost):
    """min-cost perfect matching, O(n^3). cost is n x n. returns row->col."""
    n = len(cost)
    INF = float("inf")
    u = [0.0] * (n + 1)
    v = [0.0] * (n + 1)
    p = [0] * (n + 1)
    way = [0] * (n + 1)
    for i in range(1, n + 1):
        p[0] = i
        j0 = 0
        minv = [INF] * (n + 1)
        used = [False] * (n + 1)
        while True:
            used[j0] = True
            i0, delta, j1 = p[j0], INF, 0
            for j in range(1, n + 1):
                if used[j]:
                    continue
                cur = cost[i0 - 1][j - 1] - u[i0] - v[j]
                if cur < minv[j]:
                    minv[j], way[j] = cur, j0
                if minv[j] < delta:
                    delta, j1 = minv[j], j
            for j in range(n + 1):
                if used[j]:
                    u[p[j]] += delta
                    v[j] -= delta
                else:
                    minv[j] -= delta
            j0 = j1
            if p[j0] == 0:
                break
        while j0:
            j1 = way[j0]
            p[j0] = p[j1]
            j0 = j1
    out = [0] * n
    for j in range(1, n + 1):
        if p[j]:
            out[p[j] - 1] = j - 1
    return out


# ---------------------------------------------------------------- main
def main(apply_it=False):
    # newline="" on the read as well as the write. Without it Python's
    # universal-newline translation hands back bare LF, the write puts bare LF
    # back, and the whole 16k-line schematic silently flips from CRLF to LF --
    # a clean 96-line diff locally, because git normalises it, and a whole-file
    # churn for anyone whose checkout does not.
    s = io.open(SCH, encoding="utf-8", errors="replace", newline="").read()
    con = sch_connects(s)
    viv = vivado_sites()
    pos, net, target = brd_geometry()

    xs = sorted({round(p[0], 3) for p in pos.values()})
    ys = sorted({round(p[1], 3) for p in pos.values()})
    CX, CY = (xs[0] + xs[-1]) / 2.0, (ys[0] + ys[-1]) / 2.0
    HX, HY = (xs[-1] - xs[0]) / 2.0 + 0.5, (ys[-1] - ys[0]) / 2.0 + 0.5

    def side(pad):
        x, y = pos[pad]
        u, w = x - CX, y - CY
        return ("right" if u > 0 else "left") if abs(u) >= abs(w) \
               else ("top" if w > 0 else "bottom")

    def exitpt(pad):
        x, y = pos[pad]
        sd = side(pad)
        if sd == "left":   return (CX - HX, y)
        if sd == "right":  return (CX + HX, y)
        if sd == "bottom": return (x, CY - HY)
        return (x, CY + HY)

    def cost(pad, tgt):
        bx, by = pos[pad]
        ex, ey = exitpt(pad)
        return (math.hypot(ex - bx, ey - by) +
                math.hypot(tgt[0] - ex, tgt[1] - ey))

    # gates that may be permuted: single-pad, not fixed, net has a far end,
    # and the ball is a general-purpose I/O site
    gate_pad = {}
    for g, pin, pad in con:
        gate_pad.setdefault(g, []).append(pad)
    ck = clock_nets()
    movable, pinned, seen_pin, seen_ck = [], [], set(), set()
    for g, pin, pad in con:
        nm = net.get(pad)
        if len(gate_pad[g]) != 1 or not nm or nm not in target:
            continue
        if not viv.get(pad, {}).get("site", "").startswith("IO_"):
            continue                      # dedicated pin -- not ours to move
        why = ("clock input" if is_clock(nm, ck) else
               "config/XADC" if nm in PINNED_NETS else None)
        if why:
            (seen_ck if why == "clock input" else seen_pin).add(nm)
            pinned.append((g, pad, nm, viv[pad]["site"], why))
            continue
        movable.append((g, pin, pad, nm))
    missing = PINNED_NETS - seen_pin
    assert not missing, ("these nets are pinned but were not found on an IO_ "
                         "ball -- the design changed and this list is stale: %s"
                         % sorted(missing))
    assert len(seen_ck) == len(ck), (
        "vivado_io_check drives %d nets through a BUFG but only %d of them were "
        "matched to a ball (%s) -- the name mangling has drifted and a clock "
        "would have been moved" % (len(ck), len(seen_ck), sorted(seen_ck)))
    movable.sort()
    pads = sorted(p for _, _, p, _ in movable)

    print("held back from the permutation, because their ball carries a")
    print("second function this design depends on:")
    for g, pad, nm, st, why in sorted(pinned, key=lambda q: (q[4], q[2])):
        print("   %-13s %-12s %-5s %s" % (why, nm, pad, st))
    print("")

    print("%d <connect> entries; %d gates permutable" % (len(con), len(movable)))
    held = collections.Counter(side(p) for p in pads)
    print("balls in play, by side: %s" % dict(sorted(held.items())))
    print("(that distribution is fixed -- only which net sits where changes)\n")

    # WHAT EACH NET IS WORTH. The 39 SDRAM nets are the ones that have to be
    # routed as a bundle across the board, so they get the weight. The 30 CHAN
    # nets land on X2, a 44-pin header running the FULL length of BOTH board
    # edges, so which side of the package they leave from barely changes their
    # length -- they are the natural thing to spend to buy the bus a short path.
    W_BUS, W_OTHER = float(os.environ.get("W_BUS", 4.0)), 1.0
    # W_SD: X3 sits on the left edge too, so the bus and the microSD
    # compete for the same balls. At W_SD=1 the bus takes them all and
    # microSD goes from 12.1 to 19.3 mm mean. At 3 the bus gives up 0.12 mm
    # of its own mean (-33% instead of -34%, same 25.4 mm worst net) and
    # microSD comes back to 14.4. That is the whole reason for the number.
    BUSRE = re.compile(r"^(D\d+|A\d+|BS\d|RAS#|CAS#|WE#|CKE|LDQM|UDQM|SDRAM-)")

    W_SD = float(os.environ.get("W_SD", 3.0))
    def wt(nm):
        if BUSRE.match(nm): return W_BUS
        if nm.startswith("SD-"): return W_SD
        return W_OTHER

    n = len(movable)
    BIG = 1e6

    def legal(nm, pad):
        return True          # every remaining net is a plain LVCMOS33 I/O

    C = [[(wt(movable[i][3]) * cost(pads[j], target[movable[i][3]])
           if legal(movable[i][3], pads[j]) else BIG)
          for j in range(n)] for i in range(n)]
    before = sum(cost(movable[i][2], target[movable[i][3]]) for i in range(n))
    asg = hungarian(C)
    after = sum(cost(pads[asg[i]], target[movable[i][3]]) for i in range(n))
    floor = sum(min(cost(p, target[g[3]]) for p in pads) for g in movable)
    print("unconstrained floor (every net on its own best ball, ignoring that"
          "\nthey would collide): %.1f mm, mean %.2f -- the bus fans out over"
          "\nU3's 20.8 mm of pads, so most of the length is irreducible.\n"
          % (floor, floor / n))

    print("total ball-to-far-end path over the %d nets:" % n)
    print("   before %8.1f mm   (mean %5.2f)" % (before, before / n))
    print("   after  %8.1f mm   (mean %5.2f)   -%.0f%%"
          % (after, after / n, 100.0 * (before - after) / before))

    plan = {}
    for i, (g, pin, pad, nm) in enumerate(movable):
        plan[(g, pin)] = (pad, pads[asg[i]], nm)

    def group(nm):
        if BUSRE.match(nm):                       return "SDRAM -> U3"
        if nm.startswith(("CHAN", "JA", "BTN")):  return "header -> X2"
        if nm.startswith("SD-"):                  return "microSD -> X3"
        if nm.startswith("UART") or nm.startswith("FT-"): return "FT2232 -> U2"
        if nm.startswith("LED"):                  return "LEDs"
        return "other"

    def tot(keys, which):
        return sum(cost(plan[k][which], target[plan[k][2]]) for k in keys)

    print("\n%-16s %4s   %-18s   %-18s" % ("", "n", "before mm", "after mm"))
    by = collections.defaultdict(list)
    for k in plan:
        by[group(plan[k][2])].append(k)
    for gname in sorted(by, key=lambda g: -len(by[g])):
        ks = by[gname]
        b0, a0 = tot(ks, 0), tot(ks, 1)
        print("%-16s %4d   %7.1f (%5.2f)    %7.1f (%5.2f)   %+.0f%%"
              % (gname, len(ks), b0, b0 / len(ks), a0, a0 / len(ks),
                 100.0 * (a0 - b0) / b0))
    bus = by["SDRAM -> U3"]
    sb = collections.Counter(side(plan[k][0]) for k in bus)
    sa = collections.Counter(side(plan[k][1]) for k in bus)
    print("\n   SDRAM balls by side  before %s" % dict(sorted(sb.items())))
    print("                        after  %s" % dict(sorted(sa.items())))
    worst0 = max(cost(plan[k][0], target[plan[k][2]]) for k in bus)
    worst1 = max(cost(plan[k][1], target[plan[k][2]]) for k in bus)
    print("   longest single SDRAM net  %.1f -> %.1f mm" % (worst0, worst1))

    moved = [k for k in plan if plan[k][0] != plan[k][1]]
    print("\n%d of %d gates change ball" % (len(moved), n))
    json.dump({"%s.%s" % k: {"from": v[0], "to": v[1], "net": v[2]}
               for k, v in plan.items()},
              io.open(os.path.join(ROOT, "board", "ball-remap.json"), "w", encoding="utf-8"),
              indent=1, sort_keys=True)

    # sanity: it must be a permutation of exactly the same pad set
    assert sorted(v[1] for v in plan.values()) == sorted(v[0] for v in plan.values())
    for k, v in plan.items():
        assert not is_clock(v[2], ck), "a clock net reached the permutation: %s" % v[2]
    assert all(C[i][asg[i]] < BIG for i in range(n)), "no legal assignment found"
    # per-side counts must be untouched, or the escape's job has changed
    b4 = collections.Counter(side(v[0]) for v in plan.values())
    af = collections.Counter(side(v[1]) for v in plan.values())
    assert b4 == af, (b4, af)
    print("checks: permutation of the same %d pads  OK" % n)
    print("        every site rule satisfied        OK")
    print("        per-side ball counts unchanged   OK  %s" % dict(sorted(af.items())))

    if apply_it:
        out = s
        for (g, pin), (old, new) in ((k, (v[0], v[1])) for k, v in plan.items()):
            if old == new:
                continue
            pat = '<connect gate="%s" pin="%s" pad="%s"/>' % (g, pin, old)
            assert out.count(pat) == 1, (pat, out.count(pat))
            out = out.replace(pat, '<connect gate="%s" pin="%s" pad="%s"/>' % (g, pin, new))
        io.open(SCH, "w", encoding="utf-8", newline="").write(out)
        print("\nzulu_a7.sch rewritten: %d <connect> pads changed" % len(moved))
    return 0


if __name__ == "__main__":
    sys.exit(main("--apply" in sys.argv))
