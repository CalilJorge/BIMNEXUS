import sys
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from src import kpis as K  # noqa: E402


def df():
    return pd.read_csv(RAIZ / "data" / "elementos.csv")


def test_contagens_e_volumes():
    r = K.resumo(df())
    assert r["n"] == 838
    assert r["n_tipo"] == {"Vigas": 497, "Pilares": 184, "Lajes": 157}
    assert round(r["vol_total"], 1) == 1041.2
    assert round(r["area_laje"], 1) == 1807.0
    assert round(r["esp_media_cm"], 1) == 15.0
    assert r["n_vigas_sem_secao"] == 114


def test_qualidade():
    r = K.resumo(df())
    assert r["pct_material"] == 100
    assert (r["n_sem_pav"], r["n_vol_zero"], r["n_nome_fora"], r["n_classe_errada"]) == (0, 0, 0, 0)
    tk = K.tabela_kpis(df())
    assert (tk.Pergunta != 'extra').sum() == 16 and len(tk) == 17


def test_malhas_consistentes():
    import numpy as np

    d = df()
    z = np.load(RAIZ / "data" / "malhas.npz")
    assert d.v_n.sum() == len(z["V"]) and d.f_n.sum() == len(z["F"])


def test_app_roda_sem_erros():
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(RAIZ / "app.py"), default_timeout=120).run()
    assert not at.exception
    assert len(at.tabs) == 7
