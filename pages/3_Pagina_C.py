import streamlit as st
import os
import pandas as pd
import numpy as np
from scipy.optimize import minimize
import plotly.express as px

# ==============================
# Configuración de página
# ==============================
st.set_page_config(page_title="Portafolio Óptimo", layout="wide", initial_sidebar_state="collapsed")

st.title("📊 Optimización Automática de Portafolio - Markowitz")
st.info("Analizando todas las acciones disponibles en la app... Esto puede tardar unos segundos.")

# ==============================
# Carpeta de CSV
# ==============================
CARPETA_DATOS = "acciones"
archivos = [os.path.join(root, f) for root, _, files in os.walk(CARPETA_DATOS) for f in files if f.endswith(".csv")]
archivos = sorted(archivos)

if not archivos:
    st.error("No se encontraron archivos CSV en la carpeta.")
    st.stop()

# ==============================
# Construir DataFrame con precios ajustados (vectorizado)
# ==============================
with st.spinner("Cargando datos de todas las acciones..."):
    lista_df = [
        pd.read_csv(f, usecols=["Date","Adj Close"], parse_dates=["Date"])
        .rename(columns={"Adj Close": os.path.basename(f).split("_")[0]})
        .set_index("Date")
        for f in archivos
    ]

    df_all = pd.concat(lista_df, axis=1).sort_index().dropna()

# ==============================
# Rendimientos logarítmicos
# ==============================
log_returns = np.log(df_all / df_all.shift(1)).dropna()
pBar = log_returns.mean()
Sigma = log_returns.cov()

# ==============================
# Funciones de optimización
# ==============================
def riskFunction(w):
    return np.dot(w.T, np.dot(Sigma, w))

def checkMinimumReturn(w):
    return np.sum(pBar * w) - 0.02  # retorno mínimo requerido

def checkSumToOne(w):
    return np.sum(w) - 1

# ==============================
# Optimización
# ==============================
n_assets = len(pBar)
w0 = np.ones(n_assets) / n_assets
bounds = [(0, 1)] * n_assets
constraints = (
    {'type': 'eq', 'fun': checkMinimumReturn},
    {'type': 'eq', 'fun': checkSumToOne}
)

with st.spinner("Calculando portafolio óptimo..."):
    w_opt = minimize(riskFunction, w0, method='SLSQP', bounds=bounds, constraints=constraints)

if not w_opt.success:
    st.error("No se encontró una solución óptima. Intenta nuevamente.")
    st.stop()

w_scipy = w_opt.x
risk_scipy = riskFunction(w_scipy)
expected_return = np.sum(pBar * w_scipy)

# ==============================
# Mostrar resultados
# ==============================
resultados = pd.DataFrame({
    "Acción": df_all.columns,
    "Peso Óptimo": w_scipy
})
resultados = resultados[resultados["Peso Óptimo"] > 0.001]
resultados["Peso Óptimo (%)"] = resultados["Peso Óptimo"] * 100

st.subheader("📌 Portafolio Óptimo - Pesos de Acciones")
st.dataframe(resultados.sort_values("Peso Óptimo (%)", ascending=False), use_container_width=True)

st.write(f"📈 Retorno esperado: **{expected_return:.2%}**")
st.write(f"⚖️ Riesgo (varianza): **{risk_scipy:.4f}**")

# ==============================
# Gráfico de pastel
# ==============================
st.subheader("📊 Distribución del Portafolio")
fig_pie = px.pie(resultados.sort_values("Peso Óptimo (%)", ascending=False),
                 names="Acción",
                 values="Peso Óptimo (%)",
                 title="Composición del Portafolio Óptimo",
                 color_discrete_sequence=px.colors.qualitative.Dark24)

fig_pie.update_traces(textinfo="label+percent", pull=[0.05]*len(resultados))
fig_pie.update_layout(showlegend=True)
st.plotly_chart(fig_pie, use_container_width=True)
