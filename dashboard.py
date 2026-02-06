import pandas as pd
import streamlit as st
import plotly.express as px

# =====================
# CONFIGURAÇÃO
# =====================
st.set_page_config(page_title="Dashboard Financeiro", layout="wide")

# =====================
# CSS DEFINITIVO
# =====================
st.markdown("""
<style>
.kpi-card {
    border: 1px solid #555;
    border-radius: 12px;
    padding: 16px;
    background-color: rgba(255,255,255,0.03);
    margin-bottom: 16px;
}

.card {
    border: 1px solid #555;
    border-radius: 12px;
    padding: 16px;
    background-color: rgba(255,255,255,0.03);
    margin-bottom: 16px;
}

div.stPlotlyChart {
    border: 1px solid #555;
    border-radius: 12px;
    padding: 12px;
    background-color: rgba(255,255,255,0.03);
    margin-bottom: 16px;
    overflow: hidden;
}
</style>
""", unsafe_allow_html=True)

# =====================
# FORMATO BR
# =====================
def formato_br(v):
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

# =====================
# GOOGLE SHEETS
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

df["mes_ano_ref"] = pd.to_datetime(
    df["mes_ano_ref"],
    format="%d/%m/%Y",
    errors="coerce"
)

df["mes_ordem"] = df["mes_ano_ref"].dt.to_period("M").dt.to_timestamp()
df["mes_label"] = df["mes_ano_ref"].dt.strftime("%b/%y").str.capitalize()

df["categoria"] = df["categoria"].str.lower()
df["subcategoria"] = df["subcategoria"].fillna("outros")
df["status"] = df["status"].fillna("indefinido")
df["detalhe"] = df["detalhe"].fillna("não informado")

df["valor"] = (
    df["valor"]
    .astype(str)
    .str.replace("R$", "", regex=False)
    .str.replace(".", "", regex=False)
    .str.replace(",", ".", regex=False)
)

df["valor"] = pd.to_numeric(df["valor"], errors="coerce").fillna(0)

# =====================
# FILTROS
# =====================
st.sidebar.header("Filtros")

lista_meses = ["Todos"] + sorted(
    df["mes_label"].unique(),
    key=lambda x: pd.to_datetime(x, format="%b/%y")
)

mes_sel = st.sidebar.selectbox("Mês/Ano", lista_meses)
cat_sel = st.sidebar.selectbox("Categoria", ["Todos"] + sorted(df["categoria"].unique()))
status_sel = st.sidebar.selectbox("Status", ["Todos"] + sorted(df["status"].unique()))

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
ticket = despesas / max(1, len(df_f[df_f["categoria"] == "despesa"]))

c1, c2, c3, c4 = st.columns(4)

with c1: st.markdown(f"<div class='kpi-card'><h4>Receitas</h4><h2>{formato_br(receitas)}</h2></div>", unsafe_allow_html=True)
with c2: st.markdown(f"<div class='kpi-card'><h4>Despesas</h4><h2>{formato_br(despesas)}</h2></div>", unsafe_allow_html=True)
with c3: st.markdown(f"<div class='kpi-card'><h4>Saldo</h4><h2>{formato_br(saldo)}</h2></div>", unsafe_allow_html=True)
with c4: st.markdown(f"<div class='kpi-card'><h4>Ticket Médio</h4><h2>{formato_br(ticket)}</h2></div>", unsafe_allow_html=True)

# =====================
# RESUMO FINANCEIRO
# =====================
taxa = saldo / receitas if receitas else 0

if taxa >= 0.2:
    nivel, texto = "BOA", "Boa margem financeira."
elif taxa > 0:
    nivel, texto = "ATENÇÃO", "Saldo positivo, mas margem apertada."
else:
    nivel, texto = "CRÍTICA", "Despesas superam a receita."

st.markdown(f"""
<div class='card'>
<h4>Resumo Financeiro</h4>
<p><b>Saúde financeira:</b> {nivel}</p>
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
    category_orders={"mes_label": df_mes["mes_label"].tolist()}
)

fig_saldo.update_layout(
    title=dict(
        text="Evolução do Saldo Mensal",
        x=0.02,
        y=0.95,
        xanchor="left",
        yanchor="top"
    ),
    margin=dict(t=80, l=40, r=40, b=40)
)

st.plotly_chart(fig_saldo, use_container_width=True)

# =====================
# TABELA FINAL
# =====================
st.subheader("Tabela Analítica")
st.dataframe(df_f.sort_values("mes_ano_ref", ascending=False), use_container_width=True)
