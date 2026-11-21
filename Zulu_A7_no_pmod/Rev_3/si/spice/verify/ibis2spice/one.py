import sys, json, cases2
case, m = cases2.run(tuple(json.loads(sys.argv[1])))
print('%-6s %-5s %-3s %-12s ovs %+.4f  uns %.4f  | rx pin max %.3f min %.3f' % (*case, m['overshoot'], m['undershoot'], m['rx_pin_max'], m['rx_pin_min']), flush=True)
