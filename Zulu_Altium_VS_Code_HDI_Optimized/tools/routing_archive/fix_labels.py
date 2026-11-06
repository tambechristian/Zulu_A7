"""Sheet-specific clean-ups after fix_text_orientation.py, all found by
reviewing the Smart PDF export.  Anchors stay on their wires (the only
wire edit is lengthening six stubs, with the label moved to the new end).

  sheet 1  SW1/2/3_NET were hidden names in EAGLE and now sit on the
           inductors: small font, hung under the wire, centred on the stub.
           The GND labels on the FB1/FB2 return lines shared a band with the
           VCC1V8/VCC3V3 rail labels: slide them left along their wires.
  sheet 2  PMOD-1..10 (hidden names) ran over J1's pins: small, under the
           wire, anchored at the J1 end of the stub so they clear the
           resistor value texts of the next row.  NODE_P0/P1: smaller vertical font, centred on the wire.
           VEXT shared a band with ANALOG-IO1: hang it under pin 44's wire.
  sheet 5  the six GNDADC/GND labels started on top of the pin designators
           A12/B13/B12/A13/A11/B11: lengthen the 10-unit stubs to 25 and
           move the labels to the new end, GNDADC in 7 pt so it stops short
           of the EAGLE frame line at x~1040.
  sheet 6  VCC1V0 on the VCCBRAM feed ran into pin M11's designator: move
           it 31 units left along the wire.  A note used an em dash that
           the importer double-encoded: use the ASCII form the other notes use.
"""
import sys, re
sys.path.insert(0, sys.argv[1])
from fix_text_orientation import read_stream, write_stream, split, join, field, set_field, fonts_of

def small_font(fonts, fid, rot):
    base=fonts[fid]
    cands=[i for i,g in fonts.items() if g['name']==base['name'] and g['rot']==rot and g['size']<base['size']]
    return max(cands, key=lambda i: fonts[i]['size']) if cands else fid

def edit_sheet(path, rules):
    data=read_stream(path,'FileHeader'); recs=split(data)
    fonts=fonts_of(next(r for r in recs if r[1].startswith(b'|RECORD=31|'))[1])
    done=[]
    for rec in recs:
        b=rec[1]
        for name,match,apply in rules:
            if match(b):
                rec[1]=apply(rec[1], fonts); done.append(name)
    new=join(recs); write_stream(path,'FileHeader',new)
    assert read_stream(path,'FileHeader')==new
    return done

def label(text, x=None, y=None):
    def m(b):
        return (b.startswith(b'|RECORD=25|') and field(b,'Text')==text
                and (x is None or field(b,'Location.X')==str(x)) and (y is None or field(b,'Location.Y')==str(y)))
    return m
def wire(x1,y1,x2,y2):
    return lambda b: b.startswith(b'|RECORD=27|') and all(field(b,k)==str(v) for k,v in (('X1',x1),('Y1',y1),('X2',x2),('Y2',y2)))
def hang_small(b,fonts):      # horizontal label, small font, centred, hanging under the wire
    b=set_field(b,'FontID',str(small_font(fonts,int(field(b,'FontID') or 1),0)))
    return set_field(b,'Justification','7')
def vertical_small(b,fonts):  # vertical label, smaller font, centred along the wire
    b=set_field(b,'FontID',str(small_font(fonts,int(field(b,'FontID') or 1),90)))
    return set_field(b,'Justification','1')
def move_x(x): return lambda b,f: set_field(b,'Location.X',str(x))
def hang_small_at(x):
    return lambda b,f: set_field(hang_small(b,f),'Location.X',str(x))
def font_pt(pt):
    def a(b,fonts):
        base=fonts[int(field(b,'FontID') or 1)]
        for i,g in fonts.items():
            if g['name']==base['name'] and g['rot']==base['rot'] and g['size']==pt: return set_field(b,'FontID',str(i))
        return b
    return a
def label_x_in(text, xs, y):
    return lambda b: b.startswith(b'|RECORD=25|') and field(b,'Text')==text and field(b,'Location.X') in [str(x) for x in xs] and field(b,'Location.Y')==str(y)
def wire_x2_in(x1,y1,x2s,y2):
    return lambda b: b.startswith(b'|RECORD=27|') and field(b,'X1')==str(x1) and field(b,'Y1')==str(y1) and field(b,'X2') in [str(x) for x in x2s] and field(b,'Y2')==str(y2)
def just(j):   return lambda b,f: set_field(b,'Justification',str(j))
def set_x2(x): return lambda b,f: set_field(b,'X2',str(x))
def fix_dash(b,f):
    return re.sub(rb'\|(%UTF8%)?Text=VCCAUX [^|]*?1x47uF', b'|Text=VCCAUX -- 1x47uF', b)

rules={
 1:[('SW1_NET small', label('SW1_NET',617,1072), hang_small),
    ('SW2_NET small', label('SW2_NET',612,1032), hang_small),
    ('SW3_NET small', label('SW3_NET',612,992), hang_small),
    ('GND FB1 return left', label('GND',815,1042), move_x(790)),
    ('GND FB2 return left', label('GND',820,1002), move_x(775))],
 2:[(f'{n} small at J1 end', label(n), hang_small_at(270)) for n in ('PMOD-1','PMOD-2','PMOD-3','PMOD-4')]
   +[(f'{n} small at J1 end', label(n), hang_small_at(340)) for n in ('PMOD-7','PMOD-8','PMOD-9','PMOD-10')]
   +[('NODE_P0 vertical', label('NODE_P0'), vertical_small),('NODE_P1 vertical', label('NODE_P1'), vertical_small),
     ('VEXT under wire', label('VEXT',360,919), just(6))],
 5:[(f'stub {y} longer', wire_x2_in(975,y,(985,1005),y), set_x2(1000)) for y in (537,547,567,577,587,597)]
   +[(f'GND {y} to stub end', label_x_in('GND',(985,1005),y), move_x(1000)) for y in (537,547)]
   +[(f'GNDADC {y} to stub end, 7pt', label_x_in('GNDADC',(985,1005),y), lambda b,f: font_pt(7)(move_x(1000)(b,f),f)) for y in (567,577,587,597)],
 6:[('VCC1V0 off M11', label('VCC1V0',331,822), move_x(300)),
    ('VCCAUX note dash', lambda b: b.startswith(b'|RECORD=4|') and b'VCCAUX' in b and b'1x47uF' in b, fix_dash)],
}
if __name__=='__main__':
    folder=sys.argv[2]
    for k,rs in rules.items():
        done=edit_sheet(f'{folder}/zulu_a7_{k}.SchDoc', rs)
        print(f'sheet {k}: {len(done)} edits ->', done)
        missing=[n for n,_,_ in rs if n not in done]
        if missing: print('   NOT FOUND:', missing)
