import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="Portafolio Óptimo", layout="wide")
st.title("📊 Análisis de Portafolios")

# --- ID de la hoja de Google Sheets ---
SHEET_ID = "19xIH0ipdUYg0XELl4mHBLcNbmQ5vxQcL"
url_excel = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=xlsx"

# --- Leer todas las hojas desde Google Sheets ---
st.info("📥 Cargando base de datos desde Google Drive, por favor espera...")
df_dict = pd.read_excel(url_excel, sheet_name=None, engine="openpyxl")

# --- Extraer hojas ---
df_res = df_dict.get("Resumen_Portafolios")   # Resultados globales
df_gmvp = df_dict.get("GMVP")
df_ms = df_dict.get("Max_Sharpe")

# --- Formatear valores en pesos ---
def formato_pesos(x):
    return f"${x:,.0f}"

if df_res is not None and "Ganancia Anual" in df_res.columns:
    df_res["Ganancia Anual"] = df_res["Ganancia Anual"].apply(formato_pesos)

# --- Mostrar tabla de resultados ---
st.subheader("📑 Resultados Globales")
st.dataframe(df_res)

# --- Selector de portafolio ---
portafolios = df_res["Portafolio"].unique()
seleccionado = st.selectbox("🔎 Selecciona un portafolio", portafolios)

datos_sel = df_res[df_res["Portafolio"] == seleccionado].iloc[0]

st.subheader(f"🌟 Portafolio: {seleccionado}")

# --- Mostrar métricas con color verde ---
col1, col2, col3 = st.columns(3)
col1.markdown(f"<p style='color:#00FF9D; font-size:20px;'>Retorno Anual:<br>{datos_sel['Retorno Anual']:.2%}</p>", unsafe_allow_html=True)
col2.markdown(f"<p style='color:#00FF9D; font-size:20px;'>Riesgo Anual:<br>{datos_sel['Riesgo Anual']:.2%}</p>", unsafe_allow_html=True)
col3.markdown(f"<p style='color:#00FF9D; font-size:20px;'>Ganancia Anual:<br>{datos_sel['Ganancia Anual']}</p>", unsafe_allow_html=True)

# --- Distribución del portafolio ---
st.write(f"### 📌 Distribución de Activos – {seleccionado}")

if seleccionado == "GMVP" and df_gmvp is not None:
    comp_sel = df_gmvp
elif seleccionado == "Max Sharpe" and df_ms is not None:
    comp_sel = df_ms
else:
    comp_sel = None

if comp_sel is not None:
    fig1 = px.bar(
        comp_sel.sort_values("Peso %", ascending=True),
        x="Peso %", y="Ticker",
        orientation="h", text="Peso %",
        title=f"Distribución de Activos - {seleccionado}",
        color="Peso %", color_continuous_scale=px.colors.sequential.Teal
    )
    fig1.update_traces(texttemplate="%{text:.2f}%", textposition="outside")
    fig1.update_layout(
        template="plotly_dark",
        plot_bgcolor="#0E1117", paper_bgcolor="#0E1117",
        font=dict(color="white")
    )
    st.plotly_chart(fig1, use_container_width=True)
else:
    st.warning(f"⚠️ No hay datos de composición para {seleccionado}")

# --- Comparación Retorno vs Riesgo ---
st.write("### 🌐 Comparación Portafolios")

fig2 = go.Figure()

# Todos los portafolios simulados
fig2.add_trace(go.Scatter(
    x=df_res["Riesgo Anual"], y=df_res["Retorno Anual"] * 100,
    mode="markers",
    marker=dict(size=10, color="#00CFFF", line=dict(color="white", width=0.5)),
    name="Portafolios Simulados"
))

# GMVP
if "GMVP" in df_res["Portafolio"].values:
    mvp = df_res[df_res["Portafolio"] == "GMVP"]
    fig2.add_trace(go.Scatter(
        x=mvp["Riesgo Anual"], y=mvp["Retorno Anual"] * 100,
        mode="markers", marker=dict(size=14, color="#FF4B4B", symbol="star"),
        name="GMVP"
    ))

# Max Sharpe
if "Max Sharpe" in df_res["Portafolio"].values:
    ms = df_res[df_res["Portafolio"] == "Max Sharpe"]
    fig2.add_trace(go.Scatter(
        x=ms["Riesgo Anual"], y=ms["Retorno Anual"] * 100,
        mode="markers", marker=dict(size=14, color="#00FF9D", symbol="star"),
        name="Max Sharpe"
    ))

# Seleccionado
sel = df_res[df_res["Portafolio"] == seleccionado]
fig2.add_trace(go.Scatter(
    x=sel["Riesgo Anual"], y=sel["Retorno Anual"] * 100,
    mode="markers", marker=dict(size=18, color="gold", symbol="star"),
    name=f"Seleccionado: {seleccionado}"
))

fig2.update_layout(
    template="plotly_dark",
    plot_bgcolor="#0E1117", paper_bgcolor="#0E1117",
    font=dict(color="white"),
    title="Comparación entre Portafolios",
    xaxis_title="Riesgo Anual",
    yaxis=dict(
        title="Retorno Anual (%)",
        tickformat=".2f"
    )
)

st.plotly_chart(fig2, use_container_width=True)

# --- Frontera eficiente ---
st.write("### 📈 Frontera Eficiente - Markowitz")

# Escalar retornos diarios a porcentaje
df_res["Retorno Diario %"] = df_res["Retorno Diario"] * 100

fig3 = go.Figure()

# Frontera eficiente
fig3.add_trace(go.Scatter(
    x=df_res["Riesgo Diario"], y=df_res["Retorno Diario %"],
    mode="lines+markers", line=dict(color="#00CFFF", width=2),
    name="Frontera Eficiente"
))

# GMVP
if df_gmvp is not None:
    gmvp = df_gmvp.iloc[0]
    fig3.add_trace(go.Scatter(
        x=[gmvp["Riesgo Portafolio Diario"]],
        y=[gmvp["Retorno Esperado Diario"] * 100],
        mode="markers+text",
        marker=dict(color="#FF4B4B", size=16, symbol="star"),
        text=["GMVP"], textposition="top right",
        name="GMVP"
    ))

# Max Sharpe
if df_ms is not None:
    ms = df_ms.iloc[0]
    fig3.add_trace(go.Scatter(
        x=[ms["Riesgo Portafolio Diario"]],
        y=[ms["Retorno Esperado Diario"] * 100],
        mode="markers+text",
        marker=dict(color="#00FF9D", size=16, symbol="star"),
        text=["Max Sharpe"], textposition="top right",
        name="Max Sharpe"
    ))

# Ajustes de estilo
fig3.update_layout(
    template="plotly_dark",
    plot_bgcolor="#0E1117", paper_bgcolor="#0E1117",
    font=dict(color="white"),
    title="Frontera Eficiente - Markowitz",
    xaxis_title="Riesgo (Volatilidad Diaria)",
    yaxis=dict(
        title="Retorno Esperado Diario (%)",
        tickformat=".2f"
    )
)

st.plotly_chart(fig3, use_container_width=True)

# --- Estilo global para el selectbox ---
st.markdown("""
    <style>
    div[data-baseweb="select"] span { color: #00CFFF !important; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)


