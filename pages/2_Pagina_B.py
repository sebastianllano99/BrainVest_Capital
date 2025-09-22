import streamlit as st
import pandas as pd
import numpy as np
import os
import zipfile
import io

# Intento usar gdown si está instalado; si no, fallback a requests
try:
    import gdown
    _HAS_GDOWN = True
except Exception:
    _HAS_GDOWN = False
    import requests

# -----------------------
# Configuración: IDs / rutas
# -----------------------
# ZIP de históricos
HISTORICOS_ZIP_ID = "1Tm2vRpHYbPNUGDVxU4cRbXpYGH_uasW_"
HISTORICOS_ZIP_NAME = "datos_acciones.zip"
ACTIONS_FOLDER = "acciones"

# Archivos que vamos a guardar (resultados del usuario)
RESULT_CSV = "resultado_usuario.csv"
SUMMARY_CSV = "resultado_usuario_summary.csv"

# -----------------------
# Funciones utilitarias
# -----------------------
def download_zip_from_drive(file_id: str, output: str):
    """Descarga un ZIP desde Google Drive; intenta gdown y si no requests."""
    if os.path.exists(output):
        return True
    if _HAS_GDOWN:
        url = f"https://drive.google.com/uc?id={file_id}"
        gdown.download(url, output, quiet=True)
        return os.path.exists(output)
    else:
        url = f"https://drive.google.com/uc?export=download&id={file_id}"
        resp = requests.get(url, timeout=60)
        if resp.status_code == 200:
            with open(output, "wb") as f:
                f.write(resp.content)
            return True
        return False

def ensure_folder_from_zip(file_id, zip_name, folder_name):
    """Descarga y extrae ZIP si es necesario. Devuelve True si hay CSV dentro."""
    try:
        ok = download_zip_from_drive(file_id, zip_name)
        if not ok:
            st.warning(f"No se pudo descargar el ZIP {zip_name} desde Drive.")
            return False

        if not os.path.exists(folder_name):
            os.makedirs(folder_name, exist_ok=True)
            with zipfile.ZipFile(zip_name, "r") as z:
                # extraer cada archivo al folder_name directamente
                for f in z.namelist():
                    if f.lower().endswith(".csv") or f.lower().endswith(".npy"):
                        base = os.path.basename(f)
                        z.extract(f, folder_name)
                        # mover al nivel raíz
                        os.rename(os.path.join(folder_name, f), os.path.join(folder_name, base))
                        # eliminar carpetas vacías internas
                        dir_created = os.path.join(folder_name, os.path.dirname(f))
                        if os.path.exists(dir_created):
                            try: os.rmdir(dir_created)
                            except: pass

        csv_files = [f for f in os.listdir(folder_name) if f.lower().endswith(".csv")]
        return len(csv_files) > 0
    except zipfile.BadZipFile:
        st.error(f"❌ Archivo ZIP {zip_name} inválido (BadZipFile).")
        return False
    except Exception as e:
        st.error(f"❌ Error extrayendo/leyendo ZIP {zip_name}: {e}")
        return False

def find_price_file_for_ticker(ticker: str):
    """Busca CSV en carpeta de históricos que coincida con ticker exacto."""
    if not os.path.exists(ACTIONS_FOLDER):
        return None
    ticker_u = ticker.upper()
    for f in os.listdir(ACTIONS_FOLDER):
        if f.lower().endswith(".csv") and f[:-4].upper() == ticker_u:
            return os.path.join(ACTIONS_FOLDER, f)
    return None

def detect_adjcol_and_datecol(df: pd.DataFrame):
    """Detecta columnas Date y Adj Close (soporta variantes comunes)."""
    date_col = None
    adj_col = None
    for c in df.columns:
        cl = c.lower()
        if cl in ("date", "fecha"):
            date_col = c
        if "adj" in cl and "close" in cl:
            adj_col = c
        if cl == "close" and adj_col is None:
            adj_col = c
    if date_col is None:
        for c in df.columns:
            if np.issubdtype(df[c].dtype, np.datetime64):
                date_col = c
                break
    return date_col, adj_col

# -----------------------
# Interfaz
# -----------------------
st.title("Página 2 — Simulación de Portafolio")
st.write("""
Sube un CSV con columnas `Ticker` y `% del Portafolio` (o nombres parecidos).  
Al cargar el CSV aparecerá el botón **Iniciar Simulación**. Después de ver resultados, podrás **Finalizar / Guardar**.
""")

# botón para ejemplo
ejemplo = pd.DataFrame({"Ticker":["AAPL","MSFT","GOOGL"], "% del Portafolio":[40,30,30]})
st.download_button(" Descargar ejemplo CSV", ejemplo.to_csv(index=False), file_name="ejemplo_portafolio.csv")

# uploader
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

# Descargar/extraer ZIP si es necesario
ok = ensure_folder_from_zip(HISTORICOS_ZIP_ID, HISTORICOS_ZIP_NAME, ACTIONS_FOLDER)
if not ok:
    st.error("No hay históricos disponibles. Revisa tu ZIP de acciones.")
    st.stop()

# mostrar tickers disponibles
tickers_avail = [f[:-4].upper() for f in os.listdir(ACTIONS_FOLDER) if f.lower().endswith(".csv")]
st.info(f" Tickers disponibles localmente: {len(tickers_avail)} (muestra 20) {tickers_avail[:20]}")

# Mostrar botón Iniciar sólo si CSV cargado
if df_user is not None:
    if st.button(" Iniciar Simulación"):
        # detectar columnas
        cols_lower = [c.strip().lower() for c in df_user.columns]
        col_ticker = None
        col_weight = None
        for c_orig, c_low in zip(df_user.columns, cols_lower):
            if "tick" in c_low:
                col_ticker = c_orig
            if ("por" in c_low) or ("%" in c_low) or ("peso" in c_low) or ("weight" in c_low):
                col_weight = c_orig

        if col_ticker is None or col_weight is None:
            st.error(" Tu CSV debe tener columnas con Ticker y con el % (ej. '% del Portafolio' o 'Peso').")
        else:
            # Normalizar pesos
            df_user[col_weight] = pd.to_numeric(df_user[col_weight], errors="coerce")
            if df_user[col_weight].isnull().any():
                st.error(" Algunos pesos no son numéricos.")
            else:
                df_user[col_weight] = df_user[col_weight] / df_user[col_weight].sum()
                tickers = [str(x).strip().upper() for x in df_user[col_ticker].tolist()]
                weights = df_user[col_weight].values

                # Cargar series de retornos diarios
                series_list = []
                missing = []
                for t in tickers:
                    path = find_price_file_for_ticker(t)
                    if path is None:
                        missing.append(t)
                        continue
                    dfp = pd.read_csv(path)
                    date_col, adj_col = detect_adjcol_and_datecol(dfp)
                    if date_col is None or adj_col is None:
                        missing.append(t)
                        continue
                    dfp[date_col] = pd.to_datetime(dfp[date_col], errors="coerce")
                    dfp = dfp.dropna(subset=[date_col, adj_col])
                    dfp = dfp.sort_values(date_col)
                    s = dfp.set_index(date_col)[adj_col].pct_change().dropna()
                    s.name = t
                    series_list.append(s)

                if missing:
                    st.error(f"No se encontraron históricos válidos para: {missing}")
                    st.stop()
                elif len(series_list) == 0:
                    st.error("No se pudieron cargar series válidas. Ajusta tu CSV o verifica la carpeta de históricos.")
                    st.stop()
                else:
                    returns_df = pd.concat(series_list, axis=1, join="inner").dropna()
                    if returns_df.shape[1] == 0:
                        st.error("No hay solape de fechas entre las series seleccionadas.")
                        st.stop()
                    else:
                        mean_returns = returns_df.mean()
                        cov_matrix = returns_df.cov()
                        port_ret_ann = float(np.dot(weights, mean_returns) * 252)
                        port_vol_ann = float(np.sqrt(np.dot(weights.T, np.dot(cov_matrix * 252, weights))))

                        st.subheader(" Resultados de simulación (Usuario)")
                        st.write(f"- Retorno anual esperado: **{port_ret_ann:.2%}**")
                        st.write(f"- Volatilidad anual esperada: **{port_vol_ann:.2%}**")

                        distrib = pd.DataFrame({
                            "Ticker": tickers,
                            "% del Portafolio": (weights * 100).round(6),
                            "Portafolio": "Usuario"
                        })
                        st.dataframe(distrib)

                        if st.button(" Finalizar y Guardar Resultados"):
                            distrib.to_csv(RESULT_CSV, index=False, encoding="utf-8-sig")
                            resumen = pd.DataFrame([{
                                "Portafolio": "Usuario",
                                "Retorno Anual": port_ret_ann,
                                "Riesgo Anual": port_vol_ann
                            }])
                            resumen.to_csv(SUMMARY_CSV, index=False, encoding="utf-8-sig")

                            st.session_state["last_sim"] = {
                                "tickers": tickers,
                                "weights": list(weights),
                                "retorno_anual": port_ret_ann,
                                "riesgo_anual": port_vol_ann
                            }
                            st.success(f"Resultados guardados: {RESULT_CSV} y {SUMMARY_CSV}")
