"""KPIs da planilha dashboard_perguntas_kpis.xlsx calculados sobre o DataFrame de elementos."""
from __future__ import annotations

import re

import numpy as np
import pandas as pd

CLASSES = ["Vigas", "Pilares", "Lajes"]
# Padrão de nomenclatura do TQS: letra do tipo + número (V12, P5, L3). Ajuste para outros projetos.
NOME_PADRAO = re.compile(r"^[VPL]\d+$")


def fmt(x, casas: int = 1) -> str:
    """Número no padrão brasileiro (1.234,5)."""
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "n/d"
    s = f"{x:,.{casas}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def sem_secao(df: pd.DataFrame) -> pd.Series:
    """Vigas sem largura ou altura definidas."""
    return df.classe.eq("Vigas") & (df.largura_cm.isna() | df.altura_cm.isna())


def pendencias(df: pd.DataFrame) -> pd.DataFrame:
    """Uma linha por (elemento, problema). Vazio quando o modelo não tem pendências."""
    problemas = {
        "Material não definido": df.material.isna(),
        "Sem pavimento": df.pavimento.isna(),
        "Volume zero ou ausente": df.vol_geom_m3.fillna(0) <= 0,
        "Nome fora do padrão": ~df.nome.fillna("").str.match(NOME_PADRAO),
        "Classe IFC diferente do tipo TQS": df.tipo_tqs.notna() & (df.classe != df.tipo_tqs),
        "Viga sem largura/altura": sem_secao(df),
    }
    partes = []
    for nome, mask in problemas.items():
        if mask.any():
            t = df.loc[mask, ["GlobalId", "classe", "titulo", "pavimento"]].copy()
            t["pendencia"] = nome
            partes.append(t)
    cols = ["GlobalId", "classe", "titulo", "pavimento", "pendencia"]
    return pd.concat(partes, ignore_index=True)[cols] if partes else pd.DataFrame(columns=cols)


def resumo(df: pd.DataFrame) -> dict:
    """Valores numéricos usados nos cartões e nos gráficos."""
    n = len(df)
    vol = df.vol_geom_m3.sum()
    lajes = df[df.classe == "Lajes"]
    vigas = df[df.classe == "Vigas"]
    area = lajes.area_laje_m2.sum()
    com_secao = vigas[vigas.largura_cm.notna() & vigas.altura_cm.notna()]
    comp_secao = (com_secao.vol_geom_m3 / (com_secao.largura_cm * com_secao.altura_cm / 1e4)).sum()
    pend = pendencias(df)
    bloqueantes = pend[pend.pendencia.isin(["Material não definido", "Sem pavimento", "Volume zero ou ausente"])]
    com_qto = df.vol_ifc_m3.notna()
    dif_vol = (
        (df.loc[com_qto, "vol_geom_m3"].sum() - df.loc[com_qto, "vol_ifc_m3"].sum()) / df.loc[com_qto, "vol_ifc_m3"].sum() * 100
        if com_qto.any() else np.nan
    )
    return {
        "n": n,
        "n_tipo": df.classe.value_counts().reindex(CLASSES).fillna(0).astype(int).to_dict(),
        "n_pilar_parede": int((df.classe.eq("Pilares") & df.cortina.eq("Sim")).sum()),
        "vol_total": vol,
        "vol_tipo": df.groupby("classe").vol_geom_m3.sum().reindex(CLASSES).fillna(0).to_dict(),
        "pct_tipo": (df.groupby("classe").vol_geom_m3.sum().reindex(CLASSES).fillna(0) / vol * 100).to_dict() if vol else {},
        "area_laje": area,
        "esp_media_cm": lajes.vol_geom_m3.sum() / area * 100 if area else np.nan,
        "consumo_m3_m2": vol / area if area else np.nan,
        "comp_vigas_secao": comp_secao,
        "n_vigas_com_secao": len(com_secao),
        "comp_vigas_geom": vigas.comprimento_geom_m.sum(),
        "n_vigas_sem_secao": int(sem_secao(df).sum()),
        "pct_vigas_sem_secao": sem_secao(df).sum() / len(vigas) * 100 if len(vigas) else np.nan,
        "secoes_vigas": com_secao.secao.nunique(),
        "secoes_pilares": df.loc[df.classe == "Pilares", "secao"].nunique(),
        "fck": (df.material.fillna("Não definido").value_counts() / n * 100).to_dict() if n else {},
        "pct_material": df.material.notna().mean() * 100 if n else np.nan,
        "pct_sem_pendencia": (1 - bloqueantes.GlobalId.nunique() / n) * 100 if n else np.nan,
        "n_sem_pav": int(df.pavimento.isna().sum()),
        "n_vol_zero": int((df.vol_geom_m3.fillna(0) <= 0).sum()),
        "n_nome_fora": int((~df.nome.fillna("").str.match(NOME_PADRAO)).sum()),
        "n_classe_errada": int((df.tipo_tqs.notna() & (df.classe != df.tipo_tqs)).sum()),
        "dif_vol_pct": dif_vol,
    }


def tabela_kpis(df: pd.DataFrame) -> pd.DataFrame:
    """Os 16 KPIs da planilha (mais o extra do grupo) com valor calculado."""
    r = resumo(df)
    nt, vt = r["n_tipo"], r["vol_tipo"]
    pt = r["pct_tipo"]
    linhas = [
        (1, "Nº de elementos por tipo", "un", f"{r['n']} no total: {nt['Vigas']} vigas, {nt['Pilares']} pilares, {nt['Lajes']} lajes, {r['n_pilar_parede']} pilares-parede"),
        (1, "Volume de concreto total e por tipo", "m³", f"{fmt(r['vol_total'])} total: vigas {fmt(vt['Vigas'])}; pilares {fmt(vt['Pilares'])}; lajes {fmt(vt['Lajes'])}"),
        (1, "Área de laje", "m²", fmt(r["area_laje"])),
        (1, "Comprimento de vigas", "m", f"{fmt(r['comp_vigas_secao'], 0)} (volume ÷ seção, {r['n_vigas_com_secao']} vigas com seção); {fmt(r['comp_vigas_geom'], 0)} pela geometria (todas as vigas)"),
        (2, "Volume por pavimento", "m³", "Gráfico empilhado por tipo (aba Visão geral)"),
        (2, "Nº de elementos por pavimento", "un", "Gráfico por pavimento (aba Visão geral)"),
        (3, "Espessura média de laje", "cm", fmt(r["esp_media_cm"])),
        (3, "Consumo de concreto por m² de laje", "m³/m²", fmt(r["consumo_m3_m2"], 3)),
        (3, "% do volume por tipo de elemento", "%", f"vigas {fmt(pt.get('Vigas'))}; pilares {fmt(pt.get('Pilares'))}; lajes {fmt(pt.get('Lajes'))}"),
        (4, "Nº de seções distintas de vigas e pilares", "un", f"vigas {r['secoes_vigas']}; pilares {r['secoes_pilares']}"),
        (4, "Distribuição por classe de concreto (fck)", "%", "; ".join(f"{k} {fmt(v)}" for k, v in r["fck"].items())),
        (5, "% de elementos com material definido", "%", fmt(r["pct_material"])),
        (5, "% de elementos sem pendências (material, pavimento, volume)", "%", fmt(r["pct_sem_pendencia"])),
        (5, "Elementos sem pavimento ou sem volume", "un", f"{r['n_sem_pav']} sem pavimento; {r['n_vol_zero']} sem volume"),
        (5, "Nomes fora do padrão; classe IFC errada", "un", f"{r['n_nome_fora']} e {r['n_classe_errada']}"),
        (5, "Diferença entre volume do IFC e volume geométrico", "%", fmt(r["dif_vol_pct"], 2) if not np.isnan(r["dif_vol_pct"]) else "n/d: o IFC não traz quantidades"),
        ("extra", "Vigas sem largura/altura", "un e %", f"{r['n_vigas_sem_secao']} ({fmt(r['pct_vigas_sem_secao'])}%)"),
    ]
    return pd.DataFrame(linhas, columns=["Pergunta", "KPI", "Unidade", "Valor neste modelo"]).astype({"Pergunta": str})
