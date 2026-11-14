from harness import *
for net, scen in (('SDRAM-CLK','write'),('D0','read'),('D0','write')):
    m, r, info = run(net, scen)
    print(net, scen, info['dm'], '->', info['rm'], 'dpkg', info['dpk'], 'rpkg', info['rpk'], 'flight', info['rep']['delay_ps'], 'len', info['rep']['len_mm'])
    print('   full board:', fmt(m))
