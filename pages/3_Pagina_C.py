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
rMin = 0.02  # Retorno mínimo esperado
UMBRAL_ANALITICO = 20  # Si hay más de 20 acciones, usar método analítico

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
n_assets = len(pBar)

# ==============================
# Función analítica
# ==============================
def ourMarkowitzSingleEquationSolver(rMin, Sigma, pBar):
    ones = np.ones(len(Sigma))
    SigmaInv = np.linalg.inv(Sigma)
    a = np.dot(pBar.T, np.dot(SigmaInv, pBar))
    b = np.dot(pBar.T, np.dot(SigmaInv, ones))
    c = np.dot(ones.T, np.dot(SigmaInv, ones))
    return (1 / (a * c - b**2)) * np.dot(
        SigmaInv,
        ((c * rMin - b) * pBar + (a - b * rMin) * ones)
    )

# Funciones para scipy
def riskFunction(w):
    return np.dot(w.T, np.dot(Sigma, w))

def checkMinimumReturn(w):
    return np.sum(pBar * w) - rMin

def checkSumToOne(w):
    return np.sum(w) - 1

# ==============================
# Elegir método según cantidad de acciones
# ==============================
if n_assets > UMBRAL_ANALITICO:
    st.info(f"Se detectaron {n_assets} acciones, usando método analítico rápido.")
    w_opt = ourMarkowitzSingleEquationSolver(rMin, Sigma, pBar)
else:
    st.info(f"Se detectaron {n_assets} acciones, usando optimización con scipy.minimize.")
    w0 = np.ones(n_assets) / n_assets
    bounds = [(0, 1)] * n_assets
    constraints = (
        {'type': 'eq', 'fun': checkMinimumReturn},
        {'type': 'eq', 'fun': checkSumToOne}
    )
    sol = minimize(riskFunction, w0, method='SLSQP', bounds=bounds, constraints=constraints)
    if not sol.success:
        st.error("No se encontró solución óptima.")
        st.stop()
    w_opt = sol.x

# ==============================
# Calcular riesgo y retorno
# ==============================
risk_opt = np.dot(w_opt.T, np.dot(Sigma, w_opt))
expected_return = np.sum(pBar * w_opt)

# ==============================
# Resultados
# ==============================
resultados = pd.DataFrame({
    "Acción": tickers,
    "Peso Óptimo": w_opt
})
resultados = resultados[resultados["Peso Óptimo"] > 0.001]  # filtrar pesos insignificantes
resultados["Peso Óptimo (%)"] = resultados["Peso Óptimo"] * 100
resultados["Monto Invertido (COP)"] = (resultados["Peso Óptimo"] * CAPITAL_TOTAL).round(0).astype(int)

st.subheader("📌 Portafolio Óptimo")
st.dataframe(resultados.sort_values("Peso Óptimo (%)", ascending=False), use_container_width=True)

st.write(f"📈 Retorno esperado: **{expected_return:.2%}**")
st.write(f"⚖️ Riesgo (varianza): **{risk_opt:.4f}**")
st.write(f"💰 Total invertido: **{resultados['Monto Invertido (COP)'].sum():,.0f} COP**")
