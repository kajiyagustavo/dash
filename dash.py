import streamlit as st
import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta
import numpy as np
import xlsxwriter
import io

st.title("Análise de Vendas - Comparação de Meses Relacionados")

# Upload de arquivos
uploaded_files = st.file_uploader(
    "Faça o upload dos arquivos de vendas (.csv ou .xlsx)", 
    type=['csv', 'xlsx'], 
    accept_multiple_files=True
)

# Função para adicionar total no fim das colunas
def adicionar_total(df, valor_colunas):
    total = {col: df[col].sum() if col in valor_colunas else "Total" for col in df.columns}
    return pd.concat([df, pd.DataFrame([total])], ignore_index=True)

if uploaded_files:
    # Concatenar arquivos em um único DataFrame
    dataframes = []
    for file in uploaded_files:
        if file.name.endswith('.csv'):
            df = pd.read_csv(file, encoding='utf-8', low_memory=False)
        elif file.name.endswith('.xlsx'):
            df = pd.read_excel(file)
        dataframes.append(df)
    
    df_consolidado = pd.concat(dataframes, ignore_index=True)
    
    if 'AnoMes' not in df_consolidado.columns or 'NomeEstab' not in df_consolidado.columns:
        st.error("As colunas 'AnoMes' e 'NomeEstab' são necessárias no conjunto de dados.")
    else:
        # Parâmetro Geral: Seleção de Ano-Mês
        st.sidebar.header("Parâmetro Geral")
        meses_disponiveis = sorted(df_consolidado['AnoMes'].unique(), reverse=True)
        meses_selecionados = st.sidebar.multiselect("Selecione os Ano-Mês para análise", meses_disponiveis)

        if not meses_selecionados:
            st.warning("Selecione pelo menos um Ano-Mês para continuar.")
        else:
            # Definição das Tabs (uma única vez)
            tab1, tab2, tab3, tab4 = st.tabs([
                "Comparação Geral", 
                "Meses Relacionados", 
                "Resumo Consolidado", 
                "Vendas por Estabelecimento"
            ])

            # Tab 1: Comparação Geral
            with tab1:
                st.subheader("Comparação Geral")
                df_filtrado = df_consolidado[df_consolidado['AnoMes'].isin(meses_selecionados)]
                st.write(f"**Ano-Mês Selecionados:** {', '.join(meses_selecionados)}")
                st.dataframe(df_filtrado)

            # Tab 2: Meses Relacionados
            with tab2:
                st.subheader("Análise de Meses Relacionados")
                mes_referencia = st.selectbox("Selecione o Mês de Referência", meses_selecionados)

                if mes_referencia:
                    data_referencia = datetime.strptime(mes_referencia, "%Y-%m")

                    meses_relacionados = [
                        (data_referencia - relativedelta(years=1, months=1)).strftime("%Y-%m"),
                        (data_referencia - relativedelta(years=1)).strftime("%Y-%m"),
                        (data_referencia - relativedelta(years=1) + relativedelta(months=1)).strftime("%Y-%m"),
                        (data_referencia - relativedelta(months=1)).strftime("%Y-%m"),
                        mes_referencia
                    ]

                    meses_disponiveis_set = set(df_consolidado['AnoMes'])
                    meses_relacionados = [mes for mes in meses_relacionados if mes in meses_disponiveis_set]

                    df_relacionados = df_consolidado[df_consolidado['AnoMes'].isin(meses_relacionados)]

                    df_agrupado = df_relacionados.groupby(['AnoMes', 'NomeEstab']).agg(
                        TotalVendas=('ValorTotal', 'sum'),
                        NumeroPassagens=('ValorTotal', 'count')
                    ).reset_index()

                    df_pivot = df_agrupado.pivot(index='NomeEstab', columns='AnoMes', values=['TotalVendas', 'NumeroPassagens']).fillna(0)
                    df_pivot.columns = ['_'.join(map(str, col)) for col in df_pivot.columns]

                    st.dataframe(df_pivot)

            # Tab 3: Resumo Consolidado
            with tab3:
                st.subheader("Resumo Consolidado")
                df_filtrado = df_consolidado[df_consolidado['AnoMes'].isin(meses_selecionados)]
                total_vendas = df_filtrado['ValorTotal'].sum()
                total_passagens = len(df_filtrado)
                total_estabelecimentos = df_filtrado['NomeEstab'].nunique()

                st.write(f"**Total de Vendas:** R$ {total_vendas:,.2f}")
                st.write(f"**Número Total de Passagens:** {total_passagens}")
                st.write(f"**Número de Estabelecimentos:** {total_estabelecimentos}")

            # Tab 4: Vendas por Estabelecimento
            with tab4:
                st.subheader("Vendas por Estabelecimento")
                estabelecimentos = sorted(df_consolidado['NomeEstab'].unique())
                estabelecimentos_selecionados = st.multiselect("Selecione os NomeEstab", estabelecimentos)

                if estabelecimentos_selecionados:
                    # Filtrar os dados com base nos estabelecimentos selecionados e meses globais
                    df_filtrado = df_consolidado[
                        (df_consolidado['NomeEstab'].isin(estabelecimentos_selecionados)) &
                        (df_consolidado['AnoMes'].isin(meses_selecionados))
                    ]

                    # Função para adicionar totais ao DataFrame
                    def adicionar_total(df, colunas_valores):
                        total = {col: df[col].sum() if col in colunas_valores else "Total" for col in df.columns}
                        return pd.concat([df, pd.DataFrame([total])], ignore_index=True)

                    # Processar cada NomeEstab individualmente
                    for nome_estab in estabelecimentos_selecionados:
                        st.write(f"### Estabelecimento: {nome_estab}")

                        df_estab = df_filtrado[df_filtrado['NomeEstab'] == nome_estab]

                        ### Contagem de tipoVenda
                        if 'TipoVenda' in df_estab.columns:
                            tipo_venda_counts = (
                                df_estab.groupby(['AnoMes', 'TipoVenda'])
                                .size()
                                .reset_index(name='Contagem')
                            )

                            # Calcular o total por AnoMes para obter percentuais
                            total_por_mes = tipo_venda_counts.groupby('AnoMes')['Contagem'].transform('sum')
                            tipo_venda_counts['Percentual'] = (tipo_venda_counts['Contagem'] / total_por_mes * 100).round(2)

                            # Pivotar a tabela para melhor visualização
                            tipo_venda_pivot = tipo_venda_counts.pivot_table(
                                index='TipoVenda',
                                columns='AnoMes',
                                values=['Contagem', 'Percentual'],
                                fill_value=0
                            ).reset_index()

                            # Adicionar total ao DataFrame
                            colunas_valores_tipo_venda = tipo_venda_pivot.columns.get_level_values(1).unique()
                            tipo_venda_pivot_com_total = adicionar_total(tipo_venda_pivot, colunas_valores_tipo_venda)

                            # Exibir a tabela no Streamlit
                            st.write("#### Contagem de TipoVenda com Totais")
                            st.dataframe(tipo_venda_pivot_com_total)

                        ### Contagem de DescDesconto
                        if 'DescDesconto' in df_estab.columns:
                            desc_desconto_counts = (
                                df_estab.groupby(['AnoMes', 'DescDesconto'])
                                .size()
                                .reset_index(name='Contagem')
                            )

                            # Calcular o total por AnoMes para obter percentuais
                            total_por_mes_desc = desc_desconto_counts.groupby('AnoMes')['Contagem'].transform('sum')
                            desc_desconto_counts['Percentual'] = (desc_desconto_counts['Contagem'] / total_por_mes_desc * 100).round(2)

                            # Pivotar a tabela para melhor visualização
                            desc_desconto_pivot = desc_desconto_counts.pivot_table(
                                index='DescDesconto',
                                columns='AnoMes',
                                values=['Contagem', 'Percentual'],
                                fill_value=0
                            ).reset_index()

                            # Adicionar total ao DataFrame
                            colunas_valores_desc_desconto = desc_desconto_pivot.columns.get_level_values(1).unique()
                            desc_desconto_pivot_com_total = adicionar_total(desc_desconto_pivot, colunas_valores_desc_desconto)

                            # Exibir a tabela no Streamlit
                            st.write("#### Contagem de DescDesconto com Totais")
                            st.dataframe(desc_desconto_pivot_com_total)

                    # Criar DataFrames separados (tabelas 1, 2, 3, 4)
                    df_valor_total = df_filtrado.pivot_table(
                        index='NomeEstab',
                        columns='AnoMes',
                        values='ValorTotal',
                        aggfunc='sum',
                        fill_value=0
                    ).reset_index()

                    df_valor_total_com_total = adicionar_total(df_valor_total, df_valor_total.columns[1:])
                    st.write("### Tabela 1: Valor Total por NomeEstab e Ano-Mês (com Totais)")
                    st.dataframe(df_valor_total_com_total)

                    df_desconto = df_filtrado.pivot_table(
                        index='NomeEstab',
                        columns='AnoMes',
                        values='Desconto',
                        aggfunc='sum',
                        fill_value=0
                    ).reset_index()

                    df_desconto_com_total = adicionar_total(df_desconto, df_desconto.columns[1:])
                    st.write("### Tabela 2: Desconto por NomeEstab e Ano-Mês (com Totais)")
                    st.dataframe(df_desconto_com_total)

                    df_quantidade_passagens = df_filtrado.pivot_table(
                        index='NomeEstab',
                        columns='AnoMes',
                        values='ValorTotal',
                        aggfunc='count',
                        fill_value=0
                    ).reset_index()

                    df_quantidade_passagens_com_total = adicionar_total(df_quantidade_passagens, df_quantidade_passagens.columns[1:])
                    st.write("### Tabela 3: Quantidade de Passagens por NomeEstab e Ano-Mês (com Totais)")
                    st.dataframe(df_quantidade_passagens_com_total)

                    df_percentual_desconto = df_desconto.copy()
                    for col in df_percentual_desconto.columns[1:]:
                        if col in df_valor_total.columns:
                            df_percentual_desconto[col] = (df_desconto[col] / df_valor_total[col] * 100).fillna(0)

                    df_percentual_desconto_com_total = adicionar_total(df_percentual_desconto, df_percentual_desconto.columns[1:])
                    st.write("### Tabela 4: Percentual de Desconto (Desconto / ValorTotal * 100, com Totais)")
                    st.dataframe(df_percentual_desconto_com_total)

                    # Tabelas separadas por OrigemDestino
                    for nome_estab in estabelecimentos_selecionados:
                        st.write(f"### Tabelas Separadas para {nome_estab}")
                        df_filtrado_estab = df_filtrado[df_filtrado['NomeEstab'] == nome_estab]

                        df_valor_total_origem = df_filtrado_estab.pivot_table(
                            index='OrigemDestino',
                            columns='AnoMes',
                            values='ValorTotal',
                            aggfunc='sum',
                            fill_value=0
                        ).reset_index()

                        df_valor_total_origem_com_total = adicionar_total(df_valor_total_origem, df_valor_total_origem.columns[1:])
                        st.write("#### Valor Total por OrigemDestino (com Totais)")
                        st.dataframe(df_valor_total_origem_com_total)