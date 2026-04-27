#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# ==============================================================
#  GRAFICOS.PY – Funções de Plotagem para o Dashboard
# ==============================================================

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.lines as mlines
from matplotlib.patches import Patch
from scipy.interpolate import make_interp_spline
import seaborn as sns
import numpy as np
import pingouin as pg
from scipy import stats
import mplstereonet

# --- Listas de ordem desejada para Afloramento e Camada ---
afloramentos_ordem = [
    'VINUALES', 'PONTE', 'HOTEL_DEL_DIQUE', 'CEDAMAVI', 'CEDAMAVI_ESP',
    'ZORRO', 'LALULA', 'GAUCHITO_GIL', 'LOMITO', 'ABLOME_ESP', 'ABLOME',
    'ABLOME_COSTAS', 'BIV', 'DIQUE_COMPENSADOR', 'BODEGUITA'
]
ordem_desejada = [
    'BEIRA_MAR_INFERIORHOTE', 'BEIRA_LAGO', 'BEIRA_RIO',
    'PELE_4', 'PELE_3', 'PELE_2', 'PELE_1',
    'ISOLADA',
    'MARIA_SUPERIOR', 'MARIA_MEDIA', 'MARIA_INFERIOR',
    'MARADONA', 'LEIOLITO', 'UFC_Carbonato',
    'PLANAR', 'COLCHETE', 'GRETA_II', 'GRETA_I',
    'DUMOUND', 'MRG_AT_Gerson', 'SIM1', 'SIM2', 'SIM3', 'SIM4',
    'SRM1', 'SRM2', 'SRM3', 'SRM4', 'SRM5', 'SRM6', 'SRM7'
]

# =================================================================
# 1 – FUNÇÕES AUXILIARES
# =================================================================

def _estatisticas_abertura(df, col="abert media"):
    """Calcula estatísticas para uma coluna específica do DataFrame."""
    if df.empty or col not in df.columns or df[col].isnull().all():
        return {
            "media": np.nan, "mediana": np.nan, "moda": np.nan,
            "std": np.nan, "max": np.nan, "min": np.nan, "n": 0
        }
    mode_val = df[col].mode()
    return {
        "media":   df[col].mean(),
        "mediana": df[col].median(),
        "moda":    mode_val.iloc[0] if not mode_val.empty else np.nan,
        "std":     df[col].std(),
        "max":     df[col].max(),
        "min":     df[col].min(),
        "n":       len(df)
    }


def _estatisticas_altura(df, col="Altura da estrutura"):
    """Calcula estatísticas para a coluna 'Altura da estrutura'."""
    if df.empty or col not in df.columns or df[col].isnull().all():
        return {
            "media": np.nan, "mediana": np.nan, "moda": np.nan,
            "std": np.nan, "max": np.nan, "min": np.nan, "n": 0
        }
    mode_val = df[col].mode()
    return {
        "media":   df[col].mean(),
        "mediana": df[col].median(),
        "moda":    mode_val.iloc[0] if not mode_val.empty else np.nan,
        "std":     df[col].std(),
        "max":     df[col].max(),
        "min":     df[col].min(),
        "n":       len(df)
    }


def preparar_dados_para_excel(df_veios_confinados, litofacies_selecionada):
    """
    Prepara os dados filtrados por litofacies para serem salvos em Excel.
    'df_veios_confinados' deve ter Subtipo=VEIO e Estrutura confinada=Confinada.
    """
    colunas_necessarias = [
        'abert media', 'Espessura da camada', 'Camada', 'Afloramento', 'Litofacies'
    ]
    if not all(col in df_veios_confinados.columns for col in colunas_necessarias):
        return pd.DataFrame()

    df_limpo = df_veios_confinados.dropna(subset=colunas_necessarias)

    if not df_limpo.empty:
        q_low  = df_limpo['abert media'].quantile(0.005)
        q_high = df_limpo['abert media'].quantile(0.90)
        df_filtrado_quantil = df_limpo[
            (df_limpo['abert media'] >= q_low) &
            (df_limpo['abert media'] <= q_high)
        ]
    else:
        df_filtrado_quantil = df_limpo

    if litofacies_selecionada == 'Todas as Litofacies':
        grupo = df_filtrado_quantil.copy()
    elif litofacies_selecionada == 'LMC+LMT+MUD':
        grupo = df_filtrado_quantil[
            df_filtrado_quantil['Litofacies'].isin(['LMC', 'LMT', 'MUD'])
        ]
    else:
        grupo = df_filtrado_quantil[
            df_filtrado_quantil['Litofacies'] == litofacies_selecionada
        ]

    if not grupo.empty:
        grupo = grupo.copy()
        grupo['Espessura da camada'] = pd.to_numeric(
            grupo['Espessura da camada'], errors='coerce'
        )
        grupo = grupo.dropna(subset=['Espessura da camada'])

    if not grupo.empty:
        grupo['Q1'] = grupo.groupby('Espessura da camada')['abert media'].transform(
            lambda x: x.quantile(0.25) if not x.empty else np.nan
        )
        grupo['Mediana'] = grupo.groupby('Espessura da camada')['abert media'].transform(
            lambda x: x.quantile(0.50) if not x.empty else np.nan
        )
        grupo['Q3'] = grupo.groupby('Espessura da camada')['abert media'].transform(
            lambda x: x.quantile(0.75) if not x.empty else np.nan
        )
    else:
        grupo['Q1'] = np.nan
        grupo['Mediana'] = np.nan
        grupo['Q3'] = np.nan

    colunas_selecionadas = [
        'Espessura da camada', 'abert media', 'Litofacies',
        'Camada', 'Afloramento', 'Q1', 'Mediana', 'Q3'
    ]
    colunas_existentes = [c for c in colunas_selecionadas if c in grupo.columns]
    return grupo[colunas_existentes]


# =================================================================
# 2 – FUNÇÕES DE PLOTAGEM
# =================================================================

# ---- 2.1 – Boxplot Espessura x Abertura ----
def grafico_espessura_abertura(df_veios_confinados, litofacies_selecionada):
    sns.set(style="whitegrid")
    fig, ax = plt.subplots(figsize=(10, 6))

    colunas_necessarias = [
        'abert media', 'Espessura da camada', 'Camada', 'Afloramento', 'Litofacies'
    ]
    for col in colunas_necessarias:
        if col not in df_veios_confinados.columns:
            ax.text(0.5, 0.5,
                    f"Erro: Coluna '{col}' não encontrada no DataFrame.",
                    ha='center', va='center', fontsize=12, color='red')
            ax.axis('off')
            return fig

    df_limpo = df_veios_confinados.dropna(subset=colunas_necessarias)

    if not df_limpo.empty:
        q_low  = df_limpo['abert media'].quantile(0.005)
        q_high = df_limpo['abert media'].quantile(0.90)
        df_filtrado_quantil = df_limpo[
            (df_limpo['abert media'] >= q_low) &
            (df_limpo['abert media'] <= q_high)
        ]
    else:
        q_low = q_high = np.nan
        df_filtrado_quantil = df_limpo

    if litofacies_selecionada == 'Todas as Litofacies':
        grupo = df_filtrado_quantil.copy()
    elif litofacies_selecionada == 'LMC+LMT+MUD':
        grupo = df_filtrado_quantil[
            df_filtrado_quantil['Litofacies'].isin(['LMC', 'LMT', 'MUD'])
        ]
    else:
        grupo = df_filtrado_quantil[
            df_filtrado_quantil['Litofacies'] == litofacies_selecionada
        ]

    if grupo.empty:
        ax.text(0.5, 0.5,
                f"Nenhum dado encontrado para a Litofacies: {litofacies_selecionada}",
                ha='center', va='center', fontsize=12)
        ax.axis('off')
        return fig

    sns.boxplot(
        x='Espessura da camada', y='abert media',
        data=grupo, hue='Espessura da camada',
        palette='Greens', dodge=False, ax=ax
    )

    texto = (
        f"Faixa de Abertura Média (Quantil 90%): [{q_low:.2f}, {q_high:.2f}]\n"
        f"Número de dados usados: {len(grupo)}"
    )
    ax.text(
        0.78, 0.98, texto, transform=ax.transAxes, fontsize=10,
        color='blue', verticalalignment='top', horizontalalignment='right',
        bbox=dict(facecolor='white', alpha=0.7, edgecolor='blue')
    )
    ax.set_title(
        f'Espessura da Camada e Abertura Média do VEIO para {litofacies_selecionada}'
    )
    ax.set_xlabel('Espessura da Camada (cm)')
    ax.set_ylabel('Abertura Média da Fratura (mm)')
    ax.tick_params(axis='x', rotation=70)
    plt.tight_layout()
    return fig


# ---- 2.2 – Distribuição abertura VEIOS CONFINADOS por Litofacies ----
def grafico_abertura_por_litofacies(dados, litofacies):
    sns.set(style="whitegrid")

    if 'Litofacies' not in dados.columns or 'abert media' not in dados.columns:
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.text(0.5, 0.5,
                "Colunas 'Litofacies' ou 'abert media' não encontradas.",
                ha='center', va='center', fontsize=12, color='red')
        ax.axis('off')
        return fig

    if litofacies == 'Todas as Litofacies':
        dados_sel = dados.copy()
    elif litofacies == 'LMC+LMT+MUD':
        dados_sel = dados[dados['Litofacies'].isin(['LMC', 'LMT', 'MUD'])]
    else:
        dados_sel = dados[dados['Litofacies'] == litofacies]

    dados_limpos = dados_sel.dropna(subset=['abert media'])
    fig, ax = plt.subplots(figsize=(10, 6))

    if dados_limpos.empty:
        ax.text(0.5, 0.5, f"Nenhum dado disponível para {litofacies}",
                ha='center', va='center', fontsize=12)
        ax.axis('off')
        return fig

    q_low  = dados_limpos['abert media'].quantile(0.005)
    q_high = dados_limpos['abert media'].quantile(0.90)
    dados_filtrados = dados_limpos[
        (dados_limpos['abert media'] >= q_low) &
        (dados_limpos['abert media'] <= q_high)
    ]

    stats_todos     = _estatisticas_abertura(dados_limpos)
    stats_filtrados = _estatisticas_abertura(dados_filtrados)

    sns_hist = sns.histplot(dados_limpos['abert media'], bins=100, kde=True, ax=ax)
    kde_line_color = sns_hist.lines[0].get_color() if sns_hist.lines else "black"

    legend_handles = [
        mlines.Line2D([0], [0], color=kde_line_color, lw=2, linestyle='-',
                      label="Estimativa de densidade de kernel (KDE)")
    ]

    ax.set_title(f'Distribuição da Abertura Média (Litofacies = {litofacies})')
    ax.set_xlabel('Abertura média (mm)')
    ax.set_ylabel('Frequência')
    ax.grid(True, alpha=0.3)

    texto_todos = (
        f"Todos os dados:\n"
        f" Média: {stats_todos['media']:.2f} mm\n"
        f" Mediana: {stats_todos['mediana']:.2f} mm\n"
        f" Moda: {stats_todos['moda']:.2f} mm\n"
        f" Desvio padrão: {stats_todos['std']:.2f} mm\n"
        f" Mínimo: {stats_todos['min']:.2f} mm\n"
        f" Máximo: {stats_todos['max']:.2f} mm\n"
        f" Nº de dados: {stats_todos['n']}"
    )
    texto_filtrados = (
        f"Dados filtrados (0.5% - 90%):\n"
        f" Média: {stats_filtrados['media']:.2f} mm\n"
        f" Mediana: {stats_filtrados['mediana']:.2f} mm\n"
        f" Moda: {stats_filtrados['moda']:.2f} mm\n"
        f" Desvio padrão: {stats_filtrados['std']:.2f} mm\n"
        f" Mínimo: {stats_filtrados['min']:.2f} mm\n"
        f" Máximo: {stats_filtrados['max']:.2f} mm\n"
        f" Nº de dados: {stats_filtrados['n']}"
    )
    ax.text(0.55, 0.95, texto_todos, transform=ax.transAxes,
            fontsize=10, color='blue', verticalalignment='top')
    ax.text(0.08, 0.95, texto_filtrados, transform=ax.transAxes,
            fontsize=10, color='green', verticalalignment='top')

    faixa_90_patch = Patch(color='orange', alpha=0.2,
                           label=f"Faixa 90% ({q_low:.2f} - {q_high:.2f} mm)")
    ax.axvspan(q_low, q_high, color='orange', alpha=0.2)
    legend_handles.append(faixa_90_patch)

    quantis = [0.80, 0.85, 0.90, 0.95, 0.99]
    cores   = sns.color_palette("deep", len(quantis))
    for i, q in enumerate(quantis):
        q_val = dados_limpos['abert media'].quantile(q)
        ax.axvline(q_val, linestyle="--", color=cores[i], alpha=0.7)
        legend_handles.append(
            mlines.Line2D([], [], linestyle="--", color=cores[i],
                          label=f"Q{int(q*100)}={q_val:.2f} mm")
        )

    ax.legend(handles=legend_handles, loc='best')
    plt.tight_layout()
    return fig


# ---- 2.3 – Distribuição abertura por Litofacies e Camada ----
def grafico_abertura_por_litofacies_camada(dados, litofacies, camada):
    sns.set(style="whitegrid")

    if ('Litofacies' not in dados.columns or
            'Camada' not in dados.columns or
            'abert media' not in dados.columns):
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.text(0.5, 0.5,
                "Colunas 'Litofacies', 'Camada' ou 'abert media' não encontradas.",
                ha='center', va='center', fontsize=12, color='red')
        ax.axis('off')
        return fig

    if litofacies == 'Todas as Litofacies':
        dados_sel = dados.copy()
    elif litofacies == 'LMC+LMT+MUD':
        dados_sel = dados[dados['Litofacies'].isin(['LMC', 'LMT', 'MUD'])]
    else:
        dados_sel = dados[dados['Litofacies'] == litofacies]

    if camada != 'Todas as Camadas':
        dados_sel = dados_sel[dados_sel['Camada'] == camada]

    dados_limpos = dados_sel.dropna(subset=['abert media'])
    fig, ax = plt.subplots(figsize=(10, 6))

    if dados_limpos.empty:
        ax.text(0.5, 0.5,
                f"Nenhum dado disponível para Litofacies: {litofacies}, Camada: {camada}",
                ha='center', va='center', fontsize=12)
        ax.axis('off')
        return fig

    q_low  = dados_limpos['abert media'].quantile(0.005)
    q_high = dados_limpos['abert media'].quantile(0.90)
    dados_filtrados = dados_limpos[
        (dados_limpos['abert media'] >= q_low) &
        (dados_limpos['abert media'] <= q_high)
    ]

    stats_todos     = _estatisticas_abertura(dados_limpos)
    stats_filtrados = _estatisticas_abertura(dados_filtrados)

    sns_hist = sns.histplot(dados_limpos['abert media'], bins=100, kde=True, ax=ax)
    kde_line_color = sns_hist.lines[0].get_color() if sns_hist.lines else "black"

    legend_handles = [
        mlines.Line2D([0], [0], color=kde_line_color, lw=2, linestyle='-',
                      label="Estimativa de densidade de kernel (KDE)")
    ]

    ax.set_title(
        f'Distribuição da Abertura Média (Litofacies: {litofacies}, Camada: {camada})'
    )
    ax.set_xlabel('Abertura média (mm)')
    ax.set_ylabel('Frequência')
    ax.grid(True, alpha=0.3)

    texto_todos = (
        f"Todos os dados:\n"
        f" Média: {stats_todos['media']:.2f} mm\n"
        f" Mediana: {stats_todos['mediana']:.2f} mm\n"
        f" Moda: {stats_todos['moda']:.2f} mm\n"
        f" Desvio padrão: {stats_todos['std']:.2f} mm\n"
        f" Mínimo: {stats_todos['min']:.2f} mm\n"
        f" Máximo: {stats_todos['max']:.2f} mm\n"
        f" Nº de dados: {stats_todos['n']}"
    )
    texto_filtrados = (
        f"Dados filtrados (0.5% - 90%):\n"
        f" Média: {stats_filtrados['media']:.2f} mm\n"
        f" Mediana: {stats_filtrados['mediana']:.2f} mm\n"
        f" Moda: {stats_filtrados['moda']:.2f} mm\n"
        f" Desvio padrão: {stats_filtrados['std']:.2f} mm\n"
        f" Mínimo: {stats_filtrados['min']:.2f} mm\n"
        f" Máximo: {stats_filtrados['max']:.2f} mm\n"
        f" Nº de dados: {stats_filtrados['n']}"
    )
    ax.text(0.55, 0.95, texto_todos, transform=ax.transAxes,
            fontsize=10, color='blue', verticalalignment='top')
    ax.text(0.08, 0.95, texto_filtrados, transform=ax.transAxes,
            fontsize=10, color='green', verticalalignment='top')

    faixa_90_patch = Patch(color='orange', alpha=0.2,
                           label=f"Faixa 90% ({q_low:.2f} - {q_high:.2f} mm)")
    ax.axvspan(q_low, q_high, color='orange', alpha=0.2)
    legend_handles.append(faixa_90_patch)

    quantis = [0.80, 0.85, 0.90, 0.95, 0.99]
    cores   = sns.color_palette("deep", len(quantis))
    for i, q in enumerate(quantis):
        q_val = dados_limpos['abert media'].quantile(q)
        ax.axvline(q_val, linestyle="--", color=cores[i], alpha=0.7)
        legend_handles.append(
            mlines.Line2D([], [], linestyle="--", color=cores[i],
                          label=f"Q{int(q*100)}={q_val:.2f} mm")
        )

    ax.legend(handles=legend_handles, loc='best')
    plt.tight_layout()
    return fig


# ---- 2.4 – Distribuição do Tamanho dos Veios por Litofacies ----
def grafico_tamanho_por_litofacies(dados, litofacies):
    sns.set(style="whitegrid")

    if 'Litofacies' not in dados.columns or 'Altura da estrutura' not in dados.columns:
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.text(0.5, 0.5,
                "Colunas 'Litofacies' ou 'Altura da estrutura' não encontradas.",
                ha='center', va='center', fontsize=12, color='red')
        ax.axis('off')
        return fig

    if litofacies == 'Todas as Litofacies':
        df = dados.copy()
    elif litofacies == 'LMC+LMT+MUD':
        df = dados[dados['Litofacies'].isin(['LMC', 'LMT', 'MUD'])]
    else:
        df = dados[dados['Litofacies'] == litofacies]

    df = df.dropna(subset=['Altura da estrutura'])
    fig, ax = plt.subplots(figsize=(10, 6))

    if df.empty:
        ax.text(0.5, 0.5, f"Nenhum dado disponível para Litofacies: {litofacies}",
                ha='center', va='center', fontsize=12)
        ax.axis('off')
        return fig

    q_low_90  = df['Altura da estrutura'].quantile(0.005)
    q_high_90 = df['Altura da estrutura'].quantile(0.90)
    dados_na_faixa    = df[
        (df['Altura da estrutura'] >= q_low_90) &
        (df['Altura da estrutura'] <= q_high_90)
    ]
    num_dados_na_faixa = len(dados_na_faixa)

    altura_media        = df['Altura da estrutura'].mean()
    altura_mediana      = df['Altura da estrutura'].median()
    altura_moda         = df['Altura da estrutura'].mode()
    altura_moda         = altura_moda.iloc[0] if not altura_moda.empty else np.nan
    altura_desvio_padrao = df['Altura da estrutura'].std()
    altura_min          = df['Altura da estrutura'].min()
    altura_max          = df['Altura da estrutura'].max()

    sns.histplot(df['Altura da estrutura'], bins=100, kde=True,
                 label='Histograma com KDE', ax=ax)
    ax.axvspan(q_low_90, q_high_90, color='yellow', alpha=0.3,
               label='Faixa 90% dos dados')

    quantis_colors = ['blue', 'green', 'orange', 'purple', 'red']
    quantis = {
        '80%': df['Altura da estrutura'].quantile(0.80),
        '85%': df['Altura da estrutura'].quantile(0.85),
        '90%': df['Altura da estrutura'].quantile(0.90),
        '95%': df['Altura da estrutura'].quantile(0.95),
        '99%': df['Altura da estrutura'].quantile(0.99),
    }
    for i, (lbl, val) in enumerate(quantis.items()):
        ax.axvline(val, color=quantis_colors[i], linestyle='--',
                   label=f'Quantil {lbl}')

    ax.set_title(
        "Distribuição do Tamanho dos Veios (Altura da Estrutura)\n"
        f"Subtipo = VEIO, Estrutura confinada = Confinada\nLitofacies: {litofacies}"
    )
    ax.set_xlabel('Altura da estrutura (m)')
    ax.set_ylabel('Frequência')

    estatisticas_texto = (
        f"Média: {altura_media:.2f}\nMediana: {altura_mediana:.2f}\n"
        f"Moda: {altura_moda:.2f}\nDesvio padrão: {altura_desvio_padrao:.2f}\n"
        f"Mínimo: {altura_min:.2f}\nMáximo: {altura_max:.2f}\n"
        f"Número de dados total: {len(df)}"
    )
    faixa_texto = (
        f"Número de dados na faixa (90%): {num_dados_na_faixa}\n"
        f"Faixa: [{q_low_90:.2f}, {q_high_90:.2f}]"
    )
    ax.text(0.95, 0.95, estatisticas_texto, transform=ax.transAxes, fontsize=10,
            color='black', verticalalignment='top', horizontalalignment='right')
    ax.text(0.94, 0.73, faixa_texto, transform=ax.transAxes, fontsize=10,
            color='black', verticalalignment='top', horizontalalignment='right')

    ax.legend(loc='best')
    plt.tight_layout()
    return fig


# ---- 2.5 – Distribuição do Tamanho dos Veios por Camada ----
def grafico_tamanho_por_camada(dados, camada):
    sns.set(style="whitegrid")

    if 'Camada' not in dados.columns or 'Altura da estrutura' not in dados.columns:
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.text(0.5, 0.5,
                "Colunas 'Camada' ou 'Altura da estrutura' não encontradas.",
                ha='center', va='center', fontsize=12, color='red')
        ax.axis('off')
        return fig

    df = dados.copy() if camada == 'Todas as Camadas' else dados[dados['Camada'] == camada]
    df = df.dropna(subset=['Altura da estrutura'])
    fig, ax = plt.subplots(figsize=(10, 6))

    if df.empty:
        ax.text(0.5, 0.5, f"Nenhum dado disponível para Camada: {camada}",
                ha='center', va='center', fontsize=12)
        ax.axis('off')
        return fig

    q_low_90  = df['Altura da estrutura'].quantile(0.005)
    q_high_90 = df['Altura da estrutura'].quantile(0.90)
    num_dados_na_faixa = len(df[
        (df['Altura da estrutura'] >= q_low_90) &
        (df['Altura da estrutura'] <= q_high_90)
    ])

    altura_media        = df['Altura da estrutura'].mean()
    altura_mediana      = df['Altura da estrutura'].median()
    altura_moda         = df['Altura da estrutura'].mode()
    altura_moda         = altura_moda.iloc[0] if not altura_moda.empty else np.nan
    altura_desvio_padrao = df['Altura da estrutura'].std()
    altura_min          = df['Altura da estrutura'].min()
    altura_max_val      = df['Altura da estrutura'].max()

    sns.histplot(df['Altura da estrutura'], bins=100, kde=True,
                 label='Histograma com KDE', ax=ax)
    ax.axvspan(q_low_90, q_high_90, color='yellow', alpha=0.3,
               label='Faixa 90% dos dados')

    quantis_colors = ['blue', 'green', 'orange', 'purple', 'red']
    quantis = {
        '80%': df['Altura da estrutura'].quantile(0.80),
        '85%': df['Altura da estrutura'].quantile(0.85),
        '90%': df['Altura da estrutura'].quantile(0.90),
        '95%': df['Altura da estrutura'].quantile(0.95),
        '99%': df['Altura da estrutura'].quantile(0.99),
    }
    for i, (lbl, val) in enumerate(quantis.items()):
        ax.axvline(val, color=quantis_colors[i], linestyle='--',
                   label=f'Quantil {lbl}')

    ax.set_title(
        "Distribuição do Tamanho dos Veios (Altura da Estrutura)\n"
        f"Subtipo = VEIO, Estrutura confinada = Confinada\nCamada: {camada}"
    )
    ax.set_xlabel('Altura da estrutura (m)')
    ax.set_ylabel('Frequência')

    estatisticas_texto = (
        f"Média: {altura_media:.2f}\nMediana: {altura_mediana:.2f}\n"
        f"Moda: {altura_moda:.2f}\nDesvio padrão: {altura_desvio_padrao:.2f}\n"
        f"Mínimo: {altura_min:.2f}\nMáximo: {altura_max_val:.2f}\n"
        f"Número de dados total: {len(df)}"
    )
    faixa_texto = (
        f"Número de dados na faixa (90%): {num_dados_na_faixa}\n"
        f"Faixa: [{q_low_90:.2f}, {q_high_90:.2f}]"
    )
    ax.text(0.95, 0.95, estatisticas_texto, transform=ax.transAxes, fontsize=10,
            color='black', verticalalignment='top', horizontalalignment='right')
    ax.text(0.94, 0.73, faixa_texto, transform=ax.transAxes, fontsize=10,
            color='black', verticalalignment='top', horizontalalignment='right')

    ax.legend(loc='best')
    plt.tight_layout()
    return fig


# ---- 2.6 – VEIOS: Abertura Média x DipDir (jointplot) ----
def grafico_abertura_vs_dipdir(dados):
    sns.set(style="white", font_scale=1.2)

    df = dados.copy()
    df['abert media'] = pd.to_numeric(df['abert media'], errors='coerce')
    df['DipDir']      = pd.to_numeric(df['DipDir'],      errors='coerce')
    df = df.dropna(subset=['abert media', 'DipDir'])

    if df.empty:
        fig, ax = plt.subplots()
        ax.text(0.5, 0.5, "Nenhum dado válido para Abertura média e DipDir",
                ha='center', va='center')
        ax.axis('off')
        return fig

    q_low  = df['abert media'].quantile(0.005)
    q_high = df['abert media'].quantile(0.90)
    df_f   = df[(df['abert media'] >= q_low) & (df['abert media'] <= q_high)]

    g = sns.jointplot(
        data=df_f, x='DipDir', y='abert media',
        kind='scatter', height=8, space=0.3,
        marginal_kws=dict(bins=30, fill=True, kde=True),
    )
    g.ax_joint.set_ylim(0, q_high)
    g.set_axis_labels("Dip Direction (°)", "Abertura Média (mm)")
    plt.suptitle(
        f'Relação entre Abertura Média (<= {q_high:.2f} mm) e Dip Direction (Subtipo: VEIO)',
        y=1.02
    )
    plt.tight_layout()
    return g.fig


# ---- 2.7 – Similaridade VEIOS x JUNTAS (histograma combinado) ----
def grafico_similaridade_veios_juntas(dados):
    sns.set(style="whitegrid")

    if 'Subtipo' not in dados.columns or 'DipDir' not in dados.columns:
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.text(0.5, 0.5, "Colunas 'Subtipo' ou 'DipDir' não encontradas.",
                ha='center', va='center', fontsize=12, color='red')
        ax.axis('off')
        return fig

    df = dados[dados['Subtipo'].isin(['VEIO', 'JUNTA'])].copy()
    df['DipDir'] = pd.to_numeric(df['DipDir'], errors='coerce')
    df = df.dropna(subset=['DipDir'])
    fig, ax = plt.subplots(figsize=(10, 6))

    if df.empty:
        ax.text(0.5, 0.5, "Nenhum dado para VEIO/JUNTA com DipDir válido",
                ha='center', va='center')
        ax.axis('off')
        return fig

    sns.histplot(df[df['Subtipo'] == 'VEIO']['DipDir'],
                 bins=30, color='blue', alpha=0.6, label='VEIO', ax=ax)
    sns.histplot(df[df['Subtipo'] == 'JUNTA']['DipDir'],
                 bins=30, color='orange', alpha=0.6, label='JUNTA', ax=ax)

    ax.set_title('Histograma Combinado de DipDir para VEIO e JUNTA')
    ax.set_xlabel('DipDir')
    ax.set_ylabel('Frequência')
    ax.legend(title='Subtipo')
    plt.tight_layout()
    return fig


# ---- 2.8 – JRC x Abertura Média ----
def grafico_jrc_vs_abertura(dados):
    sns.set(style="white", font_scale=1.2)

    df = dados.copy()
    df['abert media'] = pd.to_numeric(df['abert media'], errors='coerce')
    df['JRC']         = pd.to_numeric(df['JRC'],         errors='coerce')
    df = df.dropna(subset=['abert media', 'JRC'])
    df = df[df['abert media'] < 10]

    if df.empty:
        fig, ax = plt.subplots()
        ax.text(0.5, 0.5, "Nenhum dado válido para Abertura média < 10 e JRC",
                ha='center', va='center')
        ax.axis('off')
        return fig

    g = sns.jointplot(
        data=df, x='JRC', y='abert media',
        kind='scatter', height=8, space=0.3,
        marginal_kws=dict(bins=30, fill=True),
    )
    g.set_axis_labels("JRC", "Abertura Média (mm)")
    plt.suptitle('Relação entre Abertura Média e JRC', y=1.02)
    plt.tight_layout()
    return g.fig


# ---- 2.9 – Desenho de Scanlines ----
def grafico_scanlines(df_original, afloramento_selecionado, camada_selecionada):
    colunas_criticas = [
        "Afloramento", "Camada", "Espacamento", "DipDir",
        "Altura da estrutura", "Surf Dir", "FRAT SET"
    ]
    for col in colunas_criticas:
        if col not in df_original.columns:
            fig, ax = plt.subplots(figsize=(8, 4))
            ax.text(0.5, 0.5, f"Erro: Coluna '{col}' não encontrada.",
                    ha='center', va='center', fontsize=12, color='red')
            ax.axis('off')
            return None, None

    df_sel = df_original[
        (df_original['Afloramento'] == afloramento_selecionado) &
        (df_original['Camada']      == camada_selecionada)
    ].copy()

    if df_sel.empty:
        fig, ax = plt.subplots(figsize=(8, 4))
        ax.text(0.5, 0.5,
                f"Nenhum dado para '{afloramento_selecionado}' / '{camada_selecionada}'.",
                ha='center', va='center', fontsize=12)
        ax.axis('off')
        return None, None

    df_sel['Espacamento'] = pd.to_numeric(df_sel['Espacamento'], errors='coerce')
    df_sel['Surf Dir']    = pd.to_numeric(df_sel['Surf Dir'],    errors='coerce')

    comprimento = df_sel["Espacamento"].sum()
    if comprimento == 0 or pd.isna(comprimento):
        fig, ax = plt.subplots(figsize=(8, 4))
        ax.text(0.5, 0.5, "Comprimento da scanline é zero.",
                ha='center', va='center', fontsize=12)
        ax.axis('off')
        return None, None

    surf_dir_vals = df_sel["Surf Dir"].dropna()
    scan_az_geo   = surf_dir_vals.iloc[0] if not surf_dir_vals.empty else 0.0
    scan_rad      = np.deg2rad((90.0 - scan_az_geo) % 360.0)

    x0, y0 = 0.0, 0.0
    x1 = x0 + comprimento * np.cos(scan_rad)
    y1 = y0 + comprimento * np.sin(scan_rad)
    nx = np.cos(scan_rad + np.pi / 2)
    ny = np.sin(scan_rad + np.pi / 2)

    esp = None
    if ("Espessura da camada" in df_sel.columns and
            not df_sel["Espessura da camada"].isna().all()):
        esp = pd.to_numeric(
            df_sel["Espessura da camada"].dropna().iloc[0], errors='coerce'
        )

    altura_max_val = pd.to_numeric(
        df_sel["Altura da estrutura"], errors='coerce'
    ).max()
    altura_max_val = altura_max_val if pd.notna(altura_max_val) else 0.0
    offset = (esp / 2.0) if (esp is not None and not np.isnan(esp) and esp > 0) else 0.0
    extra  = max(offset, altura_max_val / 2.0)

    x_vals = [x0, x1,
               x0 + extra * nx, x1 + extra * nx,
               x0 - extra * nx, x1 - extra * nx]
    y_vals = [y0, y1,
               y0 + extra * ny, y1 + extra * ny,
               y0 - extra * ny, y1 - extra * ny]

    x_min, x_max = min(x_vals), max(x_vals)
    y_min, y_max = min(y_vals), max(y_vals)

    fig, ax = plt.subplots(figsize=(8, 5))

    if esp is not None and not np.isnan(esp) and esp > 0:
        ax.plot([x0 + offset * nx, x1 + offset * nx],
                [y0 + offset * ny, y1 + offset * ny],
                '--', color='green', lw=1.5, label=f'Topo ({esp:.2f} cm)')
        ax.plot([x0 - offset * nx, x1 - offset * nx],
                [y0 - offset * ny, y1 - offset * ny],
                '--', color='green', lw=1.5, label='Base')

    ax.plot([x0, x1], [y0, y1], color='blue', lw=2, label='Scanline')

    cores_frat = {
        'Nao subordinada': 'red',
        'Subordinada':     'blue',
        'SET3':            'green',
        'SET4':            'purple',
        'Nao observada':   'orange',
        'SET6':            'brown',
        'SET7':            'pink',
        'SET8':            'cyan',
        'SET9':            'magenta',
        'SET10':           'lime',
        'Não Subordinada': 'darkgreen',
        'NaN':             'gray',
    }

    labels_ja_adicionados = set()
    current_dist = 0.0

    for _, row in df_sel.iterrows():
        espac = row['Espacamento']
        if pd.isna(espac):
            continue

        x_pos = x0 + current_dist * np.cos(scan_rad)
        y_pos = y0 + current_dist * np.sin(scan_rad)

        dip_geo = pd.to_numeric(row['DipDir'],              errors='coerce')
        altura  = pd.to_numeric(row['Altura da estrutura'], errors='coerce')
        frat    = str(row['FRAT SET']) if pd.notna(row['FRAT SET']) else 'NaN'

        if pd.notna(dip_geo) and pd.notna(altura) and altura > 0:
            strike_geo = (dip_geo + 90.0) % 360.0
            dip_rad    = np.deg2rad((90.0 - strike_geo) % 360.0)
            meio  = altura / 2.0
            cor   = cores_frat.get(frat, 'gray')
            label = frat if frat not in labels_ja_adicionados else None
            labels_ja_adicionados.add(frat)

            x_f = [x_pos - meio * np.cos(dip_rad), x_pos + meio * np.cos(dip_rad)]
            y_f = [y_pos - meio * np.sin(dip_rad), y_pos + meio * np.sin(dip_rad)]
            ax.plot(x_f, y_f, color=cor, lw=1, label=label)

        current_dist += espac

    ax.set_xlabel('X (cm)', fontsize=10)
    ax.set_ylabel('Y (cm)', fontsize=10)
    ax.set_title(
        f"Scanline – Camada: {camada_selecionada}\n"
        f"Afloramento: {afloramento_selecionado}  |  Surf Dir: {scan_az_geo:.1f}°",
        loc='left', fontsize=11
    )

    handles, labels_leg = ax.get_legend_handles_labels()
    uniq = dict(zip(labels_leg, handles))
    ax.legend(uniq.values(), uniq.keys(), loc='best', fontsize=8,
              title="Tipo de fratura", title_fontsize=9)

    margem_x = (x_max - x_min) * 0.1 if x_max > x_min else 1.0
    margem_y = (y_max - y_min) * 0.1 if y_max > y_min else 1.0
    ax.set_xlim(x_min - margem_x, x_max + margem_x)
    ax.set_ylim(y_min - margem_y, y_max + margem_y)
    ax.set_aspect('equal', adjustable='box')
    ax.grid(True, alpha=0.4)
    plt.tight_layout()
    return fig, df_sel


# ---- 2.10 – Estereograma de Polos e Diagrama de Rosetas (COMBINADO) ----
def plotar_estereograma_e_rose(df_juntas, df_veios, afloramento_selecionado, camada_selecionada):
    sns.set_style("whitegrid")
    fig = plt.figure(figsize=(10, 6))
    ax_stereo = fig.add_subplot(121, projection='stereonet')

    df_juntas_filtered = df_juntas.copy()
    df_veios_filtered  = df_veios.copy()

    if afloramento_selecionado != 'Todos':
        df_juntas_filtered = df_juntas_filtered[
            df_juntas_filtered['Afloramento'] == afloramento_selecionado
        ]
        df_veios_filtered = df_veios_filtered[
            df_veios_filtered['Afloramento'] == afloramento_selecionado
        ]

    if camada_selecionada != 'Todas as Camadas':
        df_juntas_filtered = df_juntas_filtered[
            df_juntas_filtered['Camada'] == camada_selecionada
        ]
        df_veios_filtered = df_veios_filtered[
            df_veios_filtered['Camada'] == camada_selecionada
        ]

    df_final_juntas = df_juntas_filtered.dropna(subset=['Dip', 'Strike_RHR'])
    df_final_veios  = df_veios_filtered.dropna(subset=['Dip', 'Strike_RHR'])

    num_medidas_juntas = len(df_final_juntas)
    num_medidas_veios  = len(df_final_veios)
    num_medidas_total  = num_medidas_juntas + num_medidas_veios

    if num_medidas_total == 0:
        ax_stereo.text(0.5, 0.5, "Nenhum dado válido para estereograma.",
                       transform=ax_stereo.transAxes,
                       ha='center', va='center', fontsize=12, color='red')
        ax_stereo.set_title(
            f"Estereograma de Polos para {afloramento_selecionado}, {camada_selecionada}"
        )
        ax_stereo.grid(True)
        ax_rose = fig.add_subplot(122, projection='polar')
        ax_rose.text(0.5, 0.5, "Nenhum dado válido para diagrama de roseta.",
                     transform=ax_rose.transAxes,
                     ha='center', va='center', fontsize=12, color='red')
        ax_rose.set_xticks([])
        ax_rose.set_yticks([])
        ax_rose.set_title('Diagrama de Rosetas')
        plt.tight_layout()
        return fig

    min_density_level = 2
    levels = np.arange(min_density_level, 100, 1)
    all_strikes_density = pd.concat([df_final_juntas['Strike_RHR'], df_final_veios['Strike_RHR']])
    all_dips_density    = pd.concat([df_final_juntas['Dip'],        df_final_veios['Dip']])

    if not all_strikes_density.empty:
        cax = ax_stereo.density_contourf(
            all_strikes_density, all_dips_density,
            measurement='poles', cmap='coolwarm', levels=levels
        )
        fig.colorbar(cax, ax=ax_stereo, label='Densidade (%)')

    if num_medidas_juntas > 0:
        ax_stereo.pole(df_final_juntas['Strike_RHR'], df_final_juntas['Dip'],
                       'o', markersize=5, color='black', alpha=0.7, label='_nolegend_')
        ax_stereo.plane(df_final_juntas['Strike_RHR'], df_final_juntas['Dip'],
                        color='green', alpha=0.3, linestyle='--', label='_nolegend_')

    if num_medidas_veios > 0:
        ax_stereo.pole(df_final_veios['Strike_RHR'], df_final_veios['Dip'],
                       's', markersize=5, color='red', alpha=0.7, label='_nolegend_')
        ax_stereo.plane(df_final_veios['Strike_RHR'], df_final_veios['Dip'],
                        color='blue', alpha=0.3, linestyle='-', label='_nolegend_')

    ax_stereo.grid(True)
    legend_elements = []
    if num_medidas_juntas > 0:
        legend_elements.append(mlines.Line2D(
            [], [], marker='o', color='black', markersize=5, alpha=0.7,
            linestyle='None', label=f'Polo de JUNTA ({num_medidas_juntas})'
        ))
        legend_elements.append(mlines.Line2D(
            [], [], color='green', lw=2, linestyle='--', alpha=0.3,
            label='Plano de JUNTA'
        ))
    if num_medidas_veios > 0:
        legend_elements.append(mlines.Line2D(
            [], [], marker='s', color='red', markersize=5, alpha=0.7,
            linestyle='None', label=f'Polo de VEIO ({num_medidas_veios})'
        ))
        legend_elements.append(mlines.Line2D(
            [], [], color='blue', lw=2, linestyle='-', alpha=0.3,
            label='Plano de VEIO'
        ))

    ax_stereo.legend(handles=legend_elements,
                     bbox_to_anchor=(1.05, -0.1), loc='lower right', borderaxespad=0.)
    ax_stereo.set_title(
        f'Afloramento: {afloramento_selecionado}, Camada: {camada_selecionada}\n'
        f'(Strike calculado via RHR) - Total de Medidas: {num_medidas_total}\n'
        f'Contorno de densidade > {min_density_level}%'
    )

    ax_rose = fig.add_subplot(122, projection='polar')
    all_strikes_rose = pd.concat([
        df_final_juntas['Strike_RHR'], df_final_veios['Strike_RHR']
    ]).values

    if len(all_strikes_rose) > 0:
        strikes_espelhados = np.concatenate([
            all_strikes_rose, all_strikes_rose + 180
        ]) % 360

        bin_edges = np.arange(0, 361, 10)
        hist, _   = np.histogram(strikes_espelhados, bins=bin_edges)
        hist      = hist / 2.0

        theta = np.deg2rad(bin_edges[:-1] + 5)
        width = np.deg2rad(10)

        ax_rose.bar(theta, hist, width=width, bottom=0.0,
                    edgecolor='k', linewidth=0.5,
                    facecolor='steelblue', alpha=0.8)
        ax_rose.set_theta_zero_location('N')
        ax_rose.set_theta_direction(-1)
        ax_rose.set_thetagrids(
            np.arange(0, 360, 30),
            labels=[f'{a}°' for a in np.arange(0, 360, 30)]
        )

        max_freq = hist.max()
        if max_freq > 0:
            passo = max(1, int(max_freq / 4))
            ax_rose.set_rgrids(
                np.arange(passo, max_freq + passo, passo),
                angle=0, weight='black'
            )
        else:
            ax_rose.set_rgrids([])

        ax_rose.set_title(
            f'Diagrama de Rosetas (Strikes)\nTotal de medidas: {len(all_strikes_rose)}',
            y=1.10, fontsize=12
        )
    else:
        ax_rose.set_title('Nenhum dado de Strike para o Diagrama de Rosetas',
                          y=1.10, fontsize=12)
        ax_rose.set_xticks([])
        ax_rose.set_yticks([])

    fig.subplots_adjust(left=0.05, right=0.95, top=0.9, bottom=0.1, wspace=0.3)
    return fig


# ---- 2.11 – Scatter Plot com Regressão ----
def grafico_scatter_relacoes(df_original, camada, litotipos, x_col, y_col,
                              log_x, log_y, reg_type):
    sns.set(style="whitegrid")
    fig, ax = plt.subplots(figsize=(10, 6))

    df_filtered = df_original.copy()

    if camada != 'Todas as Camadas':
        df_filtered = df_filtered[df_filtered['Camada'] == camada]

    if 'Todas as Litofacies' not in litotipos:
        if 'LMC+LMT+MUD' in litotipos:
            df_filtered = df_filtered[df_filtered['Litofacies'].isin(['LMC', 'LMT', 'MUD'])]
        else:
            df_filtered = df_filtered[df_filtered['Litofacies'].isin(litotipos)]

    df_filtered = df_filtered.dropna(subset=[x_col, y_col])

    if df_filtered.empty:
        ax.text(0.5, 0.5, "Nenhum dado disponível para os filtros selecionados.",
                ha='center', va='center', fontsize=12, color='red')
        ax.axis('off')
        return fig, pd.DataFrame()

    sns.scatterplot(data=df_filtered, x=x_col, y=y_col, ax=ax, alpha=0.7)

    if reg_type == "Linear":
        slope, intercept, r_value, p_value, _ = stats.linregress(
            df_filtered[x_col], df_filtered[y_col]
        )
        x_line = np.array([df_filtered[x_col].min(), df_filtered[x_col].max()])
        y_line = slope * x_line + intercept
        ax.plot(x_line, y_line, color='red', linestyle='--',
                label=f'Regressão Linear\n(R²={r_value**2:.2f}, p={p_value:.3f})')
        ax.legend()

    if log_x:
        ax.set_xscale('log')
    if log_y:
        ax.set_yscale('log')

    ax.set_title(f'Relação entre {x_col} e {y_col}')
    ax.set_xlabel(x_col)
    ax.set_ylabel(y_col)
    plt.tight_layout()
    return fig, df_filtered


# ---- 2.12 – Heatmap de Correlação Spearman ----
def grafico_spearman_heatmap(df_original, camada, litotipos):
    sns.set(style="white")
    fig, ax = plt.subplots(figsize=(12, 10))

    df_filtered = df_original.copy()

    if camada != 'Todas as Camadas':
        df_filtered = df_filtered[df_filtered['Camada'] == camada]

    if 'Todas as Litofacies' not in litotipos:
        if 'LMC+LMT+MUD' in litotipos:
            df_filtered = df_filtered[df_filtered['Litofacies'].isin(['LMC', 'LMT', 'MUD'])]
        else:
            df_filtered = df_filtered[df_filtered['Litofacies'].isin(litotipos)]

    numeric_cols = df_filtered.select_dtypes(include=np.number).columns.tolist()
    df_numeric   = df_filtered[numeric_cols].dropna()

    if df_numeric.empty or len(df_numeric.columns) < 2:
        ax.text(0.5, 0.5,
                "Nenhum dado numérico suficiente para calcular a correlação.",
                ha='center', va='center', fontsize=12, color='red')
        ax.axis('off')
        return fig, None

    corr_spearman = pg.rcorr(df_numeric, method='spearman', stars=False, decimals=2)['r']
    sns.heatmap(corr_spearman, annot=True, cmap='coolwarm',
                fmt=".2f", linewidths=.5, ax=ax)
    ax.set_title(
        f'Heatmap de Correlação de Spearman\n'
        f'Camada: {camada}, Litotipos: {", ".join(litotipos)}'
    )
    plt.tight_layout()
    return fig, corr_spearman


# ---- 2.13 – P21 por Afloramento (com filtro de Camada) ----
def plotar_p21_por_afloramento(df_original, camada_selecionada):
    """
    Gera o gráfico de P21 por Afloramento, filtrado por camada.
    """
    plt.style.use('seaborn-v0_8-darkgrid')

    df = df_original.copy()

    for col in ['Espacamento', 'Espessura da camada', 'Altura da estrutura']:
        if col not in df.columns:
            fig, ax = plt.subplots(figsize=(10, 6))
            ax.text(0.5, 0.5, f"Erro: Coluna '{col}' não encontrada no DataFrame.",
                    ha='center', va='center', fontsize=12, color='red')
            ax.axis('off')
            return fig
        df[col] = pd.to_numeric(df[col], errors='coerce')

    df = df.dropna(how='all')
    df = df[df['Altura da estrutura'] <= 300]

    resultado = (
        df.groupby(['Afloramento', '

