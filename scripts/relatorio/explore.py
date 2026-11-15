import ifcopenshell, collections
f = ifcopenshell.open('ifc/EAN-BNX-XX-XX-M3D-CON-0001-P01.ifc')
print(f.schema)
c = collections.Counter(e.is_a() for e in f.by_type('IfcProduct'))
for k,v in c.most_common(): print(k,v)
print('storeys:')
for s in f.by_type('IfcBuildingStorey'): print(' ',s.Name, s.Elevation)
print('psets:')
pc = collections.Counter()
for r in f.by_type('IfcRelDefinesByProperties'):
    d = r.RelatingPropertyDefinition
    if d.is_a('IfcPropertySet'): pc[d.Name]+=1
    elif d.is_a('IfcElementQuantity'): pc['Q:'+d.Name]+=1
for k,v in pc.most_common(30): print(' ',k,v)
print('materials', len(f.by_type('IfcMaterial')))
print('classif', len(f.by_type('IfcClassificationReference')))
