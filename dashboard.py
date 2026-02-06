import pandas as pd
import streamlit as st
import plotly.express as px

# =====================
# FORMATAÇÃO DE NÚMEROS 
# =====================
def formato_br(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

st.set_page_config(page_title="Dashboard Financeiro", layout="wide")

# =====================
# GOOGLE SHEETS (CSV PUBLICADO)
# =====================
GOOGLE_SHEETS_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSctKxjmf-ReJi0mEun2i5wZP72qdwf9HOeU-CSXS12xk7-tT5qhrPH0lRGcnlGimYcS2rgC_EWu9oO/pub?output=csv"

# =====================
# ATUALIZAÇÃO A CADA 60 SEG
# =====================
@st.cache_data(ttl=60)  # atualiza automaticamente a cada 60s
def carregar_dados():
    df = pd.read_csv(GOOGLE_SHEETS_URL)
    return df

df = carregar_dados()

# =====================
# NORMALIZAÇÃO
# =====================
df.columns = df.columns.str.lower().str.strip()

df["mes_ano_ref"] = pd.to_datetime(df["mes_ano_ref"])
df["mes"] = df["mes_ano_ref"].dt.strftime("%Y-%m")

df["categoria"] = df["categoria"].astype(str).str.lower()
df["subcategoria"] = df["subcategoria"].fillna("outros")
df["status"] = df["status"].fillna("indefinido")
df["detalhe"] = df["detalhe"].fillna("não informado")

df["valor"] = (
    df["valor"]
    .astype(str)
    .str.replace("R$", "", regex=False)
    .str.replace(".", "", regex=False)
    .str.replace(",", ".", regex=False)
    .str.strip()
)

df["valor"] = pd.to_numeric(df["valor"], errors="coerce").fillna(0)

# =====================
# FILTROS (LISTAS)
# =====================
st.sidebar.header("Filtros")

lista_meses = ["Todos"] + sorted(df["mes"].unique().tolist())
mes_selecionado = st.sidebar.selectbox("Mês/Ano", lista_meses)

lista_categorias = ["Todos"] + sorted(df["categoria"].unique().tolist())
categoria_selecionada = st.sidebar.selectbox("Categoria", lista_categorias)

lista_status = ["Todos"] + sorted(df["status"].unique().tolist())
status_selecionado = st.sidebar.selectbox("Status", lista_status)

df_f = df.copy()

if mes_selecionado != "Todos":
    df_f = df_f[df_f["mes"] == mes_selecionado]

if categoria_selecionada != "Todos":
    df_f = df_f[df_f["categoria"] == categoria_selecionada]

if status_selecionado != "Todos":
    df_f = df_f[df_f["status"] == status_selecionado]

# =====================
# KPIs
# =====================
receitas = df_f[df_f["categoria"] == "receita"]["valor"].sum()
despesas = df_f[df_f["categoria"] == "despesa"]["valor"].sum()
saldo = receitas - despesas
ticket_medio = despesas / max(1, len(df_f[df_f["categoria"] == "despesa"]))

c1, c2, c3, c4 = st.columns(4)
c1.metric("Receitas", formato_br(receitas))
c2.metric("Despesas", formato_br(despesas))
c3.metric("Saldo", formato_br(saldo))
c4.metric("Ticket Médio Despesas", formato_br(ticket_medio))

# =====================
# EVOLUÇÃO TEMPORAL
# =====================
st.subheader("Evolução Financeira")

df_mes = (
    df_f.assign(
        valor_calc=lambda x: x.apply(
            lambda r: r["valor"] if r["categoria"] == "receita" else -r["valor"],
            axis=1
        )
    )
    .groupby("mes")["valor_calc"]
    .sum()
    .reset_index()
)

fig_saldo = px.line(
    df_mes,
    x="mes",
    y="valor_calc",
    markers=True,
    title="Saldo Mensal"
)
st.plotly_chart(fig_saldo, use_container_width=True)

# =====================
# DESPESAS POR CATEGORIA
# =====================
st.subheader("Onde o dinheiro está indo")

col1, col2 = st.columns(2)

with col1:
    df_cat = (
        df_f[df_f["categoria"] == "despesa"]
        .groupby("subcategoria")["valor"]
        .sum()
        .reset_index()
        .sort_values("valor", ascending=False)
    )

    fig_cat = px.bar(
        df_cat,
        x="subcategoria",
        y="valor",
        title="Despesas por Subcategoria"
    )
    st.plotly_chart(fig_cat, use_container_width=True)

with col2:
    fig_pie = px.pie(
        df_cat,
        names="subcategoria",
        values="valor",
        title="Distribuição Percentual das Despesas"
    )
    st.plotly_chart(fig_pie, use_container_width=True)

# =====================
# DESPESAS POR DETALHE
# =====================
st.subheader("Despesas por Detalhe")

df_det = (
    df_f[df_f["categoria"] == "despesa"]
    .groupby("detalhe")["valor"]
    .sum()
    .reset_index()
    .sort_values("valor", ascending=False)
)

fig_det = px.bar(
    df_det,
    x="detalhe",
    y="valor",
    title="Gastos por Detalhe"
)
st.plotly_chart(fig_det, use_container_width=True)

# =====================
# STATUS
# =====================
st.subheader("Status dos Lançamentos")

df_status = (
    df_f.groupby("status")["valor"]
    .sum()
    .reset_index()
)

fig_status = px.pie(
    df_status,
    names="status",
    values="valor",
    title="Pago x Pendente"
)
st.plotly_chart(fig_status, use_container_width=True)

# =====================
# TABELA
# =====================
st.subheader("Tabela Analítica")

st.dataframe(
    df_f.sort_values(["mes_ano_ref", "valor"], ascending=[False, False]),
    use_container_width=True
)


