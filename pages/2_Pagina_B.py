import streamlit as st
import pandas as pd
import numpy as np
import os, zipfile, gdown
import matplotlib.pyplot as plt
from scipy.optimize import minimize

# =========================
# CONFIGURACIÓN DE DATOS
# =========================
ZIP_FILE_ID = "19R9zQNq5vmNuP3l2BMvN0V7rmNvegGas"
CARPETA_DATOS = "acciones"
ZIP_NAME = "acciones.zip"

def download_and_unzip():
    url = f"https://drive.google.com/uc?export=download&id={ZIP_FILE_ID}"
    st.info("Descargando base de datos desde Google Drive, por favor espera...")
    gdown.download(url, ZIP_NAME, quiet=False)
    with zipfile.ZipFile(ZIP_NAME, "r") as zf:
        zf.extractall(CARPETA_DATOS)

if not os.path.exists(CARPETA_DATOS) or len(os.listdir(CARPETA_DATOS)) == 0:
    download_and_unzip()

# Buscar CSV en la carpeta de históricos
archivos = []
for root, _, files in os.walk(CARPETA_DATOS):
    for f in files:
        if f.endswith(".csv"):
            archivos.append(os.path.join(root, f))

archivos = sorted(archivos)

if not archivos:
    st.error("No se encontraron archivos CSV en la carpeta de históricos.")
    st.stop()

# Diccionario {ticker: ruta al csv}
tickers = {os.path.basename(f).split("_")[0]: f for f in archivos}

# =========================
# INTERFAZ DE PÁGINA 2
# =========================
st.title("📊 Simulación de Portafolios con Markowitz")

st.write("Sube el archivo CSV con la selección de tu equipo. El sistema calculará el portafolio óptimo usando los datos históricos.")

# -------------------------
# CSV de guía para descargar
# -------------------------
st.markdown("### 📥 Descarga un CSV de ejemplo con la estructura correcta")
sample_df = pd.DataFrame({
    "Ticker": ["AAPL", "MSFT", "GOOG", "AMZN"],
    "Porcentaje": [40, 30, 20, 10]
})
st.download_button(
    label="⬇️ Descargar CSV de ejemplo",
    data=sample_df.to_csv(index=False).encode("utf-8"),
    file_name="ejemplo_portafolio.csv",
    mime="text/csv",
)
st.info("El CSV debe contener las columnas **Ticker** y **Porcentaje**, y la suma de porcentajes debe ser 100%.")

# -------------------------
# Subida del CSV del equipo
# -------------------------
uploaded_file = st.file_uploader("📂 Sube tu archivo CSV de tu equipo", type=["csv"])

if uploaded_file is not None:
    df_equipo = pd.read_csv(uploaded_file)
    st.success("✅ Archivo cargado correctamente.")
    st.write("Vista previa de tu selección:")
    st.dataframe(df_equipo.head())

    # Validación básica
    if "Ticker" not in df_equipo.columns or "Porcentaje" not in df_equipo.columns:
        st.error("El CSV debe contener las columnas `Ticker` y `Porcentaje`.")
        st.stop()

    if abs(df_equipo["Porcentaje"].sum() - 100) > 0.01:
        st.error("❌ La suma de los porcentajes debe ser 100%.")
        st.stop()

    tickers_equipo = df_equipo["Ticker"].unique().tolist()
    st.info(f"Tu equipo seleccionó los siguientes activos: {', '.join(tickers_equipo)}")

    # =====================
    # BOTÓN PARA SIMULACIÓN
    # =====================
    if st.button("🚀 Iniciar Simulación"):
        precios = pd.DataFrame()

        # Leer históricos de los tickers seleccionados
        for t in tickers_equipo:
            if t in tickers:
                df_hist = pd.read_csv(tickers[t], parse_dates=["Date"], index_col="Date")
                precios[t] = df_hist["Adj Close"]
            else:
                st.warning(f"No se encontró histórico para {t}")

        if precios.empty:
            st.error("No se encontraron datos históricos para los tickers seleccionados.")
            st.stop()

        # =====================
        # Cálculo de retornos diarios y anualización
        # =====================
        TRADING_DAYS = 252  # días de trading por año
        returns = np.log(precios / precios.shift(1)).dropna()
        pBar = returns.mean()
        Sigma = returns.cov()
        n_assets = len(pBar)

        # =====================
        # Funciones Markowitz
        # =====================
        def portfolio_return(weights):
            return np.sum(pBar * weights)

        def portfolio_volatility(weights):
            return np.sqrt(np.dot(weights.T, np.dot(Sigma, weights)))

        def minimize_volatility(target_return):
            w0 = np.ones(n_assets)/n_assets
            bounds = [(0,1)]*n_assets
            constraints = (
                {'type':'eq','fun': lambda w: portfolio_return(w)-target_return},
                {'type':'eq','fun': lambda w: np.sum(w)-1}
            )
            return minimize(portfolio_volatility, w0, method="SLSQP", bounds=bounds, constraints=constraints)

        # Frontera eficiente
        frontier_volatility, frontier_returns = [], []
        target_returns = np.linspace(pBar.min(), pBar.max(), 30)
        for r in target_returns:
            opt = minimize_volatility(r)
            if opt.success:
                frontier_volatility.append(portfolio_volatility(opt.x) * np.sqrt(TRADING_DAYS))
                frontier_returns.append(portfolio_return(opt.x) * TRADING_DAYS)

        # Portafolio de mínima varianza (GMVP)
        def global_min_variance():
            w0 = np.ones(n_assets)/n_assets
            bounds = [(0,1)]*n_assets
            constraints = ({'type':'eq','fun': lambda w: np.sum(w)-1})
            return minimize(portfolio_volatility, w0, method="SLSQP", bounds=bounds, constraints=constraints)

        gmv = global_min_variance()

        # Portafolio de máxima razón de Sharpe
        risk_free = 0.0
        def negative_sharpe(weights):
            ret = portfolio_return(weights) * TRADING_DAYS
            vol = portfolio_volatility(weights) * np.sqrt(TRADING_DAYS)
            return -(ret - risk_free) / vol

        def max_sharpe():
            w0 = np.ones(n_assets)/n_assets
            bounds = [(0,1)]*n_assets
            constraints = ({'type':'eq','fun': lambda w: np.sum(w)-1})
            return minimize(negative_sharpe, w0, method="SLSQP", bounds=bounds, constraints=constraints)

        ms = max_sharpe()

        # =====================
        # Mostrar Resultados Anualizados
        # =====================
        st.subheader("📈 Resultados de la Simulación (Anualizados)")

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Portafolio de Mínima Varianza (GMVP):**")
            st.write("Pesos:", dict(zip(pBar.index, np.round(gmv.x, 3))))
            st.write("Retorno esperado anual:", round(portfolio_return(gmv.x)*TRADING_DAYS*100, 2), "%")
            st.write("Volatilidad anual:", round(portfolio_volatility(gmv.x)*np.sqrt(TRADING_DAYS)*100, 2), "%")

        with col2:
            st.markdown("**Portafolio de Máxima Razón de Sharpe:**")
            st.write("Pesos:", dict(zip(pBar.index, np.round(ms.x, 3))))
            st.write("Retorno esperado anual:", round(portfolio_return(ms.x)*TRADING_DAYS*100, 2), "%")
            st.write("Volatilidad anual:", round(portfolio_volatility(ms.x)*np.sqrt(TRADING_DAYS)*100, 2), "%")

        # =====================
        # Gráfico Frontera Eficiente
        # =====================
        st.subheader("📊 Frontera Eficiente")
        fig, ax = plt.subplots(figsize=(8,5))
        ax.plot(frontier_volatility, frontier_returns, 'b--', label="Frontera Eficiente")
        ax.scatter(portfolio_volatility(gmv.x)*np.sqrt(TRADING_DAYS), portfolio_return(gmv.x)*TRADING_DAYS, c="red", marker="o", s=80, label="GMVP")
        ax.scatter(portfolio_volatility(ms.x)*np.sqrt(TRADING_DAYS), portfolio_return(ms.x)*TRADING_DAYS, c="green", marker="*", s=120, label="Max Sharpe")
        ax.set_xlabel("Volatilidad Anual")
        ax.set_ylabel("Retorno Esperado Anual")
        ax.legend()
        st.pyplot(fig)

        # =====================
        # Botón para avanzar
        # =====================
        if st.button("✅ Finalizar Simulación y continuar a Página 3"):
            st.session_state["simulacion_finalizada"] = True
            st.success("Simulación finalizada. Ahora puedes ir a la Página 3.")
