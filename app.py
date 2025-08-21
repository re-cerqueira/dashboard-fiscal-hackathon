# Importando as bibliotecas necessárias
import streamlit as st
import pandas as pd
import plotly.express as px

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Dashboard de Análise Fiscal", page_icon="📊", layout="wide")


# --- ARQUIVOS NECESSÁRIOS PARA DEPLOY (requirements.txt) ---
# Para deploy na Streamlit Community Cloud, crie um arquivo requirements.txt com o seguinte conteúdo:
# streamlit
# pandas
# plotly


# --- CARGA DE DADOS (100% VIA URL) ---
URL_BASE = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQXjBJDTJKEqmfsJ7--1yKYu4GS_HGjSL6oYqmxvBQAuq531vP9Tn8aAtslzfcv7-nBI2etu-66UFg1/pub?gid=0&single=true&output=csv"
URL_REGRAS = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQXjBJDTJKEqmfsJ7--1yKYu4GS_HGjSL6oYqmxvBQAuq531vP9Tn8aAtslzfcv7-nBI2etu-66UFg1/pub?gid=811132636&single=true&output=csv"
URL_DIVERGENCIAS = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQXjBJDTJKEqmfsJ7--1yKYu4GS_HGjSL6oYqmxvBQAuq531vP9Tn8aAtslzfcv7-nBI2etu-66UFg1/pub?gid=752190062&single=true&output=csv"

# O decorator @st.cache_data melhora a performance, guardando os dados em cache.
@st.cache_data
def carregar_dados_url(url):
    """Função para carregar dados de uma URL CSV e retornar um DataFrame do Pandas."""
    try:
        df = pd.read_csv(url, encoding='utf-8')
        return df
    except UnicodeDecodeError:
        try:
            df = pd.read_csv(url, encoding='latin1')
            return df
        except Exception as e:
            st.error(f"Erro ao ler os dados da URL: {url}")
            st.error(e)
            return None
    except Exception as e:
        st.error(f"Erro ao carregar dados da URL: {url}")
        st.error(e)
        return None

# Carrega os três DataFrames
df_base = carregar_dados_url(URL_BASE)
df_regras = carregar_dados_url(URL_REGRAS)
df_divergencias = carregar_dados_url(URL_DIVERGENCIAS)

# Verifica se todos os arquivos foram carregados antes de continuar
dados_carregados = df_base is not None and df_regras is not None and df_divergencias is not None

if dados_carregados:
    # Remove linhas completamente vazias que podem vir do CSV
    df_regras.dropna(how='all', inplace=True)
    df_divergencias.dropna(how='all', inplace=True)
    df_base.dropna(how='all', inplace=True)

    # --- TRANSFORMAÇÃO E LIMPEZA DOS DADOS ---
    df_divergencias['Regra Aplicada'] = df_divergencias['Regra Aplicada'].astype(str)
    df_regras['Número da Regra'] = df_regras['Número da Regra'].astype(str)
    
    df_divergencias['ID_Regra'] = df_divergencias['Regra Aplicada'].str.split(' - ').str[0:2].str.join(' - ').str.replace('Regra: ', '')
    df_divergencias['Diferença'] = pd.to_numeric(df_divergencias['Diferença'], errors='coerce').fillna(0)
    df_divergencias['DTNOTA'] = pd.to_datetime(df_divergencias['DTNOTA'], format='%d/%m/%Y', errors='coerce')
    df_regras = df_regras.rename(columns={"Número da Regra": "ID_Regra"})


# --- CONSTRUÇÃO DO DASHBOARD ---

st.title("📊 Dashboard de Validação de Regras Fiscais")
st.markdown("---")

if dados_carregados:
    # --- CÁLCULO DOS KPIs EXECUTIVOS ---
    total_nfs_validadas = len(df_base)
    total_campos_com_regras = df_regras['Campos Validados'].nunique()
    total_validacoes_realizadas = total_nfs_validadas * total_campos_com_regras
    total_divergencias = len(df_divergencias)
    total_validacoes_sucesso = total_validacoes_realizadas - total_divergencias
    taxa_de_sucesso = (total_validacoes_sucesso / total_validacoes_realizadas) if total_validacoes_realizadas > 0 else 0
    
    # --- SEÇÃO DE KPIs ---
    st.header("KPIs de Qualidade da Validação")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total de NFs Validadas", value=total_nfs_validadas)
    col2.metric("Total de Validações Realizadas", value=f"{total_validacoes_realizadas:,}")
    col3.metric("Total de Divergências Encontradas", value=total_divergencias)
    col4.metric("Taxa de Sucesso das Validações", value=f"{taxa_de_sucesso:.2%}")

    st.markdown("---")
    
    # --- SEÇÃO DE ANÁLISES DETALHADAS (DENTRO DE EXpanders) ---
    with st.expander("Clique aqui para ver a Análise das Divergências"):
        st.subheader("Análise de Causa Raiz")
        col_a, col_b = st.columns(2)

        with col_a:
            st.markdown("##### Top Regras-Mãe com Mais Falhas")
            regras_mais_frequentes = df_divergencias['ID_Regra'].value_counts().head(10).sort_values(ascending=True)
            fig_regras = px.bar(regras_mais_frequentes, orientation='h', text=regras_mais_frequentes.values)
            fig_regras.update_layout(showlegend=False, yaxis_title='', xaxis_title='Quantidade de Divergências')
            st.plotly_chart(fig_regras, use_container_width=True)

        with col_b:
            st.markdown("##### Proporção de Divergências por Estado")
            divergencias_por_estado = df_divergencias['ESTADO_FILIAL'].value_counts()
            fig_donut = px.pie(divergencias_por_estado, values=divergencias_por_estado.values, names=divergencias_por_estado.index, hole=.4)
            st.plotly_chart(fig_donut, use_container_width=True)
            
    with st.expander("Clique aqui para ver a Análise de Cobertura das Regras"):
        regras_com_falha = set(df_divergencias['ID_Regra'].unique())
        todas_as_regras_unicas = set(df_regras['ID_Regra'].unique())
        regras_sem_falha = todas_as_regras_unicas - regras_com_falha
        
        st.subheader("Regras-Mãe Sem Falhas Registradas")
        st.info(f"Das {len(todas_as_regras_unicas)} regras-mãe existentes no catálogo, {len(regras_sem_falha)} não apresentaram nenhuma divergência nesta amostra de dados.")
        
        lista_regras_sem_falha_str = [str(item) for item in regras_sem_falha]
        st.dataframe(pd.DataFrame(sorted(lista_regras_sem_falha_str), columns=["ID da Regra-Mãe"]))

else:
    st.error("ERRO: Falha ao carregar dados de uma ou mais URLs. Verifique se os links estão corretos e com a permissão 'Publicar na web' ativa.")