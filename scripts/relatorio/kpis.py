import pandas as pd
df = pd.read_csv('data/elementos_ifc.csv')           # gerado por extract.py
b, c, s = (df[df.IfcClass == k] for k in ('IfcBeam', 'IfcColumn', 'IfcSlab'))
tot = df.Volume_m3.sum()
area = s['TQS_Geometria.Area_superficie'].sum()
print('Elementos por tipo', len(b), len(c), len(s), '| pilar-parede (Cortina=Sim):', (c['TQS_Geometria.Cortina'] == 'Sim').sum())
print('Volume total/vigas/pilares/lajes (m3):', *(round(x, 1) for x in (tot, b.Volume_m3.sum(), c.Volume_m3.sum(), s.Volume_m3.sum())))
print('Area de laje (m2):', round(area, 1), '| espessura media (cm):', round(s.Volume_m3.sum() / area * 100, 1), '| m3/m2:', round(tot / area, 3))
print('% volume por tipo:', *(round(d.Volume_m3.sum() / tot * 100, 1) for d in (b, c, s)))
ok = b.dropna(subset=['TQS_Geometria.Largura', 'TQS_Geometria.Altura'])
print('Comprimento de vigas com secao (m):', round((ok.Volume_m3 / (ok['TQS_Geometria.Largura'] * ok['TQS_Geometria.Altura'] / 1e4)).sum(), 0), 'em', len(ok), 'vigas; sem secao:', len(b) - len(ok))
print('Secoes distintas de vigas:', ok.groupby(['TQS_Geometria.Largura', 'TQS_Geometria.Altura']).ngroups)
pk = ['TQS_Geometria.Secao', 'TQS_Geometria.Dimensao_b1', 'TQS_Geometria.Dimensao_h1', 'TQS_Geometria.Dimensao_b2', 'TQS_Geometria.Dimensao_h2']
print('Secoes distintas de pilares:', c.fillna(-1).groupby(pk).ngroups)
print('Classes de concreto:', df['TQS_Padrao.Material'].value_counts(dropna=False).to_dict())
print('Sem material:', df['TQS_Padrao.Material'].isna().sum(), '| sem pavimento:', df.Pavimento_IFC.isna().sum(), '| volume zero:', (df.Volume_m3.fillna(0) <= 0).sum())
print('Nomes fora do padrao [VPL]+numero:', (~df.Name.fillna('').str.match(r'^[VPL]\d+$')).sum())
esperado = {'IfcBeam': 'Vigas', 'IfcColumn': 'Pilares', 'IfcSlab': 'Lajes'}
print('Classe IFC x tipo TQS divergente:', (df.IfcClass.map(esperado) != df['TQS_Padrao.Tipo']).sum())
ordem = ['Subsolo', 'Pavimento Térreo', 'Mezanino'] + [f'Pavimento Tipo {i:02d}' for i in range(1, 9)] + ['Terraço', 'Cobertura']
t = df.pivot_table(index='Pavimento_IFC', columns='IfcClass', values='Volume_m3', aggfunc='sum').reindex(ordem)
t['total'] = t.sum(axis=1)
t['n'] = df.groupby('Pavimento_IFC').size().reindex(ordem)
print(t.round(1).to_string())
