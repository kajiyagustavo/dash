import streamlit as st
import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta
import numpy as np
import openpyxl
import XlsxWriter
import io

# Título do Dashboard
st.title("Análise de Vendas - Comparação de Meses Relacionados")

# Upload de múltiplos arquivos
uploaded_files = st.file_uploader(
    "Faça o upload dos arquivos de vendas (.csv ou .xlsx)", 
    type=['csv', 'xlsx'], 
    accept_multiple_files=True
)

if uploaded_files:
    # Lista para armazenar os DataFrames
    dataframes = []
    
    for file in uploaded_files:
        # Carregar cada arquivo dependendo do formato
        if file.name.endswith('.csv'):
            df = pd.read_csv(file, encoding='utf-8')
        elif file.name.endswith('.xlsx'):
            df = pd.read_excel(file)
        
        # Adicionar o DataFrame à lista
        dataframes.append(df)
    
    # Concatenar todos os DataFrames em um único
    df_consolidado = pd.concat(dataframes, ignore_index=True)
    
    # Verificar se as colunas necessárias existem
    if 'AnoMes' not in df_consolidado.columns:
        st.error("A coluna 'AnoMes' é necessária no conjunto de dados.")
    else:
        # Configurar as abas
        tab1, tab2 = st.tabs(["Comparação Geral", "Meses Relacionados"])

        with tab1:
            st.subheader("Comparação Geral")
            meses = sorted(df_consolidado['AnoMes'].unique(), reverse=True)
            selecao_meses = st.multiselect("Selecione os Ano-Mês para análise", meses)

            if selecao_meses:
                df_filtrado = df_consolidado[df_consolidado['AnoMes'].isin(selecao_meses)]
                st.write(df_filtrado)  # Exemplo de exibição (pode ser ajustado conforme necessário)

        with tab2:
            st.subheader("Análise de Meses Relacionados")

            # Seleção de mês de referência
            meses = sorted(df_consolidado['AnoMes'].unique(), reverse=True)
            mes_referencia = st.selectbox("Selecione o Mês de Referência", meses)

            if mes_referencia:
                # Converter o AnoMes para datetime
                data_referencia = datetime.strptime(mes_referencia, "%Y-%m")

                # Determinar os meses relacionados usando relativedelta
                meses_relacionados = [
                    (data_referencia - relativedelta(years=1, months=1)).strftime("%Y-%m"),  # Mês anterior do ano anterior
                    (data_referencia - relativedelta(years=1)).strftime("%Y-%m"),           # Mesmo mês do ano anterior
                    (data_referencia - relativedelta(years=1, months=-1)).strftime("%Y-%m"), # Próximo mês do ano anterior
                    (data_referencia - relativedelta(months=1)).strftime("%Y-%m"),         # Mês anterior do mesmo ano
                    mes_referencia                                                       # Mês de referência
                ]

                # Filtrar os dados para os meses relacionados
                df_relacionados = df_consolidado[df_consolidado['AnoMes'].isin(meses_relacionados)]

                # Agrupar os dados por NomeEstab e AnoMes
                df_agrupado = df_relacionados.groupby(['AnoMes', 'NomeEstab']).agg(
                    TotalVendas=('ValorTotal', 'sum'),
                    NumeroPassagens=('ValorTotal', 'count')
                ).reset_index()

                # Pivotar os dados para exibição por AnoMes
                df_pivot = df_agrupado.pivot(index='NomeEstab', columns='AnoMes', values=['TotalVendas', 'NumeroPassagens']).fillna(0)

                # Calcular os percentuais de crescimento/decrescimento
                def calcular_percentual(col1, col2):
                    return ((col2 - col1) / col1 * 100).replace([np.inf, -np.inf, np.nan], 0)

                for i in range(len(meses_relacionados) - 1):
                    mes_anterior = meses_relacionados[i]
                    mes_atual = meses_relacionados[i + 1]
                    df_pivot[('CrescimentoPercentual', mes_atual)] = calcular_percentual(
                        df_pivot[('TotalVendas', mes_anterior)], df_pivot[('TotalVendas', mes_atual)]
                    )

                # Ordenar pelo mês de referência
                df_pivot = df_pivot.sort_values(by=('TotalVendas', mes_referencia), ascending=False)

                # Exibir os resultados
                st.subheader("Tabela de Totais e Percentuais por NomeEstab")
                st.dataframe(df_pivot)

                # Exportar para Excel
                st.subheader("Exportar Resultados para Excel")

                # Converter para Excel
                def converter_para_excel(df):
                    output = io.BytesIO()
                    with pd.ExcelWriter(output, engine="openpyxl") as writer:
                        df.to_excel(writer, index=True, sheet_name="Resultados")
                    processed_data = output.getvalue()
                    return processed_data

                excel_data = converter_para_excel(df_pivot)
                st.download_button(
                    label="Baixar Resultados em Excel",
                    data=excel_data,
                    file_name="analise_meses_relacionados.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

else:
    st.info("Por favor, faça o upload de um ou mais arquivos para continuar.")