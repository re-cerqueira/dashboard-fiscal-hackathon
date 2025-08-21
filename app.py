import streamlit as st
import pandas as pd
import plotly.express as px

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Dashboard de Validação Fiscal", page_icon="📊", layout="wide")


# --- URLs DOS DADOS ---
URL_BASE = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQXjBJDTJKEqmfsJ7--1yKYu4GS_HGjSL6oYqmxvBQAuq531vP9Tn8aAtslzfcv7-nBI2etu-66UFg1/pub?gid=0&single=true&output=csv"
URL_REGRAS = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQXjBJDTJKEqmfsJ7--1yKYu4GS_HGjSL6oYqmxvBQAuq531vP9Tn8aAtslzfcv7-nBI2etu-66UFg1/pub?gid=811132636&single=true&output=csv"
URL_DIVERGENCIAS = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQXjBJDTJKEqmfsJ7--1yKYu4GS_HGjSL6oYqmxvBQAuq531vP9Tn8aAtslzfcv7-nBI2etu-66UFg1/pub?gid=1194048936&single=true&output=csv"
URL_RESUMO = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQXjBJDTJKEqmfsJ7--1yKYu4GS_HGjSL6oYqmxvBQAuq531vP9Tn8aAtslzfcv7-nBI2etu-66UFg1/pub?gid=1297077689&single=true&output=csv"

@st.cache_data(show_spinner=False)
def carregar_dados_url(url):
    """Carrega dados de uma URL CSV."""
    if not url: return None
    try:
        df = pd.read_csv(url)
        if df.empty: return None
        return df
    except Exception:
        return None

# Carrega os quatro DataFrames
df_base = carregar_dados_url(URL_BASE)
df_regras = carregar_dados_url(URL_REGRAS)
df_divergencias = carregar_dados_url(URL_DIVERGENCIAS)
df_resumo = carregar_dados_url(URL_RESUMO)

# Título principal sempre aparece
st.title("📊 Dashboard de Validação de Regras Fiscais")
st.markdown("---")

dados_essenciais_carregados = df_base is not None and df_regras is not None and df_resumo is not None

if not dados_essenciais_carregados:
    st.error("Falha ao carregar os dados essenciais (Base, Regras ou Resumo). Verifique os links e permissões.")
else:
    # --- SEÇÃO DE COBERTURA DE TESTES (COM A NOVA LÓGICA) ---
    st.header("Cobertura de Testes das Regras")
    
    # Pega os nomes das colunas do arquivo resumo para segurança
    col_resumo_status = df_resumo.columns[0] # Ex: "Regra Validada"
    col_resumo_qtd = df_resumo.columns[1]    # Ex: "Quantidade de Notas"
    
    # --- NOVA LÓGICA DE CÁLCULO ---
    # Total de regras é o total de linhas no arquivo de resumo
    total_regras_catalogo = len(df_resumo)
    # Regras validadas são aquelas com valor na coluna de quantidade (não NaN)
    regras_validadas = int(df_resumo[col_resumo_qtd].count())
    # Regras não validadas são a diferença
    regras_nao_validadas = total_regras_catalogo - regras_validadas
    
    percentual_cobertura = (regras_validadas / total_regras_catalogo) if total_regras_catalogo > 0 else 0
    
    col1, col2 = st.columns([1, 2])
    with col1:
        st.subheader("Percentual de Cobertura")
        df_cobertura = pd.DataFrame({'Status': ['Regras Validadas', 'Regras não Validadas'], 'Quantidade': [regras_validadas, regras_nao_validadas]})
        fig_pizza = px.pie(df_cobertura, values='Quantidade', names='Status', hole=.4, color_discrete_sequence=['#4CAF50', '#F44336'])
        st.plotly_chart(fig_pizza, use_container_width=True)
    with col2:
        st.subheader("Resumo do Catálogo de Regras")
        st.metric("Total de Regras no Catálogo", value=total_regras_catalogo)
        st.metric("Regras Validadas (com cenário de teste)", value=regras_validadas)
        st.metric("Regras não Validadas (sem cenário de teste)", value=regras_nao_validadas)
        st.progress(percentual_cobertura, text=f"Cobertura de Teste: {percentual_cobertura:.1%}")
    
    st.markdown("---")

    # --- SEÇÃO DE ANÁLISE DAS DIVERGÊNCIAS ---
    st.header("Análise das Divergências Encontradas")

    if df_divergencias is None or df_divergencias.empty:
        st.success("🎉 Nenhuma divergência encontrada na amostra de dados!")
    else:
        # Pega os nomes das colunas de forma segura
        col_cod_filial = df_divergencias.columns[0]
        col_numnota = df_divergencias.columns[3]
        col_serie = df_divergencias.columns[4]
        col_regra_aplicada = df_divergencias.columns[10]
        col_estado = df_divergencias.columns[1]

        nfs_com_erro = df_divergencias[[col_cod_filial, col_numnota, col_serie]].drop_duplicates().shape[0]
        df_divergencias['ID_Regra'] = df_divergencias[col_regra_aplicada].astype(str).str.split(' - ').str[0:2].str.join(' - ').str.replace('Regra: ', '')

        col_kpi1, col_kpi2, col_kpi3 = st.columns(3)
        col_kpi1.metric("Total de NFs na Amostra de Teste", value=len(df_base.drop_duplicates()))
        col_kpi2.metric("NFs com Pelo Menos Uma Divergência", value=nfs_com_erro)
        col_kpi3.metric("Total de Divergências Individuais", value=len(df_divergencias))

        with st.expander("Clique aqui para ver o detalhamento dos erros"):
            col_a, col_b = st.columns(2)
            with col_a:
                st.markdown("##### Top Regras-Mãe com Mais Falhas")
                regras_mais_frequentes = df_divergencias['ID_Regra'].value_counts().head(10)
                df_regras_chart = pd.DataFrame({'ID_Regra': regras_mais_frequentes.index, 'Contagem': regras_mais_frequentes.values})
                fig_regras = px.bar(df_regras_chart.sort_values(by='Contagem', ascending=True), 
                                    x='Contagem', y='ID_Regra', orientation='h', text='Contagem')
                fig_regras.update_layout(showlegend=False, yaxis_title='', xaxis_title='Quantidade de Divergências')
                st.plotly_chart(fig_regras, use_container_width=True)
            with col_b:
                st.markdown("##### Proporção de Divergências por Estado")
                divergencias_por_estado = df_divergencias[col_estado].value_counts()
                df_estado_chart = pd.DataFrame({'Estado': divergencias_por_estado.index, 'Quantidade': divergencias_por_estado.values})
                fig_donut = px.pie(df_estado_chart, values='Quantidade', names='Estado', hole=.4)
                st.plotly_chart(fig_donut, use_container_width=True)