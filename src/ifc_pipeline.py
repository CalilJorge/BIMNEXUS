"""Extração de dados e malhas 3D de um arquivo IFC com ifcopenshell.

Uso em linha de comando (gera os arquivos da pasta data/):
    python scripts/build_data.py ifc/MODELO.ifc

O app Streamlit NÃO precisa do ifcopenshell para rodar: ele lê os arquivos
já gerados em data/. O ifcopenshell só é necessário para (re)gerar os dados
ou para o upload de um IFC dentro do app.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

CLASSES_IFC = {"IfcBeam": "Vigas", "IfcColumn": "Pilares", "IfcSlab": "Lajes"}


def _valor(p):
    v = getattr(p, "NominalValue", None)
    return v.wrappedValue if v is not None else None


def propriedades(el) -> dict:
    """Property sets e quantidades do elemento, achatados como 'Pset.Propriedade'."""
    out = {}
    for rel in getattr(el, "IsDefinedBy", None) or []:
        if not rel.is_a("IfcRelDefinesByProperties"):
            continue
        d = rel.RelatingPropertyDefinition
        if d.is_a("IfcPropertySet"):
            for p in d.HasProperties or []:
                if p.is_a("IfcPropertySingleValue"):
                    v = _valor(p)
                    if v is not None:
                        out[f"{d.Name}.{p.Name}"] = v
        elif d.is_a("IfcElementQuantity"):
            for q in d.Quantities or []:
                for attr in ("LengthValue", "AreaValue", "VolumeValue", "WeightValue", "CountValue"):
                    val = getattr(q, attr, None)
                    if val is not None:
                        out[f"Qto.{q.Name}"] = val
                        break
    return out


def material_associado(el):
    """Nome do material associado via IfcRelAssociatesMaterial (ou None)."""
    try:
        for rel in getattr(el, "HasAssociations", None) or []:
            if rel.is_a("IfcRelAssociatesMaterial"):
                m = rel.RelatingMaterial
                if m.is_a("IfcMaterial"):
                    return m.Name
                if m.is_a("IfcMaterialLayerSetUsage"):
                    return m.ForLayerSet.MaterialLayers[0].Material.Name
                if m.is_a("IfcMaterialLayerSet"):
                    return m.MaterialLayers[0].Material.Name
                if m.is_a("IfcMaterialList"):
                    return m.Materials[0].Name
    except Exception:
        pass
    return None


def _geometria(v: np.ndarray, fa: np.ndarray) -> tuple[float, float]:
    """(área das faces voltadas para cima em m², extensão do eixo principal em m)."""
    tri = v[fa]
    n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    norma = np.maximum(np.linalg.norm(n, axis=1), 1e-12)
    area = norma / 2
    topo = float(area[(n[:, 2] / norma) > 0.9].sum())
    c = v - v.mean(axis=0)
    _, _, vt = np.linalg.svd(c, full_matrices=False)
    proj = c @ vt[0]
    return topo, float(proj.max() - proj.min())


def _num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return np.nan


def extract(ifc_path: str, classes: dict | None = None):
    """Lê o IFC e devolve (df, V, F, pavimentos).

    df: uma linha por elemento (colunas canônicas + propriedades originais 'p:...').
    V: vértices (N, 3) em metros; F: faces (M, 3) com índices locais por elemento
    (v_off/v_n e f_off/f_n em df dão a fatia de cada elemento).
    pavimentos: nome, elevação (m) e nº de elementos de cada IfcBuildingStorey.
    """
    import ifcopenshell
    import ifcopenshell.geom
    import ifcopenshell.util.shape as ush
    import ifcopenshell.util.unit as uu

    classes = classes or CLASSES_IFC
    f = ifcopenshell.open(ifc_path)
    esc = uu.calculate_unit_scale(f)  # unidade do projeto -> metros
    cfg = ifcopenshell.geom.settings()
    cfg.set(cfg.USE_WORLD_COORDS, True)

    storeys = {s.id(): (s.Name, float(s.Elevation or 0) * esc) for s in f.by_type("IfcBuildingStorey")}
    contido = {}
    for r in f.by_type("IfcRelContainedInSpatialStructure"):
        if r.RelatingStructure.is_a("IfcBuildingStorey"):
            for e in r.RelatedElements:
                contido[e.id()] = storeys[r.RelatingStructure.id()]

    linhas, Vs, Fs = [], [], []
    vo = fo = 0
    for cls, rotulo in classes.items():
        for e in f.by_type(cls):
            p = propriedades(e)
            geo = ifcopenshell.geom.create_shape(cfg, e).geometry
            v = np.array(geo.verts, dtype=np.float32).reshape(-1, 3)
            fa = np.array(geo.faces, dtype=np.uint32).reshape(-1, 3)
            vol = float(ush.get_volume(geo))
            topo, ext = _geometria(v, fa)
            pav, elev = contido.get(e.id(), (None, np.nan))
            larg, alt = _num(p.get("TQS_Geometria.Largura")), _num(p.get("TQS_Geometria.Altura"))
            qvol = [val for k, val in p.items() if k.startswith("Qto.") and "volume" in k.lower()]
            if rotulo == "Vigas" and not np.isnan(larg) and not np.isnan(alt):
                secao = f"{larg:g}x{alt:g}"
            elif rotulo == "Pilares":
                partes = [p.get("TQS_Geometria.Secao")] + [p.get(f"TQS_Geometria.Dimensao_{k}") for k in ("b1", "h1", "b2", "h2")]
                secao = " ".join(f"{x:g}" if isinstance(x, float) else str(x) for x in partes if x is not None) or None
            else:
                secao = None
            linhas.append({
                "GlobalId": e.GlobalId, "classe_ifc": cls, "classe": rotulo, "nome": e.Name,
                "titulo": p.get("TQS_Padrao.Titulo") or e.Name,
                "pavimento": pav, "elevacao_m": elev,
                "material": p.get("TQS_Padrao.Material") or material_associado(e),
                "largura_cm": larg, "altura_cm": alt, "secao": secao,
                "tipo_tqs": p.get("TQS_Padrao.Tipo"), "planta_tqs": p.get("TQS_Padrao.Planta"),
                "cortina": p.get("TQS_Geometria.Cortina"),
                "vol_geom_m3": vol,
                "vol_ifc_m3": float(qvol[0]) if qvol else np.nan,
                "area_laje_m2": (_num(p.get("TQS_Geometria.Area_superficie")) if rotulo == "Lajes" else np.nan),
                "area_topo_geom_m2": topo if rotulo == "Lajes" else np.nan,
                "comprimento_geom_m": ext if rotulo == "Vigas" else np.nan,
                "v_off": vo, "v_n": len(v), "f_off": fo, "f_n": len(fa),
                **{f"p:{k}": val for k, val in p.items()},
            })
            Vs.append(v)
            Fs.append(fa)
            vo += len(v)
            fo += len(fa)

    df = pd.DataFrame(linhas)
    # Sem Area_superficie no IFC (ex.: Revit), usa a área das faces superiores.
    m = df.classe.eq("Lajes") & df.area_laje_m2.isna()
    df.loc[m, "area_laje_m2"] = df.loc[m, "area_topo_geom_m2"]
    pav = pd.DataFrame(list(storeys.values()), columns=["pavimento", "elevacao_m"]).sort_values("elevacao_m")
    pav["n_elementos"] = pav.pavimento.map(df.groupby("pavimento").size()).fillna(0).astype(int)
    V = np.concatenate(Vs) if Vs else np.zeros((0, 3), np.float32)
    F = np.concatenate(Fs) if Fs else np.zeros((0, 3), np.uint32)
    return df, V, F, pav.reset_index(drop=True)
