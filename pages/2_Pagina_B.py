# app_markowitz.py
import streamlit as st
import pandas as pd
import numpy as np
import os
import zipfile
import io
import glob
from scipy.optimize import minimize

# Intento usar gdown si está instalado; si no, fallback a requests
try:
    import gdown
    _HAS_GDOWN = True
except Exception:
    _HAS_GDOWN = False
    import requests

# -----------------------
# CONFIGURACIÓN
# -----------------------
# ID del ZIP en Drive (extraído de tu link)
HISTORICOS_ZIP_ID = "1Tm2vRpHYbPNUGDVxU4cRbXpYGH_uasW_"
HISTORICOS_ZIP_NAME = "datos_acciones.zip"
ACTIONS_FOLDER = "acciones"  # carpeta donde se extraerán los CSV de cada ticker

ANNUAL_FACTOR = 252  # días de trading para anualizar

# Nombres de archivos de resultados
RESULT_CSV = "Distribucion_Portafolios.csv"
SUMMARY_CSV = "Resumen_Portafolios.csv"
ARTIFACTS_ZIP = "precomputed_artifacts.zip"

# -----------------------
# UTIL: descargar ZIP desde Google Drive
# -----------------------
def download_zip_from_drive(file_id: str, output: str):
    """Descarga un ZIP desde Google Drive usando gdown si está disponible, si no requests."""
    if os.path.exists(output):
        return True
    if _HAS_GDOWN:
        url = f"https://drive.google.com/uc?id={file_id}"
        gdown.download(url, output, quiet=True)
        return os.path.exists(output)
    else:
        url = f"https://drive.google.com/uc?export=download&id={file_id}"
        try:
            resp = requests.get(url, timeout=120)
        except Exception as e:
            st.error(f"Error descargando ZIP desde Drive: {e}")
            return False
        if resp.status_code == 200:
            with open(output, "wb") as f:
                f.write(resp.content)
            return True
        else:
            st.error(f"Respuesta HTTP {resp.status_code} al descargar ZIP.")
            return False

def ensure_folder_from_zip(file_id, zip_name, folder_name):
    """Descarga y extrae ZIP si es necesario. Extrae solo CSVs al nivel folder_name."""
    try:
        ok = download_zip_from_drive(file_id, zip_name)
        if not ok:
            return False

        # extraer si no existe la carpeta o si está vacía
        if not os.path.exists(folder_name) or len(os.listdir(folder_name)) == 0:
            os.makedirs(folder_name, exist_ok=True)
            with zipfile.ZipFile(zip_name, "r") as z:
                for f in z.namelist():
                    if f.lower().endswith(".csv"):
                        base = os.path.basename(f)
                        # extraer al folder_name (manteniendo nombre base)
                        extracted = z.read(f)
                        with open(os.path.join(folder_name, base), "wb") as out:
                            out.write(extracted)
        csv_files = [f for f in os.listdir(folder_name) if f.lower().endswith(".csv")]
        return len(csv_files) > 0
    except zipfile.BadZipFile:
        st.error(f"❌ Archivo ZIP {zip_name} inválido (BadZipFile).")
        return False
    except Exception as e:
        st.error(f"❌ Error extrayendo/leyendo ZIP {zip_name}: {e}")
        return False

# -----------------------
# DETECCIÓN DE COLUMNAS
# -----------------------
def detect_adjcol_and_datecol(df: pd.DataFrame):
    """Detecta columnas Date y Adj Close (soporta variantes comunes)."""
    date_col = None
    adj_col = None
    for c in df.columns:
        cl = c.lower().strip()
        if cl in ("date", "fecha"):
            date_col = c
        if "adj" in cl and "close" in cl:
            adj_col = c
    if adj_col is None:
        # si no hay adj close, tomar Close si existe
        for c in df.columns:
            if c.lower().strip() == "close":
                adj_col = c
                break
    if date_col is None:
        for c in df.columns:
            # si ya viene como datetime
            if np.issubdtype(df[c].dtype, np.datetime64):
                date_col = c
                break
            # o si nombre contenga 'date' (otra variante)
            if "date" in c.lower():
                date_col = c
                break
    return date_col, adj_col

# -----------------------
# FUNCIONES DE MARKOWITZ (basadas en tu script)
# -----------------------
def anualizar(ret_diario, vol_diario):
    ret_anual = ret_diario * ANNUAL_FACTOR
    vol_anual = vol_diario * np.sqrt(ANNUAL_FACTOR)
    return ret_anual, vol_anual

def portfolio_return(weights, mean_returns):
    return float(np.sum(mean_returns * weights))

def portfolio_volatility(weights, cov_matrix):
    return float(np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights))))

def minimize_volatility_for_target(mean_returns, cov_matrix, target_return):
    n = len(mean_returns)
    def vol_fn(w): return portfolio_volatility(w, cov_matrix)
    cons = (
        {'type':'eq','fun': lambda w: portfolio_return(w, mean_returns) - target_return},
        {'type':'eq','fun': lambda w: np.sum(w) - 1.0}
    )
    bounds = tuple((0.0,1.0) for _ in range(n))
    w0 = np.ones(n)/n
    return minimize(vol_fn, w0, method="SLSQP", bounds=bounds, constraints=cons)

def global_min_variance(mean_returns, cov_matrix):
    n = len(mean_returns)
    def vol_fn(w): return portfolio_volatility(w, cov_matrix)
    cons = ({'type':'eq','fun': lambda w: np.sum(w) - 1.0})
    bounds = tuple((0.0,1.0) for _ in range(n))
    w0 = np.ones(n)/n
    return minimize(vol_fn, w0, method="SLSQP", bounds=bounds, constraints=cons)

def maximize_sharpe(mean_returns, cov_matrix, risk_free_daily=0.0):
    n = len(mean_returns)
    def neg_sharpe(w):
        ret = portfolio_return(w, mean_returns)
        vol = portfolio_volatility(w, cov_matrix)
        if vol == 0:
            return 1e9
        return -(ret - risk_free_daily) / vol
    cons = ({'type':'eq','fun': lambda w: np.sum(w) - 1.0})
    bounds = tuple((0.0,1.0) for _ in range(n))
    w0 = np.ones(n)/n
    return minimize(neg_sharpe, w0, method="SLSQP", bounds=bounds, constraints=cons)

# -----------------------
# STREAMLIT UI
# -----------------------
st.set_page_config(page_title="Markowitz — App", layout="centered")
st.title("Simulación Markowitz (integración de tu código)")

st.markdown(
    "Sube un CSV con columnas ticker y % del portafolio (o nombres parecidos). "
    "Al cargar el CSV se habilita la simulación que usará los históricos dentro del ZIP en Drive."
)

# Ejemplo descargable
ejemplo = pd.DataFrame({"ticker":["AAPL","MSFT","GOOGL"], "% del portafolio":[40,30,30]})
st.download_button("📂 Descargar ejemplo CSV", ejemplo.to_csv(index=False), file_name="ejemplo_portafolio.csv", mime="text/csv")

# Uploader del usuario
uploaded = st.file_uploader("Sube tu CSV (Ticker, % del Portafolio)", type=["csv"])
df_user = None
if uploaded is not None:
    try:
        df_user = pd.read_csv(uploaded)
        st.success("CSV cargado correctamente")
        st.dataframe(df_user)
    except Exception as e:
        st.error(f"Error leyendo tu CSV: {e}")
        st.stop()

# Descargar y extraer ZIP si hace falta
if st.button("🔽 Descargar y extraer históricos desde Drive"):
    with st.spinner("Descargando y extrayendo ZIP desde Drive..."):
        ok = ensure_folder_from_zip(HISTORICOS_ZIP_ID, HISTORICOS_ZIP_NAME, ACTIONS_FOLDER)
    if not ok:
        st.error("No se pudo preparar la carpeta de históricos. Revisa el ID del ZIP o la conexión.")
    else:
        st.success("Históricos listos en carpeta 'acciones/'")
        tickers_avail = [f[:-4].upper() for f in os.listdir(ACTIONS_FOLDER) if f.lower().endswith(".csv")]
        st.info(f"Tickers locales disponibles: {len(tickers_avail)} (muestra 50): {tickers_avail[:50]}")

# También mostrar si ya existe la carpeta con archivos
if os.path.exists(ACTIONS_FOLDER):
    tickers_avail = [f[:-4].upper() for f in os.listdir(ACTIONS_FOLDER) if f.lower().endswith(".csv")]
    st.caption(f"Tickers locales detectados: {len(tickers_avail)}")

# Ejecutar simulación cuando haya CSV del usuario
if df_user is not None:
    # detectar columnas ticker y peso (flexible)
    cols_lower = [c.strip().lower() for c in df_user.columns]
    col_ticker = None
    col_weight = None
    for c_orig, c_low in zip(df_user.columns, cols_lower):
        if "tick" in c_low:
            col_ticker = c_orig
        if ("por" in c_low) or ("%" in c_low) or ("peso" in c_low) or ("weight" in c_low):
            col_weight = c_orig

    if col_ticker is None or col_weight is None:
        st.error("Tu CSV debe contener columnas con Ticker y con % (ej. 'ticker' y '% del portafolio' o 'peso').")
    else:
        # normalizar pesos a suma 1
        df_user[col_weight] = pd.to_numeric(df_user[col_weight], errors="coerce")
        if df_user[col_weight].isnull().any():
            st.error("Algunos pesos no son numéricos. Corrige el CSV.")
        else:
            df_user[col_weight] = df_user[col_weight] / df_user[col_weight].sum()
            tickers = [str(x).strip().upper() for x in df_user[col_ticker].tolist()]
            weights_user = df_user[col_weight].values

            st.write("Tickers detectados:", tickers)
            st.write("Pesos normalizados (suma = 1):")
            st.dataframe(pd.DataFrame({"Ticker": tickers, "Weight": np.round(weights_user,6)}))

            # Botón para iniciar la simulación que usa los CSV de la carpeta acciones
            if st.button("🚀 Iniciar Simulación (usar históricos desde ZIP)"):
                # validar existencia carpeta
                if not os.path.exists(ACTIONS_FOLDER):
                    st.error("La carpeta 'acciones/' no existe. Descarga y extrae primero el ZIP.")
                    st.stop()

                # Cargar series por ticker
                series_list = []
                missing = []
                bad = []
                for t in tickers:
                    # buscar archivo exacto TICKER.csv (ignorando mayúsculas)
                    found = None
                    for f in os.listdir(ACTIONS_FOLDER):
                        if f.lower().endswith(".csv") and f[:-4].upper() == t.upper():
                            found = os.path.join(ACTIONS_FOLDER, f)
                            break
                    if found is None:
                        missing.append(t)
                        continue
                    try:
                        dfp = pd.read_csv(found)
                    except Exception:
                        bad.append(t)
                        continue
                    date_col, adj_col = detect_adjcol_and_datecol(dfp)
                    if date_col is None or adj_col is None:
                        missing.append(t)
                        continue
                    # preparar serie
                    dfp[date_col] = pd.to_datetime(dfp[date_col], errors="coerce")
                    dfp = dfp.dropna(subset=[date_col, adj_col])
                    dfp = dfp.sort_values(date_col)
                    s = dfp.set_index(date_col)[adj_col].astype(float).pct_change().dropna()
                    s.name = t
                    series_list.append(s)

                if missing or bad:
                    if missing:
                        st.error(f"No se encontraron históricos válidos para: {missing}")
                    if bad:
                        st.error(f"Archivos inválidos/no leíbles para: {bad}")
                    st.stop()

                if len(series_list) == 0:
                    st.error("No se pudieron cargar series válidas. Ajusta tu CSV o verifica la carpeta de históricos.")
                    st.stop()

                # Concatenar en DataFrame alineando por fechas (solape)
                price_returns = pd.concat(series_list, axis=1, join="inner").dropna()
                if price_returns.shape[1] == 0:
                    st.error("No hay solape de fechas entre las series seleccionadas.")
                    st.stop()

                # Según tu implementación usabas retornos logarítmicos; 
                # aquí ya tenemos pct_change de close -> aproximación. 
                # Si prefieres log returns, usar: np.log(data / data.shift(1)).dropna()
                # price_returns = np.log(price_series / price_series.shift(1)).dropna()
                # En nuestro flujo, price_returns ya contiene pct_change.
                # Convertimos a log returns para mantener exactamente tu lógica:
                try:
                    # reconvertir a precios si la serie era pct_change -> no posible; 
                    # en los CSV se usan precios, pero en este flujo ya trabajamos con pct_change.
                    # Para mantener la misma lógica: calcular log returns a partir de precio series.
                    # Re-read price series instead of pct:
                    # We'll rebuild using Adj Close columns directly to compute log returns.
                    price_series_df = {}
                    for t in tickers:
                        # read file again to get price column
                        found = None
                        for f in os.listdir(ACTIONS_FOLDER):
                            if f.lower().endswith(".csv") and f[:-4].upper() == t.upper():
                                found = os.path.join(ACTIONS_FOLDER, f)
                                break
                        dfp = pd.read_csv(found)
                        date_col, adj_col = detect_adjcol_and_datecol(dfp)
                        dfp[date_col] = pd.to_datetime(dfp[date_col], errors="coerce")
                        dfp = dfp.dropna(subset=[date_col, adj_col])
                        dfp = dfp.sort_values(date_col)
                        price_series_df[t] = dfp.set_index(date_col)[adj_col].astype(float)

                    prices = pd.concat(price_series_df.values(), axis=1, keys=price_series_df.keys())
                    # rename columns to tickers
                    prices.columns = prices.columns.droplevel(0)
                    prices = prices.dropna(axis=1, how="any")
                    if prices.shape[1] == 0:
                        st.error("Error construyendo DataFrame de precios (posible formato inesperado).")
                        st.stop()

                    # calcular retornos logarítmicos exactamente como en tu script
                    returns_log = np.log(prices / prices.shift(1)).dropna()
                except Exception as e:
                    st.error(f"Error calculando retornos log: {e}")
                    st.stop()

                # medias y covarianza diaria
                pBar = returns_log.mean().values    # vector de medias diarias
                Sigma = returns_log.cov().values     # matriz cov diaria
                n_assets = len(pBar)
                if n_assets == 0:
                    st.error("No hay activos válidos después de construir retornos.")
                    st.stop()

                # Mostrar info básica
                st.write(f"Activos utilizados en la optimización: {n_assets}")
                st.write("Fechas de inicio y fin (series):")
                st.write(f"- Desde: {returns_log.index.min().date()}  - Hasta: {returns_log.index.max().date()}")

                # calcular portafolio del usuario (usando pesos normalizados)
                port_ret_user = portfolio_return(weights_user, pBar)
                port_vol_user = portfolio_volatility(weights_user, Sigma)
                port_ret_user_an, port_vol_user_an = anualizar(port_ret_user, port_vol_user)

                # FRONTERA (opcional, compute a few points)
                frontier_returns = []
                frontier_volatility = []
                if n_assets > 1:
                    # generar targets entre min y max de pBar
                    targets = np.linspace(pBar.min(), pBar.max(), 30)
                    for r in targets:
                        try:
                            opt = minimize_volatility_for_target(pBar, Sigma, r)
                            if opt.success:
                                frontier_volatility.append(portfolio_volatility(opt.x, Sigma))
                                frontier_returns.append(portfolio_return(opt.x, pBar))
                        except Exception:
                            continue
                else:
                    frontier_returns = [portfolio_return(np.array([1.0]), pBar)]
                    frontier_volatility = [portfolio_volatility(np.array([1.0]), Sigma)]

                # GMVP
                try:
                    gmv_res = global_min_variance(pBar, Sigma)
                    w_gmv = gmv_res.x
                    gmv_ret = portfolio_return(w_gmv, pBar)
                    gmv_vol = portfolio_volatility(w_gmv, Sigma)
                    gmv_ret_an, gmv_vol_an = anualizar(gmv_ret, gmv_vol)
                except Exception as e:
                    st.error(f"Error optimizando GMVP: {e}")
                    st.stop()

                # Max Sharpe (usar input rf anual y convertir a diario)
                rf_anual = st.number_input("Tasa libre de riesgo (anual, decimal)", value=0.0, step=0.0001, format="%.6f")
                rf_diario = rf_anual / ANNUAL_FACTOR
                try:
                    ms_res = maximize_sharpe(pBar, Sigma, risk_free_daily=rf_diario)
                    w_ms = ms_res.x
                    ms_ret = portfolio_return(w_ms, pBar)
                    ms_vol = portfolio_volatility(w_ms, Sigma)
                    ms_ret_an, ms_vol_an = anualizar(ms_ret, ms_vol)
                except Exception as e:
                    st.error(f"Error optimizando Max Sharpe: {e}")
                    st.stop()

                # Mostrar resultados anualizados (como pediste)
                st.subheader("=== Resultados anualizados ===")
                st.write(f"- Portafolio Usuario: Retorno anual esperado *{port_ret_user_an:.2%}, Volatilidad anual **{port_vol_user_an:.2%}*")
                st.write(f"- GMVP: Retorno anual *{gmv_ret_an:.2%}, Volatilidad anual **{gmv_vol_an:.2%}*")
                st.write(f"- Max Sharpe: Retorno anual *{ms_ret_an:.2%}, Volatilidad anual **{ms_vol_an:.2%}*")

                # DataFrames con distribuciones (filtrar pesos muy pequeños como en tu script)
                df_gmv_weights = pd.Series(w_gmv, index=returns_log.columns, name="Peso").reset_index().rename(columns={"index":"Ticker"})
                df_ms_weights = pd.Series(w_ms, index=returns_log.columns, name="Peso").reset_index().rename(columns={"index":"Ticker"})
                df_user_weights = pd.DataFrame({"Ticker": tickers, "Peso": weights_user})

                # transformar a "% del Portafolio" y filtrar < 0.001 como en tu script
                def make_distrib_df(s_weights, name):
                    s = s_weights.copy()
                    s["% del Portafolio"] = (s["Peso"] / s["Peso"].sum()) * 100
                    s = s[s["% del Portafolio"] > 0.001]
                    s["Portafolio"] = name
                    s = s[["Ticker", "% del Portafolio", "Portafolio"]]
                    s["% del Portafolio"] = s["% del Portafolio"].round(6)
                    return s

                d_user = make_distrib_df(df_user_weights.rename(columns={"Peso":"Peso"}), "Usuario")
                d_gmv = make_distrib_df(df_gmv_weights.rename(columns={"Peso":"Peso"}), "GMVP")
                d_ms  = make_distrib_df(df_ms_weights.rename(columns={"Peso":"Peso"}), "Max Sharpe")

                distribucion_final = pd.concat([d_user, d_gmv, d_ms], ignore_index=True)
                st.dataframe(distribucion_final)

                # Guardar artefactos (CSV + resumen + zip) en carpeta local de la app
                if st.button("💾 Finalizar y Guardar Resultados"):
                    # Guardar CSVs
                    distribacion_path = os.path.join(os.getcwd(), RESULT_CSV)
                    resumen_path = os.path.join(os.getcwd(), SUMMARY_CSV)
                    distribucion_final.to_csv(distribacion_path, index=False, encoding="utf-8-sig")

                    resumen = pd.DataFrame([
                        {"Portafolio":"Usuario", "Retorno Anual": port_ret_user_an, "Riesgo Anual": port_vol_user_an},
                        {"Portafolio":"GMVP", "Retorno Anual": gmv_ret_an, "Riesgo Anual": gmv_vol_an},
                        {"Portafolio":"MaxSharpe", "Retorno Anual": ms_ret_an, "Riesgo Anual": ms_vol_an},
                    ])
                    resumen.to_csv(resumen_path, index=False, encoding="utf-8-sig")

                    # Guardar frontier (diario) igual que tu script
                    frontier_df = pd.DataFrame({
                        "Retorno_Diario": frontier_returns,
                        "Volatilidad_Diaria": frontier_volatility
                    })
                    frontier_path = os.path.join(os.getcwd(), "frontier.csv")
                    frontier_df.to_csv(frontier_path, index=False)

                    # Guardar medias y cov (como en tu script)
                    mean_returns_path = os.path.join(os.getcwd(), "mean_returns.csv")
                    cov_path = os.path.join(os.getcwd(), "covariance.npy")
                    pd.Series(pBar, index=returns_log.columns, name="MeanReturn").to_csv(mean_returns_path, header=True)
                    np.save(cov_path, Sigma)

                    # GMVP & MaxSharpe weights files
                    gmv_path = os.path.join(os.getcwd(), "GMVP.csv")
                    ms_path = os.path.join(os.getcwd(), "MaxSharpe.csv")
                    pd.Series(w_gmv, index=returns_log.columns, name="Peso").to_csv(gmv_path)
                    pd.Series(w_ms, index=returns_log.columns, name="Peso").to_csv(ms_path)

                    # Comprimir artefactos
                    zip_out = os.path.join(os.getcwd(), ARTIFACTS_ZIP)
                    with zipfile.ZipFile(zip_out, 'w') as z:
                        z.write(distribacion_path, os.path.basename(distribacion_path))
                        z.write(resumen_path, os.path.basename(resumen_path))
                        z.write(frontier_path, os.path.basename(frontier_path))
                        z.write(mean_returns_path, os.path.basename(mean_returns_path))
                        z.write(cov_path, os.path.basename(cov_path))
                        z.write(gmv_path, os.path.basename(gmv_path))
                        z.write(ms_path, os.path.basename(ms_path))

                    # Guardar en session_state
                    st.session_state["last_sim"] = {
                        "tickers": tickers,
                        "weights_user": list(weights_user),
                        "weights_gmv": list(w_gmv),
                        "weights_ms": list(w_ms),
                        "ret_user_an": port_ret_user_an, "vol_user_an": port_vol_user_an,
                        "ret_gmv_an": gmv_ret_an, "vol_gmv_an": gmv_vol_an,
                        "ret_ms_an": ms_ret_an, "vol_ms_an": ms_vol_an
                    }

                    st.success(f"Resultados guardados y comprimidos en: {zip_out}")

                    # ofrecer descargas
                    with open(distribacion_path, "rb") as f:
                        st.download_button("Descargar Distribución (CSV)", data=f, file_name=os.path.basename(distribacion_path), mime="text/csv")
                    with open(resumen_path, "rb") as f:
                        st.download_button("Descargar Resumen (CSV)", data=f, file_name=os.path.basename(resumen_path), mime="text/csv")
                    with open(zip_out, "rb") as f:
                        st.download_button("Descargar Artefactos (ZIP)", data=f, file_name=os.path.basename(zip_out), mime="application/zip")
