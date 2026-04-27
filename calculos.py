# backend/calculos.py
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import mplstereonet
import io
import base64

# listas de ordem, reaproveitadas dos arquivos originais
AFLORAMENTOS_ORDEM = [
    'VINUALES', 'PONTE','HOTEL_DEL_DIQUE', 'CEDAMAVI', 'CEDAMAVI_ESP',
    'ZORRO', 'LALULA', 'GAUCHITO_GIL', 'LOMITO', 'ABLOME_ESP', 'ABLOME',
    'ABLOME_COSTAS', 'BIV', 'DIQUE_COMPENSADOR', 'BODEGUITA'
]
CAMADAS_ORDEM = [
    'BEIRA_MAR_INFERIOR', 'FILHOTE', 'BEIRA_LAGO', 'BEIRA_RIO',
    'PELE_4', 'PELE_3', 'PELE_2', 'PELE_1',
    'ISOLADA',
    'MARIA_SUPERIOR', 'MARIA_MEDIA', 'MARIA_INFERIOR',
    'MARADONA', 'LEIOLITO', 'UFC_Carbonato',
    'PLANAR', 'COLCHETE', 'GRETA_II', 'GRETA_I',
    'DUMOUND', 'MRG_AT_Gerson','SIM1','SIM2','SIM3','SIM4',
    'SRM1','SRM2','SRM3','SRM4','SRM5','SRM6','SRM7'
]

# -------------------------------------------------------------------
# AUXILIARES
# -------------------------------------------------------------------

def _stats(series: pd.Series):
    s = series.dropna()
    if s.empty:
        return {
            "media": None, "mediana": None, "moda": None,
            "std": None, "max": None, "min": None, "n": 0
        }
    moda = None
    try:
        m = s.mode()
        moda = float(m.iloc[0]) if not m.empty else None
    except Exception:
        moda = None
    return {
        "media": float(s.mean()),
        "mediana": float(s.median()),
        "moda": moda,
        "std": float(s.std()) if len(s) > 1 else 0.0,
        "max": float(s.max()),
        "min": float(s.min()),
        "n": int(len(s)),
    }

def _filtrar_litofacies(df, litofacies):
    if litofacies == 'Todas as Litofacies':
        return df.copy()
    if litofacies == 'LMC+LMT+MUD':
        return df[df['Litofacies'].isin(['LMC', 'LMT', 'MUD'])].copy()
    return df[df['Litofacies'] == litofacies].copy()

def _filtrar_camada(df, camada):
    if camada == 'Todas as Camadas':
        return df.copy()
    return df[df['Camada'] == camada].copy()

# -------------------------------------------------------------------
# 1. Distribuição geral (página 3)
# -------------------------------------------------------------------

def calcular_distribuicao_fraturas(df: pd.DataFrame):
    """Equivalente à 3_Dados__distribuicao_geral_Fraturas.py, mas retornando contagens."""
    col_qtd = None
    for c in df.columns:
        if "No de estruturas" in c or "QtdFraturas" in c:
            col_qtd = c
            break
    if col_qtd is None:
        # se não achar, conta linhas
        col_qtd = "_cont"
        df = df.copy()
        df[col_qtd] = 1

    df[col_qtd] = pd.to_numeric(df[col_qtd], errors='coerce')
    df2 = df.dropna(subset=[col_qtd])

    # Afloramento
    af = df2.groupby('Afloramento')[col_qtd].sum()
    af = af[af.index.isin(AFLORAMENTOS_ORDEM)]
    af = af.reindex(AFLORAMENTOS_ORDEM).dropna()

    # Camada
    cam = df2.groupby('Camada')[col_qtd].sum()
    cam = cam[cam.index.isin(CAMADAS_ORDEM)]
    cam = cam.reindex(CAMADAS_ORDEM).dropna()

    return {
        "afloramentos": {str(k): float(v) for k, v in af.items()},
        "camadas": {str(k): float(v) for k, v in cam.items()},
    }

# -------------------------------------------------------------------
# 2. P21 por camada (página 6)
# -------------------------------------------------------------------

def calcular_p21_por_camada(df: pd.DataFrame, afloramento: str):
    """Replica a lógica de 6_P21_por_Camada.py, mas retorna lista JSON."""
    d = df.copy()
    for col in ['Espacamento', 'Espessura da camada', 'Altura da estrutura']:
        if col in d.columns:
            d[col] = pd.to_numeric(d[col], errors='coerce')
    d = d.dropna(how='all')

    # removendo PONTE / filtro de altura, como no script
    if 'Afloramento' in d.columns:
        d = d[d['Afloramento'] != 'PONTE']
    if 'Altura da estrutura' in d.columns:
        d = d[d['Altura da estrutura'] <= 300]

    if 'Afloramento' not in d.columns or 'Camada' not in d.columns:
        return []

    # agrupa
    resultado = (
        d.groupby(['Afloramento', 'Camada'])
        .agg(
            Espessura_Media_Camada=('Espessura da camada', 'mean'),
            Comprimento_Scanline=('Espacamento', 'sum'),
            Altura_Total_Fraturas=('Altura da estrutura', 'sum'),
            Total_de_Medidas=('Dip', 'count')
        )
        .reset_index()
    )

    resultado['Area_Scanline'] = (
        (resultado['Comprimento_Scanline'] / 100.0) *
        (resultado['Espessura_Media_Camada'] / 100.0)
    )
    resultado['P21'] = (resultado['Altura_Total_Fraturas'] / 100.0) / resultado['Area_Scanline']

    dados = resultado[resultado['Afloramento'] == afloramento].copy()
    dados = dados.dropna(subset=['Camada'])
    dados['Camada'] = dados['Camada'].astype(str)

    # garante todas as camadas da ordem, preenchendo P21=0
    todas = pd.DataFrame({'Camada': CAMADAS_ORDEM})
    dados = todas.merge(dados, on='Camada', how='left')
    dados['P21'] = dados['P21'].fillna(0.0)

    # ordena decrescente como no gráfico
    dados['Camada'] = pd.Categorical(dados['Camada'], categories=CAMADAS_ORDEM, ordered=True)
    dados = dados.sort_values('Camada', ascending=False)

    saida = []
    for _, row in dados.iterrows():
        esp = float(row['Espessura_Media_Camada']) if not pd.isna(row['Espessura_Media_Camada']) else None
        saida.append({
            "camada": str(row['Camada']),
            "p21": float(row['P21']),
            "espessura_media": esp,
        })
    return saida

# -------------------------------------------------------------------
# 3. Aberturas (página 7, 9)
# -------------------------------------------------------------------

def calcular_abertura_stats(df_veios_conf: pd.DataFrame, litofacies: str, camada: str):
    d = df_veios_conf.copy()
    if 'abert media' not in d.columns:
        return {"erro": "Coluna 'abert media' não encontrada."}

    d = d.dropna(subset=['abert media'])
    d['abert media'] = pd.to_numeric(d['abert media'], errors='coerce')
    d = d.dropna(subset=['abert media'])

    # faixa 90% (0,5% a 90%)
    q_low = d['abert media'].quantile(0.005)
    q_high = d['abert media'].quantile(0.90)
    d_quantil = d[(d['abert media'] >= q_low) & (d['abert media'] <= q_high)]

    if 'Litofacies' in d_quantil.columns:
        d_quantil = _filtrar_litofacies(d_quantil, litofacies)
    if 'Camada' in d_quantil.columns:
        d_quantil = _filtrar_camada(d_quantil, camada)

    if d_quantil.empty:
        return {"erro": "Nenhum dado para os filtros selecionados."}

    # estatísticas
    stats_todos = _stats(d['abert media'])
    stats_filtrados = _stats(d_quantil['abert media'])

    # quantis extras
    quantis = {}
    for q in [0.80, 0.85, 0.90, 0.95, 0.99]:
        quantis[f"q{int(q*100)}"] = float(d_quantil['abert media'].quantile(q))

    return {
        "q_low": float(q_low),
        "q_high": float(q_high),
        "stats_todos": stats_todos,
        "stats_filtrados": stats_filtrados,
        "quantis": quantis,
        "histograma": {
            "valores": d_quantil['abert media'].tolist()
        }
    }

# -------------------------------------------------------------------
# 4. Tamanhos (página 8)
# -------------------------------------------------------------------

def calcular_tamanho_stats(df_veios_conf: pd.DataFrame, litofacies: str, camada: str):
    d = df_veios_conf.copy()
    if 'Altura da estrutura' not in d.columns:
        return {"erro": "Coluna 'Altura da estrutura' não encontrada."}

    d = d.dropna(subset=['Altura da estrutura'])
    d['Altura da estrutura'] = pd.to_numeric(d['Altura da estrutura'], errors='coerce')
    d = d.dropna(subset=['Altura da estrutura'])

    if 'Litofacies' in d.columns:
        d = _filtrar_litofacies(d, litofacies)
    if 'Camada' in d.columns:
        d = _filtrar_camada(d, camada)

    if d.empty:
        return {"erro": "Nenhum dado para os filtros selecionados."}

    q_low = d['Altura da estrutura'].quantile(0.005)
    q_high = d['Altura da estrutura'].quantile(0.90)
    d_quantil = d[(d['Altura da estrutura'] >= q_low) & (d['Altura da estrutura'] <= q_high)]

    stats = _stats(d_quantil['Altura da estrutura'])

    quantis = {}
    for q in [0.80, 0.85, 0.90, 0.95, 0.99]:
        quantis[f"q{int(q*100)}"] = float(d_quantil['Altura da estrutura'].quantile(q))

    return {
        "q_low": float(q_low),
        "q_high": float(q_high),
        "stats": stats,
        "quantis": quantis,
        "valores": d_quantil['Altura da estrutura'].tolist(),
    }

# -------------------------------------------------------------------
# 5. Espessura x Abertura (página 9)
# -------------------------------------------------------------------

def calcular_espessura_abertura(df_veios_conf: pd.DataFrame, litofacies: str):
    d = df_veios_conf.copy()
    colunas = ['abert media', 'Espessura da camada', 'Camada', 'Afloramento', 'Litofacies']
    for c in colunas:
        if c not in d.columns:
            return {"erro": f"Coluna '{c}' não encontrada."}

    d = d.dropna(subset=colunas)

    # faixa 90% na abertura
    q_low = d['abert media'].quantile(0.005)
    q_high = d['abert media'].quantile(0.90)
    d = d[(d['abert media'] >= q_low) & (d['abert media'] <= q_high)]

    d = _filtrar_litofacies(d, litofacies)
    if d.empty:
        return {"erro": "Nenhum dado para a litofácies selecionada."}

    d['Espessura da camada'] = pd.to_numeric(d['Espessura da camada'], errors='coerce')
    d = d.dropna(subset=['Espessura da camada'])

    grupos = d.groupby('Espessura da camada')['abert media']
    dados_box = []
    for espessura, serie in grupos:
        serie = serie.dropna()
        if serie.empty:
            continue
        q1 = float(serie.quantile(0.25))
        med = float(serie.quantile(0.50))
        q3 = float(serie.quantile(0.75))
        minimo = float(serie.min())
        maximo = float(serie.max())
        dados_box.append({
            "espessura": float(espessura),
            "q1": q1,
            "mediana": med,
            "q3": q3,
            "min": minimo,
            "max": maximo,
            "n": int(len(serie)),
        })

    dados_box = sorted(dados_box, key=lambda x: x['espessura'])

    return {
        "dados": dados_box,
        "q_low": float(q_low),
        "q_high": float(q_high),
    }

# -------------------------------------------------------------------
# 6. Estereograma + Roseta (página 5)
# -------------------------------------------------------------------

def calcular_estereograma(df_juntas: pd.DataFrame, df_veios: pd.DataFrame,
                          afloramento: str, camada: str):
    dj = df_juntas.copy()
    dv = df_veios.copy()

    if afloramento != 'Todos':
        dj = dj[dj['Afloramento'] == afloramento]
        dv = dv[dv['Afloramento'] == afloramento]
    if camada != 'Todas as Camadas':
        dj = dj[dj['Camada'] == camada]
        dv = dv[dv['Camada'] == camada]

    dj = dj.dropna(subset=['Dip', 'Strike_RHR'])
    dv = dv.dropna(subset=['Dip', 'Strike_RHR'])

    fig = plt.figure(figsize=(10, 6))
    ax_stereo = fig.add_subplot(121, projection='stereonet')

    all_strikes = pd.concat([dj['Strike_RHR'], dv['Strike_RHR']])
    all_dips = pd.concat([dj['Dip'], dv['Dip']])

    min_density_level = 2
    levels = np.arange(min_density_level, 100, 1)
    if not all_strikes.empty:
        cax = ax_stereo.density_contourf(
            all_strikes, all_dips,
            measurement='poles',
            cmap='coolwarm',
            levels=levels
        )
        fig.colorbar(cax, ax=ax_stereo, label='Densidade (%)')

    if len(dj):
        ax_stereo.pole(dj['Strike_RHR'], dj['Dip'],
                       'o', markersize=5, color='black', alpha=0.7)
        ax_stereo.plane(dj['Strike_RHR'], dj['Dip'],
                        color='green', alpha=0.3, linestyle='--')
    if len(dv):
        ax_stereo.pole(dv['Strike_RHR'], dv['Dip'],
                       's', markersize=5, color='red', alpha=0.7)
        ax_stereo.plane(dv['Strike_RHR'], dv['Dip'],
                        color='blue', alpha=0.3, linestyle='-')

    ax_stereo.grid(True)
    ax_stereo.set_title(
        f'Afloramento: {afloramento}, Camada: {camada}\n'
        f'Total de medidas: {len(all_strikes)}'
    )

    # Roseta
    ax_rose = fig.add_subplot(122, projection='polar')

    strikes = all_strikes.values
    if len(strikes):
        espelhado = np.concatenate([strikes, strikes + 180]) % 360
        bins = np.arange(0, 361, 10)
        hist, edges = np.histogram(espelhado, bins=bins)
        hist = hist / 2.0

        theta = np.deg2rad(edges[:-1] + 5)
        width = np.deg2rad(10)

        ax_rose.bar(
            theta, hist,
            width=width,
            bottom=0.0,
            edgecolor='k',
            linewidth=0.5,
            facecolor='steelblue',
            alpha=0.8
        )

        ax_rose.set_theta_zero_location('N')
        ax_rose.set_theta_direction(-1)
        ax_rose.set_title(
            f'Diagrama de Rosetas (Strikes)\nTotal: {len(strikes)}',
            y=1.10
        )

    fig.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=120, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    b64 = base64.b64encode(buf.read()).decode("utf-8")

    return {
        "imagem_base64": b64,
        "n_juntas": int(len(dj)),
        "n_veios": int(len(dv)),
    }

# -------------------------------------------------------------------
# 7. Scanlines (página 4)
# -------------------------------------------------------------------

def calcular_scanlines(df: pd.DataFrame, afloramento: str, camada: str):
    d = df.copy()
    cols = ["Afloramento", "Camada", "Espacamento", "DipDir",
            "Altura da estrutura", "Surf Dir", "FRAT SET"]
    for c in cols:
        if c not in d.columns:
            return {"erro": f"Coluna '{c}' não encontrada."}

    d = d[(d["Afloramento"] == afloramento) & (d["Camada"] == camada)].copy()
    if d.empty:
        return {"erro": f"Sem dados para {afloramento} / {camada}"}

    d["Espacamento"] = pd.to_numeric(d["Espacamento"], errors="coerce")
    d["DipDir"] = pd.to_numeric(d["DipDir"], errors="coerce")
    d["Altura da estrutura"] = pd.to_numeric(d["Altura da estrutura"], errors="coerce")
    d["Surf Dir"] = pd.to_numeric(d["Surf Dir"], errors="coerce")

    surf_dir_vals = d["Surf Dir"].dropna()
    surf_dir = float(surf_dir_vals.iloc[0]) if not surf_dir_vals.empty else 0.0

    comprimento = float(d["Espacamento"].sum())
    fraturas = []
    dist = 0.0
    for _, row in d.iterrows():
        espac = row["Espacamento"]
        if pd.isna(espac):
            continue
        fraturas.append({
            "distancia": float(dist),
            "dip_dir": float(row["DipDir"]) if pd.notna(row["DipDir"]) else None,
            "altura": float(row["Altura da estrutura"]) if pd.notna(row["Altura da estrutura"]) else None,
            "frat_set": str(row["FRAT SET"]) if pd.notna(row["FRAT SET"]) else "NaN",
            "espacamento": float(espac),
        })
        dist += float(espac)

    espessura = None
    if "Espessura da camada" in d.columns:
        val = pd.to_numeric(d["Espessura da camada"], errors="coerce").dropna()
        if not val.empty:
            espessura = float(val.iloc[0])

    return {
        "surf_dir": surf_dir,
        "comprimento": comprimento,
        "espessura_camada": espessura,
        "fraturas": fraturas,
    }

# -------------------------------------------------------------------
# 8. Ji 2002 (página 10)
# -------------------------------------------------------------------

def calcular_ji2002(caminho: str, autor: str):
    df = pd.read_excel(caminho, sheet_name="Planilha1")
    df.columns = df.columns.str.strip()

    col_esp = next((c for c in df.columns if "Espessura" in c), None)
    col_espc = next((c for c in df.columns if "Espa" in c and c != col_esp), None)
    col_aut = next((c for c in df.columns if "Autor" in c), None)
    col_ref = next((c for c in df.columns if "Refer" in c), None)

    if col_esp:
        df[col_esp] = pd.to_numeric(df[col_esp], errors="coerce")
    if col_espc:
        df[col_espc] = pd.to_numeric(df[col_espc], errors="coerce")

    df = df.dropna(subset=[c for c in [col_esp, col_espc] if c])

    autores = sorted(df[col_aut].dropna().unique().tolist()) if col_aut else []

    if autor != "Todos os autores" and col_aut:
        df = df[df[col_aut] == autor]

    dados = []
    for _, row in df.iterrows():
        dados.append({
            "autor": str(row[col_aut]) if col_aut else "",
            "espessura": float(row[col_esp]),
            "espacamento": float(row[col_espc]),
        })

    refs = []
    if col_ref:
        refs_raw = df[col_ref].dropna().drop_duplicates().str.strip()
        def _fmt(r):
            r = r.strip().rstrip(".")
            if "." in r:
                partes = r.split(".", 1)
                return f"{partes[0].upper()}. {partes[1].strip()}."
            return r + "."
        refs = sorted([_fmt(r) for r in refs_raw], key=lambda x: x.split('.')[0].strip())

    return {"dados": dados, "autores": autores, "referencias": refs}
