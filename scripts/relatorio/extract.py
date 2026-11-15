import ifcopenshell, ifcopenshell.geom, pandas as pd, collections
f = ifcopenshell.open('ifc/EAN-BNX-XX-XX-M3D-CON-0001-P01.ifc')
settings = ifcopenshell.geom.settings()
settings.set(settings.USE_WORLD_COORDS, True)
storey = {}
for r in f.by_type('IfcRelContainedInSpatialStructure'):
    for e in r.RelatedElements: storey[e.id()] = r.RelatingStructure.Name
rows=[]
for t in ['IfcBeam','IfcColumn','IfcSlab']:
    for e in f.by_type(t):
        d={'GlobalId':e.GlobalId,'StepId':e.id(),'IfcClass':t,'Name':e.Name,'Pavimento_IFC':storey.get(e.id())}
        for r in e.IsDefinedBy:
            if r.is_a('IfcRelDefinesByProperties') and r.RelatingPropertyDefinition.is_a('IfcPropertySet'):
                ps=r.RelatingPropertyDefinition
                for p in ps.HasProperties:
                    v=getattr(p,'NominalValue',None)
                    if v is not None: d[f'{ps.Name}.{p.Name}']=v.wrappedValue
        # geometry
        try:
            sh=ifcopenshell.geom.create_shape(settings,e)
            import ifcopenshell.util.shape as us
            d['Volume_m3']=us.get_volume(sh.geometry)
        except Exception as ex:
            d['Volume_m3']=None; d['geom_err']=str(ex)[:60]
        rows.append(d)
df=pd.DataFrame(rows)
df.to_csv('data/elementos_ifc.csv',index=False)
print(df.shape); print(df.columns.tolist())
print(df.isna().sum()[df.isna().sum()>0])
print(df.groupby('IfcClass').Volume_m3.agg(['count','sum']))
print(df['TQS_Padrao.Material'].value_counts())
print((df['Pavimento_IFC']!=df['TQS_Padrao.Planta']).sum(),'divergências pavimento IFC x Planta')
