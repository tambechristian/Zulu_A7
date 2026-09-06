import re, collections, io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

P = r"C:\Users\tambe\Documents\Electronics\Zulu_A7\Datasheet\xc7a35tcpg236pkg_pinout.txt"
rows = "ABCDEFGHJKLMNPRTUVWY"          # JEDEC, no I/O/Q/S/X/Z
balls = {}
for ln in open(P, encoding="utf-8", errors="replace"):
    m = re.match(r"\s*([A-Y]\d{1,2})\s+(\S+)", ln)
    if not m:
        continue
    b, pin = m.group(1), m.group(2)
    r, c = b[0], int(b[1:])
    if r not in rows:
        continue
    balls[b] = pin

R = sorted({b[0] for b in balls}, key=rows.index)
C = sorted({int(b[1:]) for b in balls})
print("ball count %d   rows %s..%s (%d)   cols %d..%d (%d)"
      % (len(balls), R[0], R[-1], len(R), C[0], C[-1], len(C)))

ri = {r: i for i, r in enumerate(R)}
ci = {c: i for i, c in enumerate(C)}
n = max(len(R), len(C))
ring = collections.Counter()
occ = {}
for b in balls:
    i, j = ri[b[0]], ci[int(b[1:])]
    k = min(i, j, len(R) - 1 - i, len(C) - 1 - j)
    ring[k] += 1
    occ.setdefault(k, []).append(b)

print("\nring  balls  4n-4 for a full ring of a %dx%d grid" % (len(R), len(C)))
for k in sorted(set(range(n // 2 + 1)) | set(ring)):
    full = 4 * (len(R) - 2 * k) - 4 if len(R) - 2 * k > 1 else 1
    got = ring.get(k, 0)
    print("  %d   %5d   %5d   %s" % (k, got, full,
          "COMPLETE" if got == full else ("EMPTY" if got == 0 else "partial")))

# grid picture
print("\n     " + "".join("%2d" % c for c in C))
for r in R:
    line = "  %-3s" % r
    for c in C:
        line += " " + ("#" if r + str(c) in balls else ".")
    print(line)
