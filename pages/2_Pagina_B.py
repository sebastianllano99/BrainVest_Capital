import streamlit as st
import pandas as pd
import numpy as np
import os, zipfile, gdown, pickle
import matplotlib.pyplot as plt
from scipy.optimize import minimize

# =========================
# CONFIGURACIÓN DE DATOS
# =========================
ZIP_FILE_ID = "19R9zQNq5vmNuP3l2BMvN0V7rmNvegGas"
CARPETA_DATOS = "acciones"
ZIP_NAME = "acciones.zip"
CACHE_FILE = "frontera_global.pkl"  # archivo cacheado

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
# FUNCIÓN PARA CALCULAR FRONTERA GLOBAL
# =========================
def calcular_frontera_global():
    precios_all = pd.DataFrame()
    for t in tickers.keys():
        df_hist = pd.read_csv(tickers[t], parse_dates=["Date"], index_col="Date")
        precios_all[t] = df_hist["Adj Close"]

    returns_all = np.log(precios_all / precios_all.shift(1)).dropna()
    pBar_all = returns_all.mean()
    Sigma_all = returns_all.cov()
    n_assets_all = len(pBar_all)

    def portfolio_return(weights):
        return np.sum(pBar_all * weights)

    def portfolio_volatility(weights):
        return np.sqrt(np.dot(weights.T, np.dot(Sigma_all, weights)))

    def minimize_volatility_all(target_return):
        w0 = np.ones(n_assets_all)/n_assets_all
        bounds = [(0,1)]*n_assets_all
        constraints = (
            {'type':'eq','fun': lambda w: portfolio_return(w)-target_return},
            {'type':'eq','fun': lambda w: np.sum(w)-1}
        )
        return minimize(portfolio_volatility, w0, method="SLSQP", bounds=bounds, constraints=constraints)

    frontier_volatility_all, frontier_returns_all = [], []
    target_returns_all = np.linspace(pBar_all.min(), pBar_all.max(), 30)
    for r in target_returns_all:
        opt = minimize_volatility_all(r)
        if opt.success:
            frontier_volatility_all.append(portfolio_volatility(opt.x))
            frontier_returns_all.append(portfolio_return(opt.x))

    return {
        "vols": np.array(frontier_volatility_all),
        "rets": np.array(frontier_returns_all),
        "pBar": pBar_all,
        "Sigma": Sigma_all
    }


# =========================
# CARGAR O CREAR FRONTERA GLOBAL (cache)
# =========================
if os.path.exists(CACHE_FILE):
    with open(CACHE_FILE, "rb") as f:
        frontera_global = pickle.load(f)
else:
    st.info("⚙️ Calculando frontera eficiente global (solo una vez)...")
    frontera_global = calcular_frontera_global()
    with open(CACHE_FILE, "wb") as f:
        pickle.dump(frontera_global, f)


# =========================
# INTERFAZ DE PÁGINA
# =========================
st.title("📊 Simulación de Portafolios con Markowitz")

st.markdown("### 📥 Descargar ejemplo de CSV")
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

uploaded_file = st.file_uploader("📂 Sube tu archivo CSV de tu equipo", type=["csv"])

if uploaded_file is not None:
    df_equipo = pd.read_csv(uploaded_file)
    st.success("✅ Archivo cargado correctamente.")
    st.dataframe(df_equipo.head())

    if "Ticker" not in df_equipo.columns or "Porcentaje" not in df_equipo.columns:
        st.error("El CSV debe contener las columnas `Ticker` y `Porcentaje`.")
        st.stop()

    if abs(df_equipo["Porcentaje"].sum() - 100) > 0.01:
        st.error("❌ La suma de los porcentajes debe ser 100%.")
        st.stop()

    tickers_equipo = df_equipo["Ticker"].unique().tolist()

    if st.button("🚀 Iniciar Simulación"):
        # =====================
        # Cálculo del portafolio del jugador
        # =====================
        precios_player = pd.DataFrame()
        for t in tickers_equipo:
            if t in tickers:
                df_hist = pd.read_csv(tickers[t], parse_dates=["Date"], index_col="Date")
                precios_player[t] = df_hist["Adj Close"]
            else:
                st.warning(f"No se encontró histórico para {t}")

        returns_player = np.log(precios_player / precios_player.shift(1)).dropna()
        pBar_player = returns_player.mean()
        Sigma_player = returns_player.cov()
        n_assets_player = len(pBar_player)

        def portfolio_return(weights): return np.sum(pBar_player * weights)
        def portfolio_volatility(weights): return np.sqrt(np.dot(weights.T, np.dot(Sigma_player, weights)))

        # GMVP jugador
        def global_min_variance_player():
            w0 = np.ones(n_assets_player)/n_assets_player
            bounds = [(0,1)]*n_assets_player
            constraints = ({'type':'eq','fun': lambda w: np.sum(w)-1})
            return minimize(portfolio_volatility, w0, method="SLSQP", bounds=bounds, constraints=constraints)

        gmv_player = global_min_variance_player()

        # Max Sharpe jugador
        risk_free = 0.0
        def negative_sharpe(weights):
            ret = portfolio_return(weights)
            vol = portfolio_volatility(weights)
            return -(ret-risk_free)/vol

        def max_sharpe_player():
            w0 = np.ones(n_assets_player)/n_assets_player
            bounds = [(0,1)]*n_assets_player
            constraints = ({'type':'eq','fun': lambda w: np.sum(w)-1})
            return minimize(negative_sharpe, w0, method="SLSQP", bounds=bounds, constraints=constraints)

        ms_player = max_sharpe_player()

        # =====================
        # Gráfico comparativo
        # =====================
        st.subheader("📊 Comparativa con Frontera Eficiente Real")
        fig, ax = plt.subplots(figsize=(8,5))

        ax.plot(frontera_global["vols"]*np.sqrt(252), frontera_global["rets"]*252, 
                'b--', label="Frontera Eficiente Global")

        ax.scatter(portfolio_volatility(gmv_player.x)*np.sqrt(252), 
                   portfolio_return(gmv_player.x)*252, 
                   c="red", marker="o", s=80, label="GMVP Jugador")

        ax.scatter(portfolio_volatility(ms_player.x)*np.sqrt(252), 
                   portfolio_return(ms_player.x)*252, 
                   c="green", marker="*", s=120, label="Max Sharpe Jugador")

        ax.set_xlabel("Volatilidad Anual")
        ax.set_ylabel("Retorno Anual Esperado")
        ax.legend()
        st.pyplot(fig)
