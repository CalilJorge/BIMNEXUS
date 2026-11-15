"""Gera data/elementos.csv, data/malhas.npz e data/pavimentos.csv a partir de um IFC.

    pip install -r requirements-ifc.txt
    python scripts/build_data.py ifc/EAN-BNX-XX-XX-M3D-CON-0001-P01.ifc
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.ifc_pipeline import extract  # noqa: E402

if len(sys.argv) < 2:
    sys.exit(__doc__)
data = Path(__file__).resolve().parent.parent / "data"
data.mkdir(exist_ok=True)
df, V, F, pav = extract(sys.argv[1])
df.to_csv(data / "elementos.csv", index=False)
pav.to_csv(data / "pavimentos.csv", index=False)
np.savez_compressed(data / "malhas.npz", V=V, F=F)
(data / "modelo.txt").write_text(Path(sys.argv[1]).name, encoding="utf-8")
print(f"{len(df)} elementos, {len(V)} vértices, {len(F)} triângulos -> {data}")
