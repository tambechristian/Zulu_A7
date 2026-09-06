import math, io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

PITCH = 0.5
DIAG = PITCH * math.sqrt(2) / 2          # ball centre -> diagonal void centre
MIL = 0.0254


def lane(L, w, s):                        # trace between two adjacent lands
    return (PITCH - L) - (w + 2 * s)


def void(L, s, vland):                    # through via in the diagonal void
    return 2 * (DIAG - L / 2 - s) - vland


def vip(L, drill, ring):                  # via inside the ball land
    return L - (drill + 2 * ring)


def f(x):
    return ("fits +%.4f" % x) if x >= 0 else ("  NO %.4f" % x)


print("gap between two lands, 0.5 mm pitch")
for L in (0.275, 0.25, 0.225, 0.20):
    print("   land %.3f -> gap %.3f   diagonal void free dia %.4f (before clearance)"
          % (L, PITCH - L, 2 * (DIAG - L / 2)))

print("\n=== A trace passing BETWEEN two lands ===")
print("   %-34s %s" % ("rule", "  ".join("land %.3f" % L for L in (0.275, 0.25, 0.225, 0.20))))
for name, w, s in (("PCBWay 5/5 mil  (outer 35 um, med)", 5 * MIL, 5 * MIL),
                   ("PCBWay 4/4 mil  (outer 18 um, med)", 4 * MIL, 4 * MIL),
                   ("PCBWay 3.5/3.5  (outer 18 um, BGA)", 3.5 * MIL, 3.5 * MIL),
                   ("JLCPCB 3.5/3.5  (multilayer std)  ", 3.5 * MIL, 3.5 * MIL),
                   ("JLCPCB 3/3 mil  (BGA fanout, +20%)", 3 * MIL, 3 * MIL),
                   ("PCBWay HDI 0.065/0.065            ", 0.065, 0.065)):
    print("   %-34s %s" % (name, "  ".join("%s" % f(lane(L, w, s)) for L in (0.275, 0.25, 0.225, 0.20))))

print("\n=== A through via in the DIAGONAL VOID between four lands ===")
print("   %-34s %s" % ("via land / clearance", "  ".join("land %.3f" % L for L in (0.275, 0.25, 0.225, 0.20))))
for name, vland, s in (("PCBWay 0.30 pad, 3.5 mil clr      ", 0.30, 3.5 * MIL),
                       ("PCBWay 0.3024 (0.15+2x3mil), 3.5  ", 0.3024, 3.5 * MIL),
                       ("JLCPCB 0.25 pad (0.15 drill), 3mil", 0.25, 3 * MIL),
                       ("JLCPCB 0.30 pad (0.2 drill),  3mil", 0.30, 3 * MIL),
                       ("JLCPCB 0.30 pad (0.2 drill),  3.5 ", 0.30, 3.5 * MIL)):
    print("   %-34s %s" % (name, "  ".join("%s" % f(void(L, s, vland)) for L in (0.275, 0.25, 0.225, 0.20))))

print("\n=== A via INSIDE the ball land (via-in-pad) ===")
print("   %-34s %s" % ("drill + 2 x ring", "  ".join("land %.3f" % L for L in (0.275, 0.25, 0.225, 0.20))))
for name, drill, ring in (("PCBWay PTH 0.15 + 3 mil ring      ", 0.15, 3 * MIL),
                          ("PCBWay laser 4 mil + 3 mil ring   ", 4 * MIL, 3 * MIL),
                          ("PCBWay laser 3 mil + 3 mil ring   ", 3 * MIL, 3 * MIL),
                          ("JLCPCB PTH 0.15 + 0.05 ring       ", 0.15, 0.05),
                          ("JLCPCB PTH 0.20 + 0.05 ring       ", 0.20, 0.05)):
    print("   %-34s %s" % (name, "  ".join("%s" % f(vip(L, drill, ring)) for L in (0.275, 0.25, 0.225, 0.20))))

print("\n=== aspect ratio, board thickness / drill ===")
for t in (1.6, 1.2, 1.0):
    row = "   %.1f mm board: " % t
    for d in (0.15, 0.16, 0.20, 0.25):
        row += " %.2f->%.1f:1 " % (d, t / d)
    print(row)
print("   PCBWay item 6: <=8 normal, 8 medium, 10 high, >12 impossible")
print("   JLCPCB: 10:1 is the usual ceiling, <8:1 preferred")

print("\n=== drill density (JLCPCB surcharge above 150,000 holes/m2) ===")
area = 69.85 * 20.32 / 1e6
for n in (200, 300, 400, 500):
    print("   %d holes on %.6f m2 -> %,d /m2  %s".replace(",d", "d")
          % (n, area, int(n / area), "over" if n / area > 150000 else "under"))
