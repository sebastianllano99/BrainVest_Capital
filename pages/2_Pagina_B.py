import streamlit as st
import pandas as pd
import numpy as np
import os
import zipfile
from scipy.optimize import minimize
import gdown

# -----------------------
# Configuración
# -----------------------
ZIP_FILE_ID = "1Tm2vRpHYbPNUGDVxU4cRbXpYGH_uasW_"
CARPETA_DATOS = "acciones"
ZIP_NAME = "acciones.zip"

RESULT_CSV = "resultado_usuario.csv"
SUMMARY_CSV = "resultado_usuario_summary.csv"

# -----------------------
# Funciones utilitarias
# -----------------------
def download_and_unzip():
    """Descarga y descomprime ZIP desde Drive si no existe"""
    if not os.path.exists(ZIP_NAME):
        url = f"https://drive.google.com/uc?export=download&id={ZIP_FILE_ID}"
        st.info("Descargando base de datos desde Google Drive, por favor espera...")
        gdown.download(url, ZIP_NAME, quiet=False)
    if not os.path.exists(CARPETA_DATOS):
        with zipfile.ZipFile(ZIP_NAME, "r") as zf:
            zf.extractall(CARPETA_DATOS)

def build_tickers_dict():
    """Crea diccionario {TICKER: ruta_csv} detectando subcarpetas y sufijos"""
    archivos = []
    for root, _, files in os.walk(CARPETA_DATOS):
        for f in files:
            if f.lower().endswith(".csv"):
                archivos.append(os.path.join(root, f))
    tickers_dict = {}
    for f in archivos:
        nombre = os.path.splitext(os.path.basename(f))[0].split("_")[0].upper()
        tickers_dict[nombre] = f
    return tickers_dict

def load_price_series(tickers_selected, tickers_dict):
    """Carga series de precios ajustados de los tickers seleccionados"""
    series_list = []
    missing = []
    for t in tickers_selected:
        t_upper = t.upper()
        if t_upper not in tickers_dict:
            missing.append(t)
            continue
        df = pd.read_csv(tickers_dict[t_upper])
        if "Date" not in df.columns or "Adj Close" not in df.columns:
            missing.append(t)
            continue
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
        df = df.sort_values("Date")
        s = df.set_index("Date")["Adj Close"].pct_change().dropna()
        s.name = t_upper
        series_list.append(s)
    return series_list, missing

def anualizar(ret_diario, vol_diario):
    ret_anual = ret_diario * 252
    vol_anual = vol_diario * np.sqrt(252)
    return ret_anual, vol_anual

# -----------------------
# Interfaz
# -----------------------
st.title("Simulación de Portafolio — Markowitz")
st.write("""
Sube un CSV con columnas `Ticker` y `% del Portafolio`.
Al cargar el CSV aparecerá el botón **Iniciar Simulación**. Después de ver resultados, podrás **Finalizar / Guardar**.
""")

# Ejemplo de CSV
ejemplo = pd.DataFrame({"Ticker":["AAPL","MSFT","GOOGL"], "% del Portafolio":[40,30,30]})
st.download_button(" Descargar ejemplo CSV", ejemplo.to_csv(index=False), file_name="ejemplo_portafolio.csv")

# Subida CSV usuario
uploaded = st.file_uploader("Sube tu CSV (Ticker, % del Portafolio)", type=["csv"])
df_user = None
if uploaded:
    try:
        df_user = pd.read_csv(uploaded)
        st.success("CSV cargado")
        st.dataframe(df_user)
    except Exception as e:
        st.error(f"Error leyendo tu CSV: {e}")
        st.stop()

# Descargar y descomprimir ZIP si no existe
download_and_unzip()
tickers_dict = build_tickers_dict()

if df_user is not None:
    if st.button(" Iniciar Simulación"):
        # Detectar columnas
        cols_lower = [c.strip().lower() for c in df_user.columns]
        col_ticker, col_weight = None, None
        for c_orig, c_low in zip(df_user.columns, cols_lower):
            if "tick" in c_low:
                col_ticker = c_orig
            if ("por" in c_low) or ("%" in c_low) or ("peso" in c_low) or ("weight" in c_low):
                col_weight = c_orig
        if col_ticker is None or col_weight is None:
            st.error("Tu CSV debe tener columnas con Ticker y con el % (ej. '% del Portafolio' o 'Peso').")
            st.stop()

        # Normalizar pesos
        df_user[col_weight] = pd.to_numeric(df_user[col_weight], errors="coerce")
        if df_user[col_weight].isnull().any():
            st.error("Algunos pesos no son numéricos.")
            st.stop()
        df_user[col_weight] = df_user[col_weight] / df_user[col_weight].sum()
        tickers_selected = [str(x).strip().upper() for x in df_user[col_ticker].tolist()]
        weights = df_user[col_weight].values

        # Cargar series de precios
        series_list, missing = load_price_series(tickers_selected, tickers_dict)
        if missing:
            st.error(f"No se encontraron históricos para: {missing}")
            st.stop()
        if len(series_list) == 0:
            st.error("No se pudieron cargar series válidas.")
            st.stop()

        # DataFrame retornos
        returns_df = pd.concat(series_list, axis=1, join="inner").dropna()
        mean_returns = returns_df.mean()
        cov_matrix = returns_df.cov()

        # Funciones portafolio
        def portfolio_return(w):
            return np.dot(w, mean_returns)
        def portfolio_vol(w):
            return np.sqrt(np.dot(w.T, np.dot(cov_matrix, w)))

        n_assets = len(tickers_selected)

        # GMVP
        def global_min_variance():
            w0 = np.ones(n_assets)/n_assets
            bounds = [(0,1)]*n_assets
            constraints = ({'type':'eq','fun': lambda w: np.sum(w)-1})
            return minimize(portfolio_vol, w0, method="SLSQP", bounds=bounds, constraints=constraints)
        gmv = global_min_variance()
        gmv_ret_anual, gmv_risk_anual = anualizar(portfolio_return(gmv.x), portfolio_vol(gmv.x))

        # Max Sharpe
        risk_free = 0.0
        def negative_sharpe(w):
            ret = portfolio_return(w)
            vol = portfolio_vol(w)
            return -(ret-risk_free)/vol
        def max_sharpe():
            w0 = np.ones(n_assets)/n_assets
            bounds = [(0,1)]*n_assets
            constraints = ({'type':'eq','fun': lambda w: np.sum(w)-1})
            return minimize(negative_sharpe, w0, method="SLSQP", bounds=bounds, constraints=constraints)
        ms = max_sharpe()
        ms_ret_anual, ms_risk_anual = anualizar(portfolio_return(ms.x), portfolio_vol(ms.x))

        # Mostrar resultados
        st.subheader("Resultados de simulación")
        st.write(f"- Retorno anual GMVP: **{gmv_ret_anual:.2%}**")
        st.write(f"- Volatilidad anual GMVP: **{gmv_risk_anual:.2%}**")
        st.write(f"- Retorno anual Max Sharpe: **{ms_ret_anual:.2%}**")
        st.write(f"- Volatilidad anual Max Sharpe: **{ms_risk_anual:.2%}**")

        # Distribución portafolio
        distrib = pd.DataFrame({
            "Ticker": tickers_selected,
            "% del Portafolio": (weights*100).round(2),
            "Portafolio": "Usuario"
        })
        st.dataframe(distrib)

        # Botón guardar resultados
        if st.button("Finalizar y Guardar Resultados"):
            distrib.to_csv(RESULT_CSV, index=False, encoding="utf-8-sig")
            resumen = pd.DataFrame([{
                "Portafolio": "Usuario",
                "Retorno Anual GMVP": gmv_ret_anual,
                "Riesgo Anual GMVP": gmv_risk_anual,
                "Retorno Anual MaxSharpe": ms_ret_anual,
                "Riesgo Anual MaxSharpe": ms_risk_anual
            }])
            resumen.to_csv(SUMMARY_CSV, index=False, encoding="utf-8-sig")
            st.success(f"Resultados guardados: {RESULT_CSV} y {SUMMARY_CSV}")
