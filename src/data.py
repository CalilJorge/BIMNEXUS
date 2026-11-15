"""Carregamento dos dados pré-extraídos e processamento opcional de um IFC enviado."""
from __future__ import annotations

import importlib.util
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

DATA = Path(__file__).resolve().parent.parent / "data"


def ifcopenshell_disponivel() -> bool:
    return importlib.util.find_spec("ifcopenshell") is not None


@st.cache_data(show_spinner=False)
def carregar_padrao():
    df = pd.read_csv(DATA / "elementos.csv")
    z = np.load(DATA / "malhas.npz")
    pav = pd.read_csv(DATA / "pavimentos.csv")
    nome = (DATA / "modelo.txt").read_text(encoding="utf-8").strip() if (DATA / "modelo.txt").exists() else "modelo"
    return df, z["V"], z["F"], pav, nome


@st.cache_data(show_spinner="Lendo o IFC e extraindo geometria...")
def processar_ifc(conteudo: bytes, nome: str):
    from .ifc_pipeline import extract

    with tempfile.NamedTemporaryFile(suffix=".ifc", delete=False) as tmp:
        tmp.write(conteudo)
        caminho = tmp.name
    try:
        df, V, F, pav = extract(caminho)
    finally:
        Path(caminho).unlink(missing_ok=True)
    return df, V, F, pav, nome
