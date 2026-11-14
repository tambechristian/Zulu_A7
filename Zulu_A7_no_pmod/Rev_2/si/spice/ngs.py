"""Minimal ctypes driver for KiCad's shared ngspice (ngspice.dll). run(netlist_lines) -> {vector: numpy array}."""
import ctypes as C, os, numpy as np
DLLDIR = r'C:/Program Files/KiCad/10.0/bin'
os.add_dll_directory(DLLDIR)
_lib = C.CDLL(os.path.join(DLLDIR, 'ngspice.dll'))
_out = []
SENDCHAR = C.CFUNCTYPE(C.c_int, C.c_char_p, C.c_int, C.c_void_p)
SENDSTAT = C.CFUNCTYPE(C.c_int, C.c_char_p, C.c_int, C.c_void_p)
CTRLEXIT = C.CFUNCTYPE(C.c_int, C.c_int, C.c_bool, C.c_bool, C.c_int, C.c_void_p)
BGRUN = C.CFUNCTYPE(C.c_int, C.c_bool, C.c_int, C.c_void_p)
_cb = (SENDCHAR(lambda s, i, p: (_out.append(s.decode(errors='replace')), 0)[1]),
       SENDSTAT(lambda s, i, p: 0), CTRLEXIT(lambda *a: 0), BGRUN(lambda *a: 0))
_lib.ngSpice_Init(_cb[0], _cb[1], _cb[2], None, None, _cb[3], None)
class VecInfo(C.Structure):
    _fields_ = [('v_name', C.c_char_p), ('v_type', C.c_int), ('v_flags', C.c_short),
                ('v_realdata', C.POINTER(C.c_double)), ('v_compdata', C.c_void_p), ('v_length', C.c_int)]
_lib.ngGet_Vec_Info.restype = C.POINTER(VecInfo)
_lib.ngSpice_CurPlot.restype = C.c_char_p
_lib.ngSpice_AllVecs.restype = C.POINTER(C.c_char_p)
def cmd(s):
    return _lib.ngSpice_Command(s.encode())
def run(lines):
    del _out[:]
    cmd('destroy all')
    cmd('remcirc')
    arr = (C.c_char_p * (len(lines) + 1))(*[l.encode() for l in lines], None)
    _lib.ngSpice_Circ(arr)
    cmd('run')
    plot = _lib.ngSpice_CurPlot().decode()
    names = []
    p = _lib.ngSpice_AllVecs(plot.encode())
    i = 0
    while p[i]:
        names.append(p[i].decode()); i += 1
    res = {}
    for n in names:
        vi = _lib.ngGet_Vec_Info(('%s.%s' % (plot, n)).encode())
        if vi and vi.contents.v_realdata:
            res[n.lower()] = np.ctypeslib.as_array(vi.contents.v_realdata, shape=(vi.contents.v_length,)).copy()
    return res
def log():
    return ''.join(_out)
