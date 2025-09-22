import streamlit as st
import pandas as pd
import numpy as np
import os
import zipfile
import io
import gdown
from scipy.optimize import minimize

# =========================
# CONFIGURACIÓN
# =========================
ZIP_FILE_ID = "1Tm2vRpHYbPNUGDVxU4cRbXpYGH_uasW_"  # ID de tu zip en Drive
ZIP_NAME = "acciones.zip"
CARPETA_DATOS = "acciones"

# =========================
# FUNCIONES
# =========================
def download_and_extract_zip():
    """Descarga y extrae el ZIP desde Google Drive"""
    url = f"https://drive.google.com/uc?id={ZIP_FILE_ID}"
    output = ZIP_NAME
    if not os.path.exists(output):
        gdown.download(url, output, quiet=False)

    if not os.path.exists(CARPETA_DATOS):
        os.makedirs(CARPETA_DATOS, exist_ok=True)
        with zipfile.ZipFile(output, "r") as zip_ref:
            zip_ref.extractall(CARPETA_DATOS)


def load_price_data(ticker):
    """Carga precios de un ticker desde los CSV del ZIP (archivos nombrados solo como ticker.csv)."""
    file_path = os.path.join(CARPETA_DATOS, f"{ticker}.csv")
    if not os.path.exists(file_path):
        st.error(f"❌ No se encontró el archivo para {ticker}")
        return None
    try:
        df = pd.read_csv(file_path)
        if "Date" not in df.columns or "Adj Close" not in df.columns:
            st.error(f"⚠️ {ticker}.csv no tiene las columnas necesarias (Date, Adj Close).")
            return None
        df["Date"] = pd.to_datetime(df["Date"])
        df = df.sort_values("Date")
        return df[["Date", "Adj Close"]]
    except Exception as e:
        st.error(f"Error cargando {ticker}: {e}")
        return None


def calculate_portfolio_performance(weights, mean_returns, cov_matrix):
    returns = np.sum(mean_returns * weights) * 252
    risk = np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights))) * np.sqrt(252)
    return returns, risk


def simulate_portfolios(returns, num_portfolios=10000):
    mean_returns = returns.mean()
    cov_matrix = returns.cov()
    results = {"Return": [], "Risk": [], "Sharpe": [], "Weights": []}

    for _ in range(num_portfolios):
        weights = np.random.random(len(mean_returns))
        weights /= np.sum(weights)
        ret, risk = calculate_portfolio_performance(weights, mean_returns, cov_matrix)
        sharpe = ret / risk if risk != 0 else 0
        results["Return"].append(ret)
        results["Risk"].append(risk)
        results["Sharpe"].append(sharpe)
        results["Weights"].append(weights)

    df = pd.DataFrame(results)
    return df


def optimize_portfolio(returns, objective="sharpe"):
    mean_returns = returns.mean()
    cov_matrix = returns.cov()
    num_assets = len(mean_returns)

    def neg_sharpe(weights):
        ret, risk = calculate_portfolio_performance(weights, mean_returns, cov_matrix)
        return -(ret / risk)

    def portfolio_volatility(weights):
        return calculate_portfolio_performance(weights, mean_returns, cov_matrix)[1]

    constraints = ({"type": "eq", "fun": lambda x: np.sum(x) - 1})
    bounds = tuple((0, 1) for _ in range(num_assets))
    init_guess = num_assets * [1. / num_assets]

    if objective == "sharpe":
        result = minimize(neg_sharpe, init_guess, method="SLSQP", bounds=bounds, constraints=constraints)
    else:  # GMVP
        result = minimize(portfolio_volatility, init_guess, method="SLSQP", bounds=bounds, constraints=constraints)

    return result.x if result.success else None


# =========================
# INTERFAZ STREAMLIT
# =========================
st.title("📊 Página 2 - Simulación de Portafolios")

st.markdown("""
En esta página podrás cargar tu **CCV** (archivo CSV con la distribución de tu portafolio)  
y simular los resultados frente al **GMVP** (Global Minimum Variance Portfolio) y el  
**MaxSharpe** (portafolio con máximo Sharpe).
""")

# Archivo de ejemplo
ejemplo = pd.DataFrame({
    "Ticker": ["AAPL", "MSFT", "GOOG"],
    "% del Portafolio": [0.4, 0.35, 0.25]
})
st.download_button(
    label="⬇️ Descargar ejemplo de CCV",
    data=ejemplo.to_csv(index=False).encode("utf-8"),
    file_name="ejemplo_ccv.csv",
    mime="text/csv"
)

# Subida de archivo CCV
ccv_file = st.file_uploader("📂 Sube tu archivo CCV", type=["csv"])

if ccv_file:
    st.success("✅ Archivo cargado correctamente.")
    user_ccv = pd.read_csv(ccv_file)

    if "Ticker" not in user_ccv.columns or "% del Portafolio" not in user_ccv.columns:
        st.error("❌ El archivo debe tener columnas: 'Ticker' y '% del Portafolio'")
    else:
        if st.button("🚀 Iniciar Simulación"):
            try:
                download_and_extract_zip()

                tickers = user_ccv["Ticker"].tolist()
                weights = user_ccv["% del Portafolio"].values

                # Normalizar pesos
                weights = weights / np.sum(weights)

                # Cargar datos históricos
                prices = {}
                for ticker in tickers:
                    df = load_price_data(ticker)
                    if df is not None:
                        prices[ticker] = df.set_index("Date")["Adj Close"]

                if len(prices) == 0:
                    st.error("❌ No se encontraron datos históricos en la carpeta extraída.")
                else:
                    data = pd.concat(prices.values(), axis=1)
                    data.columns = prices.keys()
                    returns = data.pct_change().dropna()

                    # Simulación
                    sim_results = simulate_portfolios(returns)

                    # Optimización
                    max_sharpe_weights = optimize_portfolio(returns, "sharpe")
                    gmvp_weights = optimize_portfolio(returns, "gmvp")

                    st.subheader("📌 Resultados de la Simulación")
                    st.write("**Distribución del usuario:**")
                    st.dataframe(user_ccv)

                    st.write("**Portafolio Máx. Sharpe:**")
                    st.write(dict(zip(tickers, np.round(max_sharpe_weights, 4))))

                    st.write("**Portafolio GMVP:**")
                    st.write(dict(zip(tickers, np.round(gmvp_weights, 4))))

                    st.session_state["user_results"] = {
                        "tickers": tickers,
                        "weights": weights,
                        "max_sharpe": max_sharpe_weights,
                        "gmvp": gmvp_weights
                    }

                    st.success("✅ Simulación finalizada. Puedes avanzar a la página 3.")
            except Exception as e:
                st.error(f"❌ Error en la simulación: {e}")
