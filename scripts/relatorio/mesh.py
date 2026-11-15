import ifcopenshell, ifcopenshell.geom, numpy as np, json, base64, zlib, pandas as pd
f=ifcopenshell.open('ifc/EAN-BNX-XX-XX-M3D-CON-0001-P01.ifc')
st=ifcopenshell.geom.settings(); st.set(st.USE_WORLD_COORDS,True)
df=pd.read_csv('data/elementos_ifc.csv').set_index('StepId')
order=['Subsolo','Pavimento Térreo','Mezanino']+[f'Pavimento Tipo {i:02d}' for i in range(1,9)]+['Terraço','Cobertura']
cl={'IfcBeam':0,'IfcColumn':1,'IfcSlab':2}
V=[];F=[];meta=[];vo=0;fo=0
for t in cl:
    for e in f.by_type(t):
        s=ifcopenshell.geom.create_shape(st,e).geometry
        v=np.array(s.verts).reshape(-1,3); fa=np.array(s.faces).reshape(-1,3)
        r=df.loc[e.id()]
        V.append(np.round(v*100).astype(np.int32)); F.append(fa.astype(np.uint32))
        meta.append([order.index(r.Pavimento_IFC),cl[t],str(r['TQS_Padrao.Titulo']),round(float(r.Volume_m3),3),vo,len(v),fo,len(fa),int(t=='IfcBeam' and pd.isna(r['TQS_Geometria.Largura']))])
        vo+=len(v);fo+=len(fa)
V=np.concatenate(V);F=np.concatenate(F)
print('verts',len(V),'tris',len(F),'bbox',V.min(0),V.max(0))
vb=zlib.compress(V.tobytes(),9);fb=zlib.compress(F.astype(np.uint32).tobytes(),9)
print('bytes',len(vb),len(fb))
np.save('V.npy',V);np.save('F.npy',F);json.dump(meta,open('meta.json','w'),ensure_ascii=False)
