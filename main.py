# backend/main.py
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
import uvicorn
import pandas as pd
from data_loader import carregar_dados
from calculos import (
    calcular_distribuicao_fraturas,
    calcular_p21_por_camada,
    calcular_abertura_stats,
    calcular_tamanho_stats,
    calcular_espessura_abertura,
    calcular_estereograma,
    calcular_scanlines,
    calcular_ji2002,
)

app = FastAPI(title="Dashboard Fraturas API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="../static"),   name="static")
app.mount("/app",    StaticFiles(directory="../frontend", html=True), name="frontend")

# --- Carrega dados na inicialização ---
df, df_juntas, df_veios, df_veios_confinados = carregar_dados(
    "../dados/1a_2a_3a_4a_6a_Etapas_24_08_CONSISTIDO.csv"
)

# ----------------------------------------------------------------------
# RAIZ
# ----------------------------------------------------------------------
@app.get("/")
def root():
    return RedirectResponse(url="/app/index.html")

# ----------------------------------------------------------------------
# Metadados para dropdowns
# ----------------------------------------------------------------------
@app.get("/api/opcoes")
def opcoes():
    import pandas as pd

    afloramentos_ordem = [
        'VINUALES', 'PONTE', 'HOTEL_DEL_DIQUE', 'CEDAMAVI', 'CEDAMAVI_ESP',
        'ZORRO', 'LALULA', 'GAUCHITO_GIL', 'LOMITO', 'ABLOME_ESP', 'ABLOME',
        'ABLOME_COSTAS', 'BIV', 'DIQUE_COMPENSADOR', 'BODEGUITA'
    ]
    camadas_ordem = [
        'BEIRA_MAR_INFERIOR', 'FILHOTE', 'BEIRA_LAGO', 'BEIRA_RIO',
        'PELE_4', 'PELE_3', 'PELE_2', 'PELE_1', 'ISOLADA',
        'MARIA_SUPERIOR', 'MARIA_MEDIA', 'MARIA_INFERIOR',
        'MARADONA', 'LEIOLITO', 'UFC_Carbonato',
        'PLANAR', 'COLCHETE', 'GRETA_II', 'GRETA_I',
        'DUMOUND', 'MRG_AT_Gerson',
        'SIM1','SIM2','SIM3','SIM4',
        'SRM1','SRM2','SRM3','SRM4','SRM5','SRM6','SRM7'
    ]

    litofacies = ['Todas as Litofacies', 'LMC+LMT+MUD']
    if 'Litofacies' in df_veios_confinados.columns:
        extras = sorted(df_veios_confinados['Litofacies'].dropna().unique().tolist())
        litofacies += extras

    afls = ['Todos']
    afls += [a for a in afloramentos_ordem
             if a in df['Afloramento'].dropna().unique()]

    camadas_opcoes = ['Todas as Camadas']
    if 'Camada' in df.columns:
        camadas_unicas = df['Camada'].dropna().unique().tolist()
        camadas_ordenadas     = [c for c in camadas_ordem if c in camadas_unicas]
        camadas_nao_ordenadas = sorted(set(camadas_unicas) - set(camadas_ordem))
        camadas_opcoes += camadas_ordenadas + camadas_nao_ordenadas

    return {
        "afloramentos": afls,
        "camadas":      camadas_opcoes,
        "litofacies":   litofacies,
    }

# ----------------------------------------------------------------------
# Afloramentos (mapa)
# ----------------------------------------------------------------------
@app.get("/api/afloramentos")
def api_afloramentos():
    import pandas as pd
    import os

    possiveis = [
        "../static/mapas/Puntos2024.csv",
        "../static/mapas/Pontos2024.csv",
        "../static/mapas/puntos2024.csv",
        "../static/mapas/pontos2024.csv",
    ]

    caminho = None
    for p in possiveis:
        if os.path.exists(p):
            caminho = p
            break

    if caminho is None:
        pasta = "../static/mapas"
        arquivos = os.listdir(pasta) if os.path.exists(pasta) else ["PASTA NÃO ENCONTRADA"]
        return {"erro": f"CSV não encontrado. Arquivos em static/mapas: {arquivos}"}

    df_map = None
    for enc in ['utf-8', 'latin1', 'windows-1252']:
        for sep in [',', ';', '\t']:
            try:
                tmp = pd.read_csv(caminho, encoding=enc, sep=sep)
                if tmp.shape[1] > 1:
                    df_map = tmp
                    break
            except Exception:
                continue
        if df_map is not None:
            break

    if df_map is None:
        return {"erro": "Não foi possível ler o arquivo CSV."}

    colunas = {c.strip().lower(): c for c in df_map.columns}
    col_x    = colunas.get('x')    or colunas.get('longitude') or colunas.get('lon')
    col_y    = colunas.get('y')    or colunas.get('latitude')  or colunas.get('lat')
    col_name = colunas.get('name') or colunas.get('nome')      or colunas.get('afloramento')

    if not all([col_x, col_y, col_name]):
        return {"erro": f"Colunas não encontradas. Disponíveis: {list(df_map.columns)}"}

    df_map[col_x] = pd.to_numeric(df_map[col_x], errors='coerce')
    df_map[col_y] = pd.to_numeric(df_map[col_y], errors='coerce')
    df_map = df_map.dropna(subset=[col_x, col_y])

    return [
        {"X": float(r[col_x]), "Y": float(r[col_y]), "Name": str(r[col_name])}
        for _, r in df_map.iterrows()
    ]

# ----------------------------------------------------------------------
# Endpoints de dados
# ----------------------------------------------------------------------
@app.get("/api/distribuicao")
def api_distribuicao():
    return calcular_distribuicao_fraturas(df)

@app.get("/api/p21")
def api_p21(afloramento: str = Query("VINUALES")):
    return calcular_p21_por_camada(df, afloramento)

@app.get("/api/aberturas")
def api_aberturas(
    litofacies: str = Query("Todas as Litofacies"),
    camada:     str = Query("Todas as Camadas"),
):
    return calcular_abertura_stats(df_veios_confinados, litofacies, camada)

@app.get("/api/tamanhos")
def api_tamanhos(
    litofacies: str = Query("Todas as Litofacies"),
    camada:     str = Query("Todas as Camadas"),
):
    return calcular_tamanho_stats(df_veios_confinados, litofacies, camada)

@app.get("/api/espessura-abertura")
def api_espessura_abertura(litofacies: str = Query("Todas as Litofacies")):
    return calcular_espessura_abertura(df_veios_confinados, litofacies)

@app.get("/api/estereograma")
def api_estereograma(
    afloramento: str = Query("Todos"),
    camada:      str = Query("Todas as Camadas"),
):
    import matplotlib
    matplotlib.use("Agg")
    import io, base64
    from graficos import plotar_estereograma_e_rose

    fig = plotar_estereograma_e_rose(df_juntas, df_veios, afloramento, camada)

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=100, bbox_inches="tight")
    import matplotlib.pyplot as plt
    plt.close(fig)
    buf.seek(0)
    img_b64 = base64.b64encode(buf.read()).decode("utf-8")

    return {"imagem": img_b64}

@app.get("/api/estereograma/camadas")
def api_estereograma_camadas(afloramento: str = Query("Todos")):
    camadas_ordem = [
        'BEIRA_MAR_INFERIOR', 'FILHOTE', 'BEIRA_LAGO', 'BEIRA_RIO',
        'PELE_4', 'PELE_3', 'PELE_2', 'PELE_1', 'ISOLADA',
        'MARIA_SUPERIOR', 'MARIA_MEDIA', 'MARIA_INFERIOR',
        'MARADONA', 'LEIOLITO', 'UFC_Carbonato',
        'PLANAR', 'COLCHETE', 'GRETA_II', 'GRETA_I',
        'DUMOUND', 'MRG_AT_Gerson',
        'SIM1','SIM2','SIM3','SIM4',
        'SRM1','SRM2','SRM3','SRM4','SRM5','SRM6','SRM7'
    ]

    def filtrar(dataframe, afl):
        if dataframe is None or dataframe.empty:
            return []
        if 'Afloramento' not in dataframe.columns or 'Camada' not in dataframe.columns:
            return []
        if afl == "Todos":
            return dataframe['Camada'].dropna().unique().tolist()
        return dataframe[dataframe['Afloramento'] == afl]['Camada'].dropna().unique().tolist()

    c_juntas = filtrar(df_juntas, afloramento)
    c_veios  = filtrar(df_veios,  afloramento)
    todas    = set(c_juntas + c_veios)

    # Ordena respeitando a ordem definida, coloca o resto em ordem alfabética no final
    ordenadas     = [c for c in camadas_ordem if c in todas]
    nao_ordenadas = sorted(todas - set(camadas_ordem))

    return {"camadas": ordenadas + nao_ordenadas}

# ── Dados da scanline para o canvas (formato que o JS espera) ─────────────────
@app.get("/api/scanlines")
def api_scanlines(
    afloramento: str = Query(...),
    camada:      str = Query(...)
):
    """Retorna os dados estruturados de uma scanline para renderização no canvas."""

    df_sel = df[
        (df['Afloramento'] == afloramento) &
        (df['Camada']      == camada)
    ].copy()

    if df_sel.empty:
        return {"erro": f"Nenhum dado para {afloramento} / {camada}"}

    # Converte colunas numéricas
    for col in ['Espacamento', 'Surf Dir', 'DipDir', 'Altura da estrutura',
                'Espessura da camada']:
        if col in df_sel.columns:
            df_sel[col] = pd.to_numeric(df_sel[col], errors='coerce')

    # Surf Dir — mesmo cálculo do graficos.py:
    # scan_rad = deg2rad((90 - surf_dir) % 360)
    surf_dir_vals = df_sel['Surf Dir'].dropna()
    surf_dir      = float(surf_dir_vals.iloc[0]) if not surf_dir_vals.empty else 0.0

    # Comprimento total
    comprimento = float(df_sel['Espacamento'].sum())
    if comprimento == 0:
        return {"erro": "Comprimento da scanline é zero."}

    # Espessura da camada
    if 'Espessura da camada' in df_sel.columns:
        esp_vals = df_sel['Espessura da camada'].dropna()
        espessura_camada = float(esp_vals.iloc[0]) if not esp_vals.empty else 0.0
    else:
        espessura_camada = 0.0

    # ── Normaliza o FRAT SET igual ao graficos.py ─────────────────────────
    # Mapa espelho do dicionário cores_frat do graficos.py
    FRAT_SET_NORMALIZADO = {
        'nao subordinada':  'Nao subordinada',
        'não subordinada':  'Nao subordinada',
        'nao observada':    'Nao observada',
        'não observada':    'Nao observada',
        'subordinada':      'Subordinada',
        'set3':             'SET3',
        'set4':             'SET4',
        'set6':             'SET6',
        'set7':             'SET7',
        'set8':             'SET8',
        'set9':             'SET9',
        'set10':            'SET10',
        'nan':              'NaN',
    }

    def normalizar(valor):
        if pd.isna(valor):
            return 'NaN'
        s = str(valor).strip()
        chave = (s.lower()
                  .replace('ã', 'a')
                  .replace('á', 'a')
                  .replace('â', 'a')
                  .replace('é', 'e')
                  .replace('ê', 'e')
                  .replace('í', 'i')
                  .replace('ó', 'o')
                  .replace('ô', 'o')
                  .replace('ú', 'u')
                  .replace('ç', 'c'))
        return FRAT_SET_NORMALIZADO.get(chave, s)  # fallback: devolve o valor limpo

    # Lista de fraturas
    fraturas = []
    for _, row in df_sel.iterrows():
        espac = row.get('Espacamento', None)
        if pd.isna(espac):
            continue

        dip_dir = row.get('DipDir', None)
        altura  = row.get('Altura da estrutura', None)
        frat    = row.get('FRAT SET', None)

        fraturas.append({
            "espacamento": float(espac),
            "dip_dir":     float(dip_dir) if pd.notna(dip_dir) else None,
            "altura":      float(altura)  if pd.notna(altura)  else None,
            "frat_set":    normalizar(frat),
        })

    return {
        "surf_dir":          surf_dir,
        "comprimento":       comprimento,
        "espessura_camada":  espessura_camada,
        "fraturas":          fraturas,
    }

# ── Camadas disponíveis para um afloramento (usa df principal das scanlines) ──
@app.get("/api/scanlines/camadas")
def api_scanlines_camadas(afloramento: str = Query(...)):
    """Retorna apenas as camadas presentes no afloramento selecionado."""
    if afloramento not in df['Afloramento'].values:
        return {"camadas": []}

    camadas_no_afloramento = (
        df[df['Afloramento'] == afloramento]['Camada']
        .dropna()
        .unique()
        .tolist()
    )

    # Ordena respeitando a ordem geológica definida em graficos.py
    from graficos import ordem_desejada
    ordenadas     = [c for c in ordem_desejada if c in camadas_no_afloramento]
    nao_ordenadas = sorted(set(camadas_no_afloramento) - set(ordem_desejada))

    return {"camadas": ordenadas + nao_ordenadas}

@app.get("/api/ji2002")
def api_ji2002(autor: str = Query("Todos os autores")):
    return calcular_ji2002("../dados/Compilacao Ji 2002.xlsx", autor)
    
    
@app.get("/api/imagens-drones")
def api_imagens_drones():
    imagens = {
        "Afloramento Vinuales":           "aflos_imagens/Vinuales_Scanlines_Nomes.png",
        "Afloramento Ponte":              "aflos_imagens/Ponte_Scanlines_Nomes.png",
        "Afloramento Cedamavi":           "aflos_imagens/Cedamavi_Scanlines_Nomes.png",
        "Afloramento Zorro":              "aflos_imagens/Zorro_Scanlines_Nomes.png",
        "Afloramento Gauchito Gil":       "aflos_imagens/Gauchito_Scanlines_Nomes.png",
        "Afloramento Lomito":             "aflos_imagens/Lomito_Scanlines_Nomes.png",
        "Afloramento Ablome Costas":      "aflos_imagens/AblomeCostas_Scanlines_Nomes.png",
        "Afloramento BIV":                "aflos_imagens/BIV_Scanlines_Nomes.png",
        "Afloramento Dique Compensador":  "aflos_imagens/Dique_Scanlines_Nomes.png",
        "Afloramento La Bodeguita":       "aflos_imagens/LaBodeguita_Scanlines_Nomes.png",
    }
    return imagens

@app.get("/api/aberturas/grafico")
def api_aberturas_grafico(litofacies: str = Query("Todas as Litofacies")):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.lines as mlines
    from matplotlib.patches import Patch
    import seaborn as sns
    import numpy as np
    import io, base64

    dados = df_veios_confinados.copy()

    # Filtro litofacies
    if litofacies == "Todas as Litofacies":
        dados_sel = dados.copy()
    elif litofacies == "LMC+LMT+MUD":
        dados_sel = dados[dados["Litofacies"].isin(["LMC", "LMT", "MUD"])]
    else:
        dados_sel = dados[dados["Litofacies"] == litofacies]

    dados_limpos = dados_sel.dropna(subset=["abert media"])

    sns.set(style="whitegrid")
    fig, ax = plt.subplots(figsize=(10, 6))

    if dados_limpos.empty:
        ax.text(0.5, 0.5, f"Nenhum dado disponivel para {litofacies}",
                ha="center", va="center", fontsize=12)
        ax.axis("off")
    else:
        q_low  = dados_limpos["abert media"].quantile(0.005)
        q_high = dados_limpos["abert media"].quantile(0.90)
        dados_filtrados = dados_limpos[
            (dados_limpos["abert media"] >= q_low) &
            (dados_limpos["abert media"] <= q_high)
        ]

        def stats(df):
            col = df["abert media"]
            m = col.mode()
            return {
                "media":   col.mean(),
                "mediana": col.median(),
                "moda":    m.iloc[0] if not m.empty else float("nan"),
                "std":     col.std(),
                "max":     col.max(),
                "min":     col.min(),
                "n":       len(df)
            }

        st_todos = stats(dados_limpos)
        st_filt  = stats(dados_filtrados)

        sns_hist = sns.histplot(dados_limpos["abert media"], bins=100, kde=True, ax=ax)
        kde_color = sns_hist.lines[0].get_color() if sns_hist.lines else "black"

        ax.set_title(f"Distribuicao da Abertura Media (Litofacies = {litofacies})")
        ax.set_xlabel("Abertura media (mm)")
        ax.set_ylabel("Frequencia")
        ax.grid(True, alpha=0.3)

        texto_todos = (
            f"Todos os dados:\n"
            f" Media: {st_todos['media']:.2f} mm\n"
            f" Mediana: {st_todos['mediana']:.2f} mm\n"
            f" Moda: {st_todos['moda']:.2f} mm\n"
            f" Desvio padrao: {st_todos['std']:.2f} mm\n"
            f" Minimo: {st_todos['min']:.2f} mm\n"
            f" Maximo: {st_todos['max']:.2f} mm\n"
            f" N de dados: {st_todos['n']}"
        )
        texto_filt = (
            f"Dados filtrados (0.5% - 90%):\n"
            f" Media: {st_filt['media']:.2f} mm\n"
            f" Mediana: {st_filt['mediana']:.2f} mm\n"
            f" Moda: {st_filt['moda']:.2f} mm\n"
            f" Desvio padrao: {st_filt['std']:.2f} mm\n"
            f" Minimo: {st_filt['min']:.2f} mm\n"
            f" Maximo: {st_filt['max']:.2f} mm\n"
            f" N de dados: {st_filt['n']}"
        )

        ax.text(0.55, 0.95, texto_todos, transform=ax.transAxes,
                fontsize=9, color="blue", verticalalignment="top")
        ax.text(0.08, 0.95, texto_filt, transform=ax.transAxes,
                fontsize=9, color="green", verticalalignment="top")

        ax.axvspan(q_low, q_high, color="orange", alpha=0.2)

        quantis = [0.80, 0.85, 0.90, 0.95, 0.99]
        cores   = sns.color_palette("deep", len(quantis))
        for i, q in enumerate(quantis):
            q_val = dados_limpos["abert media"].quantile(q)
            ax.axvline(q_val, linestyle="--", color=cores[i], alpha=0.7,
                       label=f"Q{int(q*100)}={q_val:.2f} mm")

        ax.legend(loc="best", fontsize=8)

    plt.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=100)
    plt.close(fig)
    buf.seek(0)
    img_b64 = base64.b64encode(buf.read()).decode("utf-8")

    return {"imagem": img_b64}    

# ----------------------------------------------------------------------
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
