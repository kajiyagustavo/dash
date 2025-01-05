import os
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

# Configuração da página
st.set_page_config(page_title="Dashboard de Vendas de Passagens", layout="wide")

# Função para carregar os dados dos arquivos XLSX
def load_data(selected_files):
    dfs = []
    for file in selected_files:
        try:
            # Listar as planilhas disponíveis no arquivo
            xls = pd.ExcelFile(file)
            st.write(f"Planilhas disponíveis no arquivo {file}: {xls.sheet_names}")
            
            # Tentar carregar a primeira planilha
            df = pd.read_excel(xls, sheet_name=0)
            
            # Verificar se a coluna 'DataVenda' está presente
            if 'DataVenda' not in df.columns:
                st.error(f"A coluna 'DataVenda' não foi encontrada no arquivo {file}.")
                continue
            
            # Converter a coluna 'DataVenda' para datetime
            df['DataVenda'] = pd.to_datetime(df['DataVenda'], errors='coerce')
            df['AnoMes'] = os.path.basename(file).split('.')[0]
            
            # Converta as colunas numéricas, tratando erros
            numeric_columns = ['Valor', 'TaxaEmbarque', 'Seguro', 'Pedagio', 'Desconto', 'TotalICMS', 'ValorTarifa']
            for col in numeric_columns:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '.'), errors='coerce')
            
            dfs.append(df)
        
        except Exception as e:
            st.error(f"Erro ao carregar o arquivo {file}: {e}")
            continue
    
    if dfs:
        combined_df = pd.concat(dfs, ignore_index=True)
        combined_df = combined_df.dropna(subset=['DataVenda', 'ValorTarifa'])
        return combined_df
    else:
        return pd.DataFrame()  # Retorna um DataFrame vazio se não houver dados válidos

# Função para ordenar os arquivos corretamente
def sort_files(files):
    def extract_date(filename):
        try:
            date_str = os.path.basename(filename).split('.')[0]
            return datetime.strptime(date_str, '%Y-%m')
        except ValueError:
            return None
    
    sorted_files = sorted([f for f in files if extract_date(f) is not None], key=extract_date)
    return sorted_files

# Função para converter DataFrame para CSV
@st.cache_data
def convert_df(df):
    return df.to_csv(index=False).encode('utf-8')

# Título
st.title("Dashboard de Vendas de Passagens - Análise de Metas")

# Diretório contendo os arquivos XLSX
data_dir = '/Users/gustavokajiyagomesferreira/JamjoyDados/Novo_Teste_importacao/melhorado/Versao_final2/relatorios/split'

# Lista todos os arquivos XLSX no diretório e ordena-os
all_files = sort_files([os.path.join(data_dir, f) for f in os.listdir(data_dir) if f.endswith('.xlsx')])

# Multiselect para escolher os arquivos
selected_files = st.multiselect(
    "Selecione os meses para análise:",
    all_files,
    format_func=lambda x: os.path.basename(x).split('.')[0]
)

if selected_files:
    # Carrega os dados
    df = load_data(selected_files)

    # Verifica se há dados válidos
    if df.empty:
        st.error("Não foi possível carregar dados válidos dos arquivos selecionados.")
        st.stop()

    # Filtros de data e outros
    start_date = st.date_input("Data Inicial", value=df['DataVenda'].min())
    end_date = st.date_input("Data Final", value=df['DataVenda'].max())

    # Filtro por estabelecimento
    estabelecimentos = df['NomeEstab'].unique()
    selected_estabelecimentos = st.multiselect("Selecione o Estabelecimento:", estabelecimentos, default=estabelecimentos)

    # Aplicar filtros
    mask = (df['DataVenda'].dt.date >= start_date) & (df['DataVenda'].dt.date <= end_date) & (df['NomeEstab'].isin(selected_estabelecimentos))
    filtered_df = df[mask]

    # Métricas principais
    col1, col2, col3, col4 = st.columns(4)
    total_vendas = len(filtered_df)
    col1.metric("Número de Vendas", f"{total_vendas:,}".replace(',', '.'))
    
    total_value = filtered_df['ValorTarifa'].sum()
    col2.metric("Valor Total", f"R$ {total_value:,.2f}".replace(',', '_').replace('.', ',').replace('_', '.'))
    
    ticket_medio = total_value / total_vendas if total_vendas > 0 else 0
    col3.metric("Ticket Médio", f"R$ {ticket_medio:.2f}".replace('.', ','))

    col4.metric("Número de Linhas", filtered_df['IdLinha'].nunique())

    # Meta de crescimento
    st.subheader("Meta de Crescimento")
    try:
        first_file_date = datetime.strptime(os.path.basename(selected_files[0]).split('.')[0], '%Y-%m')
        previous_year_month = (first_file_date - pd.DateOffset(years=1)).strftime('%Y-%m')
        vendas_ano_anterior = df[df['AnoMes'] == previous_year_month]['ValorTarifa'].sum()
        meta_valor = vendas_ano_anterior * 1.2

        col5, col6 = st.columns(2)
        col5.metric("Valor Meta", f"R$ {meta_valor:,.2f}".replace(',', '_').replace('.', ',').replace('_', '.'))
        col6.metric("Atingido", f"R$ {total_value:,.2f}".replace(',', '_').replace('.', ',').replace('_', '.'), 
                    delta=f"{((total_value - vendas_ano_anterior) / vendas_ano_anterior) * 100:.2f}%", 
                    delta_color="normal")
    except Exception as e:
        st.error(f"Erro ao calcular a meta de crescimento: {e}")

    # Tabela de estabelecimentos e trechos
    st.subheader("Tabela de Estabelecimentos e Trechos")
    if 'Origem' in filtered_df.columns and 'Destino' in filtered_df.columns:
        tabela_trechos = filtered_df[['NomeEstab', 'Origem', 'Destino']].drop_duplicates()
        st.write(tabela_trechos)

    # Análise de vendas por dia da semana
    st.subheader("Análise de Vendas por Dia da Semana")
    filtered_df['DiaSemana'] = filtered_df['DataVenda'].dt.day_name(locale='pt_BR')
    vendas_por_dia = filtered_df['DiaSemana'].value_counts().reindex(
        ['segunda-feira', 'terça-feira', 'quarta-feira', 'quinta-feira', 'sexta-feira', 'sábado', 'domingo']).reset_index()
    vendas_por_dia.columns = ['Dia', 'Número de Vendas']
    st.write(vendas_por_dia)

    # Gráficos de análise
    st.subheader("Análise de Vendas")

    # Vendas por mês
    vendas_por_mes = filtered_df.groupby('AnoMes')['ValorTarifa'].sum().reset_index()
    fig1 = px.line(vendas_por_mes, x='AnoMes', y='ValorTarifa', title='Vendas por Mês')
    st.plotly_chart(fig1)

    # Top 10 linhas mais vendidas
    top_linhas = filtered_df.groupby('IdLinha')['ValorTarifa'].sum().nlargest(10).reset_index()
    fig2 = px.bar(top_linhas, x='IdLinha', y='ValorTarifa', title='Top 10 Linhas Mais Vendidas')
    st.plotly_chart(fig2)

    # Vendas por agência
    vendas_por_agencia = filtered_df.groupby('NomeEstab')['ValorTarifa'].sum().nlargest(10).reset_index()
    fig_agencia = px.bar(vendas_por_agencia, x='NomeEstab', y='ValorTarifa', title='Top 10 Agências por Vendas')
    st.plotly_chart(fig_agencia)

    # Distribuição de preços
    st.subheader("Distribuição de Preços")
    fig3 = px.histogram(filtered_df, x='ValorTarifa', nbins=50, title='Distribuição dos Preços das Passagens')
    st.plotly_chart(fig3)

    # Download button para o DataFrame filtrado
    csv = convert_df(filtered_df)
    st.download_button(
        label="Download dados filtrados como CSV",
        data=csv,
        file_name='dados_filtrados.csv',
        mime='text/csv',
    )

else:
    st.write("Por favor, selecione pelo menos um arquivo para análise.")
