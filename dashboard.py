import pandas as pd
import streamlit as st
import plotly.express as px

st.set_page_config(page_title="Dashboard Financeiro", layout="wide")

# =====================
# ESTILO (CARDS)
# =====================
st.markdown("""
<style>
.card {
    border: 1px solid #555;
    border-radius: 12px;
    padding: 16px;
    background-color: rgba(255,255,255,0.03);
    margin-bottom: 16px;
}
</style>
""", unsafe_allow_html=True)

# =====================
# FUNÇÃO FORMATO BR
# =====================
def formato_br(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

# =====================
# GOOGLE SHEETS (CSV)
# =====================
GOOGLE_SHEETS_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSctKxjmf-ReJi0mEun2i5wZP72qdwf9HOeU-CSXS12xk7-tT5qhrPH0lRGcnlGimYcS2rgC_EWu9oO/pub?output=csv"

@st.cache_data(ttl=60)
def carregar_dados():
    return pd.read_csv(GOOGLE_SHEETS_URL)

df = carregar_dados()

# =====================
# NORMALIZAÇÃO
# =====================
df.columns = df.columns.str.lower().str.strip()

df["mes_ano_ref"] = pd.to_datetime(df["mes_ano_ref"])
df["mes_ordem"] = df["mes_ano_ref"].dt.to_period("M").dt.to_timestamp()
df["mes_label"] = df["mes_ano_ref"].dt.strftime("%b/%y").str.lower()

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
# FILTROS
# =====================
st.sidebar.header("Filtros")

lista_meses = ["Todos"] + sorted(
    df["mes_label"].unique().tolist(),
    key=lambda x: pd.to_datetime(x, format="%b/%y")
)

mes_sel = st.sidebar.selectbox("Mês/Ano", lista_meses)

lista_cat = ["Todos"] + sorted(df["categoria"].unique().tolist())
cat_sel = st.sidebar.selectbox("Categoria", lista_cat)

lista_status = ["Todos"] + sorted(df["status"].unique().tolist())
status_sel = st.sidebar.selectbox("Status", lista_status)

df_f = df.copy()

if mes_sel != "Todos":
    df_f = df_f[df_f["mes_label"] == mes_sel]

if cat_sel != "Todos":
    df_f = df_f[df_f["categoria"] == cat_sel]

if status_sel != "Todos":
    df_f = df_f[df_f["status"] == status_sel]

# =====================
# KPIs
# =====================
receitas = df_f[df_f["categoria"] == "receita"]["valor"].sum()
despesas = df_f[df_f["categoria"] == "despesa"]["valor"].sum()
saldo = receitas - despesas
ticket_medio = despesas / max(1, len(df_f[df_f["categoria"] == "despesa"]))

c1, c2, c3, c4 = st.columns(4)

with c1:
    st.markdown(f"<div class='card'><h4>Receitas</h4><h2>{formato_br(receitas)}</h2></div>", unsafe_allow_html=True)

with c2:
    st.markdown(f"<div class='card'><h4>Despesas</h4><h2>{formato_br(despesas)}</h2></div>", unsafe_allow_html=True)

with c3:
    st.markdown(f"<div class='card'><h4>Saldo</h4><h2>{formato_br(saldo)}</h2></div>", unsafe_allow_html=True)

with c4:
    st.markdown(f"<div class='card'><h4>Ticket Médio</h4><h2>{formato_br(ticket_medio)}</h2></div>", unsafe_allow_html=True)

# =====================
# RESUMO INTELIGENTE
# =====================
taxa_poupanca = saldo / receitas if receitas > 0 else 0

if taxa_poupanca >= 0.2:
    saude = "BOA"
    texto = "Você mantém uma taxa de poupança saudável e controle consistente das despesas."
elif taxa_poupanca > 0:
    saude = "ATENÇÃO"
    texto = "Seu saldo é positivo, mas a margem financeira é apertada."
else:
    saude = "CRÍTICA"
    texto = "As despesas consomem toda ou mais do que a receita."

st.markdown(f"""
<div class='card'>
<h4>Resumo Financeiro</h4>
<p><b>Saúde financeira:</b> {saude}</p>
<p>{texto}</p>
</div>
""", unsafe_allow_html=True)

# =====================
# EVOLUÇÃO FINANCEIRA
# =====================
st.subheader("Evolução Financeira")

df_mes = (
    df_f.assign(
        valor_calc=lambda x: x.apply(
            lambda r: r["valor"] if r["categoria"] == "receita" else -r["valor"],
            axis=1
        )
    )
    .groupby(["mes_ordem", "mes_label"])["valor_calc"]
    .sum()
    .reset_index()
    .sort_values("mes_ordem")
)

fig_saldo = px.line(
    df_mes,
    x="mes_label",
    y="valor_calc",
    markers=True,
    title="Evolução do Saldo Mensal"
)

st.markdown("<div class='card'>", unsafe_allow_html=True)
st.plotly_chart(fig_saldo, use_container_width=True)
st.markdown("</div>", unsafe_allow_html=True)

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

    fig_cat = px.bar(df_cat, x="subcategoria", y="valor", title="Despesas por Subcategoria")
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.plotly_chart(fig_cat, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

with col2:
    fig_pie = px.pie(df_cat, names="subcategoria", values="valor", title="Distribuição das Despesas")
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.plotly_chart(fig_pie, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

# =====================
# DESPESAS POR DETALHE
# =====================
st.subheader("Gastos por Detalhe")

df_det = (
    df_f[df_f["categoria"] == "despesa"]
    .groupby("detalhe")["valor"]
    .sum()
    .reset_index()
    .sort_values("valor", ascending=False)
)

fig_det = px.bar(df_det, x="detalhe", y="valor", title="Gastos por Detalhe")

st.markdown("<div class='card'>", unsafe_allow_html=True)
st.plotly_chart(fig_det, use_container_width=True)
st.markdown("</div>", unsafe_allow_html=True)

# =====================
# STATUS
# =====================
st.subheader("Status dos Lançamentos")

df_status = df_f.groupby("status")["valor"].sum().reset_index()
fig_status = px.pie(df_status, names="status", values="valor", title="Status Financeiro")

st.markdown("<div class='card'>", unsafe_allow_html=True)
st.plotly_chart(fig_status, use_container_width=True)
st.markdown("</div>", unsafe_allow_html=True)

# =====================
# TABELA FINAL
# =====================
st.subheader("Tabela Analítica")

st.dataframe(
    df_f.sort_values(["mes_ano_ref", "valor"], ascending=[False, False]),
    use_container_width=True
)
