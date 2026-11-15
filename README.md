# Dashboard Estrutural BIM (IFC) — Streamlit

Dashboard interativo que lê um modelo estrutural em IFC (exportado do TQS) e responde às perguntas de negócio da planilha `dashboard_perguntas_kpis.xlsx`, para o **coordenador BIM** e o **orçamentista**.
Trabalho em grupo do Módulo 7, Tema 2 (Zigurat): IA aplicada à visualização de dados.

## O que o app mostra

| Aba | Conteúdo |
| --- | --- |
| Visão geral | Elementos, volume, área de laje, espessura média, m³/m², % por tipo, volume e nº de elementos por pavimento, tabela por título (clique numa linha para destacá-la no 3D) |
| Qualidade do modelo | Completude, pendências (com download em CSV), pavimentos sem elementos, vigas sem seção |
| Seções e materiais | Seções distintas e distribuição por classe de concreto |
| Modelo 3D | Geometria extraída do IFC, filtros, destaque por título e vigas sem seção em vermelho |
| KPIs da planilha | Os 16 KPIs da planilha com o valor calculado |
| Código / Dados | Viewer do código-fonte e tabela de elementos |

## Estrutura

```
app.py                      # app Streamlit
src/ifc_pipeline.py         # IFC -> tabela + malhas 3D (ifcopenshell)
src/kpis.py                 # KPIs da planilha
src/viewer3d.py             # figura 3D (Plotly)
src/data.py                 # carregamento dos dados e upload opcional de IFC
data/                       # dados pré-extraídos (o app lê daqui)
scripts/build_data.py       # regenera data/ a partir de um IFC
scripts/relatorio/          # scripts exatamente como registrados no relatório
tests/                      # pytest (KPIs, malhas e execução do app)
.github/workflows/ci.yml    # testes automáticos no GitHub
```

O app **não precisa do ifcopenshell** para rodar: ele lê `data/`. O ifcopenshell só é necessário para regenerar os dados ou para habilitar o upload de IFC.

## Rodar localmente

```bash
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

Testes: `pip install -r requirements-dev.txt && pytest -q`

## Publicar no GitHub

```bash
git init
git add .
git commit -m "Dashboard estrutural BIM (IFC) em Streamlit"
git branch -M main
git remote add origin https://github.com/<usuario>/<repositorio>.git
git push -u origin main
```

Antes de publicar, decidam se o repositório será **público ou privado**: `data/` contém nomes, pavimentos e geometria do projeto. Se o modelo for confidencial, usem repositório privado ou dados anonimizados.

## Publicar no Streamlit Community Cloud

1. Acesse https://share.streamlit.io e entre com a conta do GitHub (autorize o acesso ao repositório, inclusive se for privado).
2. Clique em **Create app** e escolha **Deploy a public GitHub repo** (ou o repositório privado).
3. Preencha: Repository `<usuario>/<repositorio>`, Branch `main`, Main file path `app.py`.
4. Em **Advanced settings**, escolha Python 3.12.
5. Clique em **Deploy**. O link público do app aparece quando o build termina, e cada `git push` atualiza o app.

O `requirements.txt` não inclui o ifcopenshell, então o build é leve e o upload de IFC fica desativado na nuvem. Para habilitá-lo, troque o conteúdo de `requirements.txt` por `-r requirements-ifc.txt` (ou copie a linha do ifcopenshell para ele) e confira se o build passa.

## Atualizar os dados com outro IFC

```bash
pip install -r requirements-ifc.txt
python scripts/build_data.py ifc/NOVO_MODELO.ifc
git add data && git commit -m "Atualiza dados do modelo" && git push
```

O IFC original fica fora do Git (`.gitignore`). A nomenclatura de propriedades segue o export do TQS (`TQS_Padrao`, `TQS_Geometria`); para IFC de outro software, o pipeline cai para nome do elemento, material associado, quantidades `Qto.*` e geometria, mas os KPIs de seção e de padrão de nome (`NOME_PADRAO` em `src/kpis.py`) podem precisar de ajuste.

## Limitações

- Volumes vêm da geometria do IFC (o arquivo não traz quantidades); validem contra o quantitativo do projeto estrutural antes de usar em orçamento.
- 114 vigas (22,9%) não têm largura e altura nas propriedades.
- O modelo é estrutural, em concreto C25, sem custos nem cronograma.
