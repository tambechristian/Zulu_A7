import re, collections, io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = r"C:\Users\tambe\Documents\Electronics\Zulu_A7"
b = open(ROOT + r"\zulu_a7.brd", encoding="utf-8", errors="replace").read()

# ball -> net, straight from the board's <contactref>s for U1
net = {}
for m in re.finditer(r'<signal name="([^"]+)">(.*?)</signal>', b, re.S):
    n, body = m.group(1), m.group(2)
    for c in re.finditer(r'<contactref element="U1" pad="([^"]+)"/>', body):
        net[c.group(1)] = n
print("U1 balls with a net: %d" % len(net))

rows = "ABCDEFGHJKLMNPRTUVWY"
R = sorted({k[0] for k in net}, key=rows.index)
C = sorted({int(k[1:]) for k in net})
ri = {r: i for i, r in enumerate(R)}
ci = {c: i for i, c in enumerate(C)}


def ring(ball):
    i, j = ri[ball[0]], ci[int(ball[1:])]
    return min(i, j, len(R) - 1 - i, len(C) - 1 - j)


def nbrs(ball):
    i, j = ri[ball[0]], ci[int(ball[1:])]
    for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        a, c = i + di, j + dj
        if 0 <= a < len(R) and 0 <= c < len(C):
            k = R[a] + str(C[c])
            if k in net:
                yield k


POWER = re.compile(r"^(GND|VCC|VDD|\+|VU$|VEXT)", re.I)


def kind(n):
    return "pwr" if POWER.match(n) or n.upper() in ("GND", "AGND", "GNDADC") else "sig"


by = collections.defaultdict(lambda: collections.Counter())
for ball, n in net.items():
    by[ring(ball)][kind(n)] += 1

print("\nring   sig   pwr   total")
for k in sorted(by):
    print("  %d %6d %5d %7d" % (k, by[k]["sig"], by[k]["pwr"], sum(by[k].values())))

# --- does every core ball reach ring 6 through same-net orthogonal neighbours?
core = [x for x in net if ring(x) >= 6]
print("\ncore balls (ring>=6): %d   nets: %s"
      % (len(core), dict(collections.Counter(net[x] for x in core))))
seen, stuck = set(), []
for start in core:
    if ring(start) == 6:
        continue
    # flood through same-net neighbours, looking for a ring-6 ball
    q, vis, found = [start], {start}, False
    while q:
        cur = q.pop()
        if ring(cur) == 6:
            found = True
            break
        for x in nbrs(cur):
            if x not in vis and net[x] == net[cur]:
                vis.add(x)
                q.append(x)
    if not found:
        stuck.append(start)
print("interior core balls that CANNOT reach ring 6 by same-net ganging: %d %s"
      % (len(stuck), stuck))

# --- ring 1: how many need a lane, after ganging power to ring 0 or 2?
need, ganged = [], []
for ball in [x for x in net if ring(x) == 1]:
    if kind(net[ball]) == "sig":
        need.append(ball)
        continue
    if any(ring(x) in (0, 2) and net[x] == net[ball] for x in nbrs(ball)):
        ganged.append(ball)
    else:
        need.append(ball)
print("\nring 1: %d balls -> %d can gang to a same-net ring 0/2 neighbour, "
      "%d still need a lane" % (by[1]["sig"] + by[1]["pwr"], len(ganged), len(need)))
print("   of the %d, signals %d, power with no same-net neighbour %d"
      % (len(need), sum(1 for x in need if kind(net[x]) == "sig"),
         sum(1 for x in need if kind(net[x]) == "pwr")))

lanes = 4 * (len(R) - 2 * 2) - 4        # gaps around ring 2 == ring 2 ball count
print("   lanes available between adjacent ring-2 lands: %d" % lanes)
print("   -> %d lanes for %d escapes, %.0f%% used" % (lanes, len(need), 100.0 * len(need) / lanes))
