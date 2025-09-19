import streamlit as st
import os
import pandas as pd
import numpy as np
from scipy.optimize import minimize

# ==============================
# Configuración
# ==============================
CAPITAL_TOTAL = 500_000_000  # COP
CARPETA_DATOS = "acciones"
rMin = 0.02  # retorno mínimo esperado

st.title("📊 Portafolio Óptimo - Markowitz")
st.info("Calculando el portafolio óptimo para todas las acciones disponibles...")

# ==============================
# Leer CSVs y construir DataFrame con Adj Close
# ==============================
archivos = [os.path.join(root, f) for root, _, files in os.walk(CARPETA_DATOS) for f in files if f.endswith(".csv")]
archivos = sorted(archivos)
if not archivos:
    st.error("No se encontraron archivos CSV en la carpeta.")
    st.stop()

df_all = pd.DataFrame()
tickers = []

for ruta in archivos:
    df_temp = pd.read_csv(ruta, parse_dates=["Date"]).sort_values("Date").set_index("Date")
    ticker = os.path.basename(ruta).split("_")[0]
    tickers.append(ticker)
    df_all[ticker] = df_temp["Adj Close"]

df_all = df_all.dropna()  # eliminar filas incompletas

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
    return np.sum(pBar * w) - rMin

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

w_opt = minimize(riskFunction, w0, method='SLSQP', bounds=bounds, constraints=constraints)

if not w_opt.success:
    st.error("No se encontró un portafolio óptimo. Intenta nuevamente.")
    st.stop()

# ==============================
# Resultados
# ==============================
w_scipy = w_opt.x
risk_scipy = riskFunction(w_scipy)
expected_return = np.sum(pBar * w_scipy)

# Tabla de pesos y montos
resultados = pd.DataFrame({
    "Acción": tickers,
    "Peso Óptimo": w_scipy
})
resultados = resultados[resultados["Peso Óptimo"] > 0.001]  # filtrar muy pequeños
resultados["Peso Óptimo (%)"] = resultados["Peso Óptimo"] * 100
resultados["Monto Invertido (COP)"] = (resultados["Peso Óptimo"] * CAPITAL_TOTAL).round(0).astype(int)

# ==============================
# Mostrar resultados
# ==============================
st.subheader("📌 Portafolio Óptimo")
st.dataframe(resultados.sort_values("Peso Óptimo (%)", ascending=False), use_container_width=True)

st.write(f"📈 Retorno esperado: **{expected_return:.2%}**")
st.write(f"⚖️ Riesgo (varianza): **{risk_scipy:.4f}**")
st.write(f"💰 Total invertido: **{resultados['Monto Invertido (COP)'].sum():,.0f} COP**")
