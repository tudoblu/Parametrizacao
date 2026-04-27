# backend/data_loader.py
import pandas as pd
import numpy as np

def carregar_dados(caminho_arquivo: str):
    codificacoes = ['utf-8', 'latin1', 'windows-1252']
    delimitadores = [';', ',', '\t']
    df = None

    for encoding in codificacoes:
        for sep in delimitadores:
            try:
                tmp = pd.read_csv(caminho_arquivo, encoding=encoding, sep=sep)
                if tmp.shape[1] > 1:
                    df = tmp
                    break
            except Exception:
                continue
        if df is not None:
            break

    if df is None:
        raise ValueError("Não foi possível carregar o CSV com as combinações testadas.")

    # Normaliza coluna problemática
    df.rename(columns={"Espa amento": "Espacamento"}, inplace=True)

    # Ajuste de confinamento (mesma lógica do Streamlit)
    if {'Espessura da camada', 'Altura da estrutura'}.issubset(df.columns):
        df['Espessura da camada'] = pd.to_numeric(df['Espessura da camada'], errors='coerce')
        df['Altura da estrutura'] = pd.to_numeric(df['Altura da estrutura'], errors='coerce')
        cond = df['Espessura da camada'] <= df['Altura da estrutura']
        df.loc[cond, 'Espessura da camada'] = df.loc[cond, 'Altura da estrutura']
        df.loc[cond, 'Estrutura confinada'] = 'Confinada'
        df.loc[~cond, 'Estrutura confinada'] = 'Não Confinada'
    else:
        df['Estrutura confinada'] = 'Não Aplicável'

    colunas_numericas = [
        'abert media', 'Altura da estrutura', 'Espacamento',
        'DipDir', 'Azimute acamamento', 'Espessura da camada',
        'JRC', 'Dip'
    ]
    for col in colunas_numericas:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    if 'FRAT SET' in df.columns:
        df['FRAT SET'] = df['FRAT SET'].astype(str)
    if 'Subtipo' in df.columns:
        df['Subtipo'] = df['Subtipo'].astype(str)

    def _strike_rhr(dip_direction):
        if pd.isnull(dip_direction):
            return np.nan
        strike = dip_direction - 90
        strike = strike % 360
        if strike < 0:
            strike += 360
        return strike

    if 'DipDir' in df.columns:
        df['Strike_RHR'] = df['DipDir'].apply(_strike_rhr)

    df_juntas = df[df.get('Subtipo', '').astype(str).str.contains('JUNTA', na=False)].copy()
    df_veios  = df[df.get('Subtipo', '').astype(str).str.contains('VEIO',  na=False)].copy()

    df_veios_confinados = df_veios.copy()
    if 'Estrutura confinada' in df_veios_confinados.columns:
        df_veios_confinados = df_veios_confinados[
            df_veios_confinados['Estrutura confinada'] == 'Confinada'
        ]

    return df, df_juntas, df_veios, df_veios_confinados
