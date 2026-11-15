"""Viewer 3D (Plotly Mesh3d) a partir das malhas extraídas do IFC."""
from __future__ import annotations

import numpy as np
import plotly.graph_objects as go

COR = {"Vigas": "#2f5bea", "Pilares": "#e0663a", "Lajes": "#2fa57a"}
COR_SEM_SECAO = "#d6362f"
COR_DESTAQUE = "#ffc400"
COR_FANTASMA = "#8a93a6"


def _juntar(sub, V, F):
    if sub.empty:
        return None
    vs, fs, rot, off = [], [], [], 0
    for r in sub.itertuples():
        v = V[r.v_off : r.v_off + r.v_n]
        vs.append(v)
        fs.append(F[r.f_off : r.f_off + r.f_n].astype(np.int64) + off)
        rot.append(np.full(r.v_n, f"{r.titulo} · {r.classe} · {r.pavimento} · {r.vol_geom_m3:.2f} m³", dtype=object))
        off += len(v)
    return np.concatenate(vs), np.concatenate(fs), np.concatenate(rot)


def _trace(m, nome, cor, opacidade=1.0, hover=True):
    v, f, rot = m
    return go.Mesh3d(
        x=v[:, 0], y=v[:, 1], z=v[:, 2], i=f[:, 0], j=f[:, 1], k=f[:, 2],
        color=cor, opacity=opacidade, flatshading=True, name=nome, showlegend=True,
        hovertext=rot if hover else None, hoverinfo="text" if hover else "skip",
        lighting=dict(ambient=0.55, diffuse=0.85, specular=0.05),
    )


def figura_3d(df, V, F, df_todos=None, destaque=None, destacar_sem_secao=False, fantasma=True):
    """df: elementos visíveis; df_todos: todos (para esmaecer os não filtrados);
    destaque: (classe, titulo) a pintar de amarelo."""
    from .kpis import sem_secao

    fig = go.Figure()
    ativo = df.copy()
    if destaque:
        hit = (ativo.classe == destaque[0]) & (ativo.titulo == destaque[1])
    else:
        hit = ativo.classe.eq("__nenhum__")
    ss = sem_secao(ativo) if destacar_sem_secao else ativo.classe.eq("__nenhum__")

    if fantasma and df_todos is not None:
        fora = df_todos[~df_todos.GlobalId.isin(ativo.GlobalId)]
        m = _juntar(fora, V, F)
        if m:
            fig.add_trace(_trace(m, "Demais elementos", COR_FANTASMA, 0.08, hover=False))
    for cls, cor in COR.items():
        sub = ativo[(ativo.classe == cls) & ~hit & ~ss]
        m = _juntar(sub, V, F)
        if m:
            fig.add_trace(_trace(m, cls, cor, 0.25 if destaque else 1.0))
    m = _juntar(ativo[ss & ~hit], V, F)
    if m:
        fig.add_trace(_trace(m, "Viga sem seção", COR_SEM_SECAO))
    m = _juntar(ativo[hit], V, F)
    if m:
        fig.add_trace(_trace(m, f"Selecionado: {destaque[1]}", COR_DESTAQUE))
    fig.update_layout(
        height=680, margin=dict(l=0, r=0, t=0, b=0),
        scene=dict(aspectmode="data", xaxis=dict(visible=False), yaxis=dict(visible=False), zaxis=dict(title="Z (m)")),
        legend=dict(orientation="h", y=1.02),
    )
    return fig
