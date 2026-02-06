import pandas as pd
import streamlit as st
import plotly.express as px

# =====================
# CONFIGURAÇÃO GERAL
# =====================
st.set_page_config(page_title="Dashboard Financeiro", layout="wide")

# =====================
# FUNÇÕES DE LOGIN
# =====================
def autenticar(usuario, senha):
    users = st.secrets["auth"]["users"]
    passwords = st.secrets["auth"]["passwords"]

    if usuario in users:
        idx = users.index(usuario)
        return senha == passwords[idx]
    return False


def tela_login():
    st.title("Acesso Restrito")
    st.write("Faça login para acessar o dashboard")

    usuario = st.text_input("Usuário")
    senha = st.text_input("Senha", type="password")

    if st.button("Entrar"):
        if autenticar(usuario, senha):
            st.session_state["autenticado"] = True
            st.session_state["usuario"] = usuario
            st.rerun()
        else:
            st.error("Usuário ou senha inválidos")


# =====================
# CONTROLE DE SESSÃO
# =====================
if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False

if not st.session_state["autenticado"]:
    tela_login()
    st.stop()

# =====================
# BOTÃO LOGOUT
# =====================
with st.sidebar:
    st.write(f"Usuário: {st.session_state['usuario']}")
    if st.button("Sair"):
        st.session_state["autenticado"] = False
        st.session_state.pop("usuario", None)
        st.rerun()

# =====================
# CSS
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
# FUNÇÃO FORMATO BR
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
# DESPESAS POR SUBCATEGORIA
# =====================
st.subheader("Onde o dinheiro está indo")

df_cat = (
    df_f[df_f["categoria"] == "despesa"]
    .groupby("subcategoria")["valor"]
    .sum()
    .reset_index()
    .sort_values("valor", ascending=False)
)

st.plotly_chart(px.bar(df_cat, x="subcategoria", y="valor"), use_container_width=True)
st.plotly_chart(px.pie(df_cat, names="subcategoria", values="valor"), use_container_width=True)

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

st.plotly_chart(px.bar(df_det, x="detalhe", y="valor"), use_container_width=True)

# =====================
# STATUS
# =====================
st.subheader("Status dos Lançamentos")

df_status = df_f.groupby("status")["valor"].sum().reset_index()
st.plotly_chart(px.pie(df_status, names="status", values="valor"), use_container_width=True)

# =====================
# TABELA FINAL
# =====================
st.subheader("Tabela Analítica")
st.dataframe(df_f.sort_values("mes_ano_ref", ascending=False), use_container_width=True)
