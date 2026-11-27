"""19_B: z detailu cfd_fill_out.txt — kde v m1 (bid) svieèke minúty fillu leží úroveò. Body 0.01."""
import ast, collections as C, statistics as S
rows=[]; on=False
for ln in open('/Users/martin/IBS/.nightsearch/kritika/cfd_fill_out.txt'):
    if ln.startswith('== detail'): on=True; continue
    if on: rows.append(ast.literal_eval(ln))
seen=set(); out=C.defaultdict(list)
for iid,oid,kind,dr,w,lvl,px,bar in rows:
    if bar is None or (iid,oid,kind) in seen or lvl % 0.25 == 0 and px % 0.25 == 0: continue  # NT futures von
    seen.add((iid,oid,kind)); o,h,l,c=bar
    sym='XAU' if lvl<10000 else ('US500' if lvl<10000*1 else 'US100')
    sym='XAU' if lvl<5000 else ('US500' if lvl<9000 else 'US100')
    if kind=='limit_in': k,v=('limit_L: e-low', (lvl-l)) if dr==1 else ('limit_S: high-e', (h-lvl))
    elif kind=='Profit target': k,v=('TP_L: high-tp',(h-lvl)) if dr==1 else ('TP_S: tp-low',(lvl-l))
    elif kind=='Stop loss': k,v=('SL_L: sl-low',(lvl-l)) if dr==1 else ('SL_S: high-sl',(h-lvl))
    else: continue
    out[(sym,k)].append(round(v*100))
for k in sorted(out): v=sorted(out[k]); print(k,'n=',len(v),'min=',v[0],'med=',S.median(v),'vsetky=',v)
