"""Dashboard BIM estrutural (IFC) — Streamlit.

Perguntas de negócio e KPIs: planilha dashboard_perguntas_kpis.xlsx.
Público: coordenador BIM e orçamentista.
"""
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from src import kpis as K
from src.data import carregar_padrao, ifcopenshell_disponivel, processar_ifc
from src.viewer3d import COR, figura_3d

RAIZ = Path(__file__).resolve().parent

st.set_page_config(page_title="Dashboard Estrutural BIM", page_icon="🏗️", layout="wide")

# ---------------------------------------------------------------- dados
df_all, V, F, pav_df, modelo = carregar_padrao()

with st.sidebar:
    st.header("Dados")
    if ifcopenshell_disponivel():
        up = st.file_uploader("Carregar outro IFC (opcional)", type=["ifc"])
        if up is not None:
            df_all, V, F, pav_df, modelo = processar_ifc(up.getvalue(), up.name)
    else:
        st.caption("Upload de IFC desativado (instale `requirements-ifc.txt` para habilitar).")
    st.caption(f"Modelo: **{modelo}**")
    st.header("Filtros")
    ordem_pav = list(pav_df.sort_values("elevacao_m").pavimento)
    sel_pav = st.multiselect("Pavimentos", ordem_pav, default=ordem_pav)
    sel_cls = st.multiselect("Classes", K.CLASSES, default=K.CLASSES)

mask = df_all.classe.isin(sel_cls)
if set(sel_pav) != set(ordem_pav):
    mask &= df_all.pavimento.isin(sel_pav)
df = df_all[mask]

st.title("Dashboard Estrutural BIM")
st.caption(
    f"{len(df):,} de {len(df_all):,} elementos · volumes calculados pela geometria do IFC · "
    "público: coordenador BIM e orçamentista".replace(",", ".")
)
if df.empty:
    st.warning("Nenhum elemento com os filtros atuais.")
    st.stop()

r = K.resumo(df)
aba_geral, aba_qual, aba_sec, aba_3d, aba_kpi, aba_cod, aba_dados = st.tabs(
    ["Visão geral", "Qualidade do modelo", "Seções e materiais", "Modelo 3D", "KPIs da planilha", "Código", "Dados"]
)

# ---------------------------------------------------------------- visão geral
with aba_geral:
    c = st.columns(6)
    c[0].metric("Elementos", K.fmt(r["n"], 0))
    c[1].metric("Volume de concreto (m³)", K.fmt(r["vol_total"]))
    c[2].metric("Área de laje (m²)", K.fmt(r["area_laje"]))
    c[3].metric("Espessura média de laje (cm)", K.fmt(r["esp_media_cm"]))
    c[4].metric("Concreto por m² de laje (m³/m²)", K.fmt(r["consumo_m3_m2"], 3))
    c[5].metric("Vigas sem seção", f"{K.fmt(r['pct_vigas_sem_secao'])}%", help="Vigas sem largura ou altura nas propriedades")
    c = st.columns(4)
    for col, cls in zip(c, K.CLASSES):
        col.metric(f"{cls}", f"{r['n_tipo'][cls]}", f"{K.fmt(r['vol_tipo'][cls])} m³ · {K.fmt(r['pct_tipo'].get(cls))}%", delta_color="off")
    c[3].metric("Comprimento de vigas (m)", K.fmt(r["comp_vigas_secao"], 0), f"{r['n_vigas_com_secao']} vigas com seção", delta_color="off")

    esq, dir_ = st.columns(2)
    por_tipo = pd.DataFrame({"classe": K.CLASSES, "volume": [r["vol_tipo"][k] for k in K.CLASSES], "pct": [r["pct_tipo"].get(k, 0) for k in K.CLASSES]})
    por_tipo["rotulo"] = por_tipo.apply(lambda x: f"{K.fmt(x.volume)} m³ ({K.fmt(x.pct)}%)", axis=1)
    fig = px.bar(por_tipo, x="classe", y="volume", color="classe", color_discrete_map=COR, text="rotulo", title="Volume de concreto por tipo (m³)")
    fig.update_layout(showlegend=False, xaxis_title=None, yaxis_title="m³")
    esq.plotly_chart(fig, width="stretch")

    g = df.groupby(["pavimento", "classe"]).agg(volume=("vol_geom_m3", "sum"), n=("GlobalId", "size")).reset_index()
    fig = px.bar(g, x="pavimento", y="volume", color="classe", color_discrete_map=COR,
                 category_orders={"pavimento": ordem_pav, "classe": K.CLASSES}, title="Volume por pavimento, empilhado por tipo (m³)")
    fig.update_layout(xaxis_title=None, yaxis_title="m³", legend_title=None)
    dir_.plotly_chart(fig, width="stretch")

    fig = px.bar(g, x="pavimento", y="n", color="classe", color_discrete_map=COR,
                 category_orders={"pavimento": ordem_pav, "classe": K.CLASSES}, title="Nº de elementos por pavimento")
    fig.update_layout(xaxis_title=None, yaxis_title="un", legend_title=None)
    st.plotly_chart(fig, width="stretch")

    st.subheader("Elementos por título")
    st.caption("Clique numa linha para destacar esses elementos na aba **Modelo 3D**.")
    tab = (df.assign(sem_secao=K.sem_secao(df).astype(int))
             .groupby(["classe", "titulo"], as_index=False)
             .agg(qtd=("GlobalId", "size"), volume_m3=("vol_geom_m3", "sum"), sem_secao=("sem_secao", "sum"))
             .sort_values("volume_m3", ascending=False).reset_index(drop=True))
    ev = st.dataframe(tab, hide_index=True, width="stretch", height=320, on_select="rerun", selection_mode="single-row",
                      key="tabela_titulos", column_config={"volume_m3": st.column_config.NumberColumn("volume (m³)", format="%.2f")})
    if ev.selection.rows:
        linha = tab.iloc[ev.selection.rows[0]]
        st.session_state["destaque"] = (linha.classe, linha.titulo)
    elif "tabela_titulos" in st.session_state and not st.session_state["tabela_titulos"]["selection"]["rows"]:
        st.session_state.pop("destaque", None)

# ---------------------------------------------------------------- qualidade
with aba_qual:
    st.caption("Pergunta 5 da planilha: os dados estão confiáveis? Onde estão as lacunas a corrigir no modelo?")
    c = st.columns(4)
    c[0].metric("Com material definido", f"{K.fmt(r['pct_material'])}%")
    c[1].metric("Sem pendências", f"{K.fmt(r['pct_sem_pendencia'])}%", help="Sem pendência de material, pavimento ou volume")
    c[2].metric("Sem pavimento / volume zero", f"{r['n_sem_pav']} / {r['n_vol_zero']}")
    c[3].metric("Nome fora do padrão / classe IFC errada", f"{r['n_nome_fora']} / {r['n_classe_errada']}")
    st.metric("Diferença volume geométrico × volume do IFC", f"{K.fmt(r['dif_vol_pct'], 2)}%" if r["dif_vol_pct"] == r["dif_vol_pct"] else "n/d (o IFC não traz quantidades)")
    vazios = pav_df[pav_df.n_elementos == 0].pavimento.tolist()
    if vazios:
        st.warning(f"Pavimentos existentes no IFC sem nenhum elemento estrutural: {', '.join(vazios)}.")

    vigas = df[df.classe == "Vigas"]
    crit = pd.DataFrame({
        "critério": ["Material definido", "Pavimento definido", "Volume maior que zero", "Nome no padrão", "Classe IFC coerente", "Vigas com largura e altura"],
        "% atendido": [
            df.material.notna().mean() * 100, df.pavimento.notna().mean() * 100, (df.vol_geom_m3.fillna(0) > 0).mean() * 100,
            (1 - r["n_nome_fora"] / len(df)) * 100, (1 - r["n_classe_errada"] / len(df)) * 100,
            (100 - r["pct_vigas_sem_secao"]) if len(vigas) else float("nan"),
        ],
    })
    fig = px.bar(crit, x="% atendido", y="critério", orientation="h", range_x=[0, 100], title="Completude por critério (%)", text="% atendido")
    fig.update_traces(texttemplate="%{text:.1f}%", marker_color="#2f5bea")
    fig.update_layout(yaxis_title=None, yaxis=dict(autorange="reversed"))
    st.plotly_chart(fig, width="stretch")

    pend = K.pendencias(df)
    st.subheader(f"Tabela de pendências ({len(pend)})")
    if pend.empty:
        st.success("Nenhuma pendência encontrada.")
    else:
        resumo_p = pend.groupby("pendencia").size().rename("elementos").reset_index()
        st.dataframe(resumo_p, hide_index=True, width="stretch")
        st.dataframe(pend, hide_index=True, width="stretch", height=320)
        st.download_button("Baixar pendências (CSV)", pend.to_csv(index=False).encode("utf-8-sig"), "pendencias.csv", "text/csv")

# ---------------------------------------------------------------- seções e materiais
with aba_sec:
    st.caption("Pergunta 4 da planilha (opcional): quais seções e materiais são usados? Muita variedade indica projeto pouco padronizado.")
    c = st.columns(3)
    c[0].metric("Seções distintas de vigas", r["secoes_vigas"])
    c[1].metric("Seções distintas de pilares", r["secoes_pilares"])
    c[2].metric("Classes de concreto", len(r["fck"]))
    fck = pd.DataFrame({"classe de concreto": list(r["fck"]), "% dos elementos": list(r["fck"].values())})
    fig = px.bar(fck, x="classe de concreto", y="% dos elementos", range_y=[0, 100], title="Distribuição por classe de concreto (%)")
    st.plotly_chart(fig, width="stretch")
    sec = (df.dropna(subset=["secao"]).groupby(["classe", "secao"]).agg(qtd=("GlobalId", "size"), volume_m3=("vol_geom_m3", "sum"))
             .reset_index().sort_values("volume_m3", ascending=False))
    st.dataframe(sec, hide_index=True, width="stretch", column_config={"volume_m3": st.column_config.NumberColumn("volume (m³)", format="%.2f")})
    st.caption("Vigas sem largura/altura não entram na contagem de seções; ver aba Qualidade do modelo.")

# ---------------------------------------------------------------- 3D
with aba_3d:
    destaque = st.session_state.get("destaque")
    opcoes = ["(nenhum)"] + [f"{a} · {b}" for a, b in df[["classe", "titulo"]].drop_duplicates().sort_values(["classe", "titulo"]).itertuples(index=False)]
    padrao = 0
    if destaque and f"{destaque[0]} · {destaque[1]}" in opcoes:
        padrao = opcoes.index(f"{destaque[0]} · {destaque[1]}")
    c1, c2, c3 = st.columns([2, 1, 1])
    escolha = c1.selectbox("Destacar elementos do título", opcoes, index=padrao, key=f"destaque_sel_{padrao}")
    ver_sem_secao = c2.checkbox("Vigas sem seção em vermelho", value=False)
    fantasma = c3.checkbox("Mostrar demais elementos esmaecidos", value=True)
    dest = None if escolha == "(nenhum)" else tuple(escolha.split(" · ", 1))
    if dest:
        n_hit = int(((df.classe == dest[0]) & (df.titulo == dest[1])).sum())
        v_hit = df[(df.classe == dest[0]) & (df.titulo == dest[1])].vol_geom_m3.sum()
        st.info(f"{dest[1]} ({dest[0]}): {n_hit} elemento(s), {K.fmt(v_hit, 2)} m³ em destaque.")
    st.plotly_chart(figura_3d(df, V, F, df_todos=df_all, destaque=dest, destacar_sem_secao=ver_sem_secao, fantasma=fantasma), width="stretch")
    st.caption("Arraste para girar, Shift + arraste para mover e roda para zoom. Passe o mouse para ver título, classe, pavimento e volume.")

# ---------------------------------------------------------------- KPIs da planilha
with aba_kpi:
    st.caption("Os 16 KPIs da planilha dashboard_perguntas_kpis.xlsx, calculados sobre os elementos filtrados.")
    tk = K.tabela_kpis(df)
    st.dataframe(tk, hide_index=True, width="stretch", height=640)
    st.download_button("Baixar KPIs (CSV)", tk.to_csv(index=False).encode("utf-8-sig"), "kpis.csv", "text/csv")

# ---------------------------------------------------------------- código
with aba_cod:
    arquivos = sorted([RAIZ / "app.py", *(RAIZ / "src").glob("*.py"), *(RAIZ / "scripts").glob("*.py"), *(RAIZ / "scripts" / "relatorio").glob("*.py")])
    arquivos = [a for a in arquivos if a.name != "__init__.py"]
    nomes = [str(a.relative_to(RAIZ)) for a in arquivos]
    esc = st.selectbox("Arquivo", nomes)
    st.code((RAIZ / esc).read_text(encoding="utf-8"), language="python", line_numbers=True)

# ---------------------------------------------------------------- dados
with aba_dados:
    base = [c for c in df.columns if not c.startswith("p:")]
    st.dataframe(df[base], hide_index=True, width="stretch", height=520)
    st.download_button("Baixar elementos (CSV)", df[base].to_csv(index=False).encode("utf-8-sig"), "elementos.csv", "text/csv")
