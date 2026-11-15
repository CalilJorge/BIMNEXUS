import ifcopenshell, collections
f = ifcopenshell.open('ifc/EAN-BNX-XX-XX-M3D-CON-0001-P01.ifc')
seen=set()
for t in ['IfcBeam','IfcColumn','IfcSlab']:
    el = f.by_type(t)[0]
    print('==',t, el.Name, el.ObjectType, el.Tag)
    for r in el.IsDefinedBy:
        if r.is_a('IfcRelDefinesByProperties'):
            d=r.RelatingPropertyDefinition
            if d.is_a('IfcPropertySet'):
                print(' PSET',d.Name)
                for p in d.HasProperties:
                    v=getattr(p,'NominalValue',None)
                    print('   ',p.Name,'=',v.wrappedValue if v else None)
# storey containment
cnt=collections.Counter()
for r in f.by_type('IfcRelContainedInSpatialStructure'):
    cnt[(r.RelatingStructure.Name)]+=len(r.RelatedElements)
print(cnt)
# materials / types
print(collections.Counter(e.ObjectType for e in f.by_type('IfcBeam')).most_common(5))
print(collections.Counter(e.PredefinedType for e in f.by_type('IfcSlab')).most_common(5))
