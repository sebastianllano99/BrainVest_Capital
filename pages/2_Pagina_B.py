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
ZIP_FILE_ID = "1Tm2vRpHYbPNUGDVxU4cRbXpYGH_uasW_"   # ZIP que contiene la carpeta 'acciones'
ZIP_NAME = "datos_acciones.zip"
DATA_FOLDER = "acciones"

# ZIP con artefactos precomputados de Markowitz
ARTIFACTS_ZIP = "precomputed_artifacts.zip"

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

def ensure_actions_folder():
    """Descarga y extrae ZIP si es necesario. Devuelve True si DATA_FOLDER existe con csv."""
    try:
        ok = download_zip_from_drive(ZIP_FILE_ID, ZIP_NAME)
        if not ok:
            st.warning("No se pudo descargar el ZIP desde Drive (revisa permisos / id).")
            return False
        with zipfile.ZipFile(ZIP_NAME, "r") as z:
            if not os.path.exists(DATA_FOLDER):
                z.extractall(".")
        return os.path.exists(DATA_FOLDER)
    except zipfile.BadZipFile:
        st.error("❌ Archivo ZIP descargado inválido (BadZipFile).")
        return False
    except Exception as e:
        st.error(f"❌ Error extrayendo/leyendo ZIP: {e}")
        return False

def find_price_file_for_ticker(ticker: str):
    """Busca en DATA_FOLDER un archivo que empiece por el ticker (case-insensitive). Devuelve ruta o None."""
    if not os.path.exists(DATA_FOLDER):
        return None
    ticker_u = ticker.upper()
    for f in os.listdir(DATA_FOLDER):
        if not f.lower().endswith(".csv"):
            continue
        base = f[:-4]
        if base.upper().startswith(ticker_u):
            return os.path.join(DATA_FOLDER, f)
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

def load_precomputed_artifacts(possible_paths=None):
    """Carga artefactos precomputados desde un ZIP si existe."""
    possible_paths = possible_paths or [ARTIFACTS_ZIP]
    for p in possible_paths:
        if os.path.exists(p):
            try:
                with zipfile.ZipFile(p, "r") as z:
                    # tickers.csv
                    if "tickers.csv" in z.namelist():
                        with z.open("tickers.csv") as f:
                            tickers_series = pd.read_csv(f, squeeze=True, header=0)
                            if isinstance(tickers_series, pd.DataFrame):
                                if "Ticker" in tickers_series.columns:
                                    tickers_list = tickers_series["Ticker"].astype(str).str.strip().tolist()
                                else:
                                    tickers_list = tickers_series.iloc[:,0].astype(str).str.strip().tolist()
                            else:
                                tickers_list = tickers_series.astype(str).str.strip().tolist()
                    else:
                        tickers_list = None

                    # mean_returns.csv
                    mean_returns = None
                    if "mean_returns.csv" in z.namelist():
                        with z.open("mean_returns.csv") as f:
                            dfmr = pd.read_csv(f, index_col=0)
                            if dfmr.shape[1] == 1:
                                mean_returns = dfmr.iloc[:,0].astype(float)
                            else:
                                mean_returns = dfmr.squeeze().astype(float)

                    # covariance.npy
                    cov = None
                    if "covariance.npy" in z.namelist():
                        with z.open("covariance.npy") as f:
                            cov_bytes = f.read()
                            cov = np.load(io.BytesIO(cov_bytes))

                    if tickers_list is not None and mean_returns is not None and cov is not None:
                        mean_returns.index = [str(x).strip().upper() for x in mean_returns.index]
                        tickers_list = [t.strip().upper() for t in tickers_list]
                        return tickers_list, mean_returns, cov
            except Exception as e:
                print("Error cargando artefactos desde", p, ":", e)
    return None, None, None

# -----------------------
# Interfaz
# -----------------------
st.title("Página 2 — Simulación de Portafolio")
st.write("""
Sube un CSV con columnas `Ticker` y `% del Portafolio` (o nombres parecidos).  
Al cargar el CSV aparecerá el botón **Iniciar Simulación**. Después de ver resultados, podrás **Finalizar / Guardar**.
""")

# Botón ejemplo CSV
ejemplo = pd.DataFrame({"Ticker":["AAPL","MSFT","GOOGL"], "% del Portafolio":[40,30,30]})
st.download_button(" Descargar ejemplo CSV", ejemplo.to_csv(index=False), file_name="ejemplo_portafolio.csv")

# Uploader
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

# Mostrar tickers disponibles
if os.path.exists(DATA_FOLDER):
    tickers_avail = [f[:-4].upper() for f in os.listdir(DATA_FOLDER) if f.lower().endswith(".csv")]
    st.info(f" Tickers disponibles localmente: {len(tickers_avail)} (muestra 20) {tickers_avail[:20]}")
else:
    st.info(" Aún no se ha descargado/extrado la carpeta 'acciones' con históricos.")

# Iniciar Simulación
if df_user is not None:
    if st.button(" Iniciar Simulación"):
        # columnas
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

                # descargar/extraer ZIP históricos
                ok = ensure_actions_folder()
                if not ok:
                    st.error(" No hay carpeta 'acciones' con históricos. Revisa el ZIP en Drive.")
                else:
                    tickers = [str(x).strip().upper() for x in df_user[col_ticker].tolist()]
                    weights = df_user[col_weight].values

                    # Cargar artefactos precomputados
                    artifact_tickers, artifact_mean_returns, artifact_cov = load_precomputed_artifacts()

                    series_list = []
                    missing = []
                    used_from_artifacts = []
                    used_from_csv = []

                    for t in tickers:
                        t_up = t.strip().upper()
                        if artifact_tickers and t_up in artifact_tickers:
                            used_from_artifacts.append(t_up)
                            continue
                        path = find_price_file_for_ticker(t_up)
                        if path is None:
                            missing.append(t_up)
                            continue
                        dfp = pd.read_csv(path)
                        date_col, adj_col = detect_adjcol_and_datecol(dfp)
                        if date_col is None or adj_col is None:
                            missing.append(t_up)
                            continue
                        dfp[date_col] = pd.to_datetime(dfp[date_col], errors="coerce")
                        dfp = dfp.dropna(subset=[date_col, adj_col])
                        dfp = dfp.sort_values(date_col)
                        s = dfp.set_index(date_col)[adj_col].pct_change().dropna()
                        s.name = t_up
                        series_list.append(s)
                        used_from_csv.append(t_up)

                    # Si todo se resolvió desde artefactos
                    if len(series_list) == 0 and len(used_from_artifacts) > 0 and artifact_mean_returns is not None:
                        not_in_art = [t for t in tickers if t.strip().upper() not in artifact_tickers]
                        if not_in_art:
                            st.error(f"No se encontraron históricos válidos para: {not_in_art}")
                        else:
                            sel = [t.strip().upper() for t in tickers]
                            mu_sel = artifact_mean_returns.loc[sel].astype(float).values
                            idx_map = {tk:i for i,tk in enumerate(artifact_tickers)}
                            sel_idx = [idx_map[t] for t in sel]
                            cov_sel = artifact_cov[np.ix_(sel_idx, sel_idx)]
                            weights_arr = np.array(weights, dtype=float)
                            port_ret_ann = float(np.dot(weights_arr, mu_sel) * 252)
                            port_vol_ann = float(np.sqrt(np.dot(weights_arr.T, np.dot(cov_sel * 252, weights_arr))))

                            st.subheader(" Resultados de simulación (Usuario) — desde artefactos precomputados")
                            st.write(f"- Retorno anual esperado: **{port_ret_ann:.2%}**")
                            st.write(f"- Volatilidad anual esperada: **{port_vol_ann:.2%}**")
                            distrib = pd.DataFrame({
                                "Ticker": tickers,
                                "% del Portafolio": (weights_arr * 100).round(6),
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
                                    "weights": list(weights_arr),
                                    "retorno_anual": port_ret_ann,
                                    "riesgo_anual": port_vol_ann
                                }
                                st.success(f"Resultados guardados: {RESULT_CSV} y {SUMMARY_CSV}")
                        st.stop()

                    # Si mezcla o solo CSV
                    if len(series_list) == 0:
                        st.error(f"No se pudieron cargar series válidas. Faltantes: {missing}")
                    else:
                        returns_df = pd.concat(series_list, axis=1, join="inner").dropna()
                        if returns_df.shape[1] == 0:
                            st.error(" No hay solape de fechas entre las series seleccionadas.")
                        else:
                            # combinar artefactos + csv si es necesario
                            final_tickers = [t.strip().upper() for t in tickers if (t.strip().upper() in used_from_csv) or (t.strip().upper() in used_from_artifacts)]
                            mu_from_csv = returns_df.mean().rename(lambda x: x.strip().upper())
                            mu_list = []
                            for tname in final_tickers:
                                if tname in mu_from_csv.index:
                                    mu_list.append(mu_from_csv.loc[tname])
                                else:
                                    mu_list.append(artifact_mean_returns.loc[tname])
                            mu_comb = np.array(mu_list, dtype=float)
                            n = len(final_tickers)
                            cov_comb = np.zeros((n,n), dtype=float)
                            for i,ti in enumerate(final_tickers):
                                for j,tj in enumerate(final_tickers):
                                    if ti in returns_df.columns and tj in returns_df.columns:
                                        cov_comb[i,j] = returns_df[[ti,tj]].cov().iloc[0,1] if ti != tj else returns_df[ti].var()
                                    elif ti in returns_df.columns and tj not in returns_df.columns:
                                        if artifact_tickers and ti in artifact_tickers and tj in artifact_tickers:
                                            idx_map = {tk:i for i,tk in enumerate(artifact_tickers)}
                                            cov_comb[i,j] = artifact_cov[idx_map[ti], idx_map[tj]]
                                        else:
                                            cov_comb[i,j] = 0.0
                                    elif ti not in returns_df.columns and tj in returns_df.columns:
                                        if artifact_tickers and ti in artifact_tickers and tj in artifact_tickers:
                                            idx_map = {tk:i for i,tk in enumerate(artifact_tickers)}
                                            cov_comb[i,j] = artifact_cov[idx_map[ti], idx_map[tj]]
                                        else:
                                            cov_comb[i,j] = 0.0
                                    else:
                                        idx_map = {tk:i for i,tk in enumerate(artifact_tickers)}
                                        cov_comb[i,j] = artifact_cov[idx_map[ti], idx_map[tj]]
                            peso_map = {tt.strip().upper(): w for tt,w in zip(tickers, weights)}
                            weights_aligned = np.array([peso_map[tk] for tk in final_tickers], dtype=float)
                            port_ret_ann = float(np.dot(weights_aligned, mu_comb) * 252)
                            port_vol_ann = float(np.sqrt(np.dot(weights_aligned.T, np.dot(cov_comb * 252, weights_aligned))))

                            st.subheader(" Resultados de simulación (Usuario)")
                            st.write(f"- Retorno anual esperado: **{port_ret_ann:.2%}**")
                            st.write(f"- Volatilidad anual esperada: **{port_vol_ann:.2%}**")
                            distrib = pd.DataFrame({
                                "Ticker": final_tickers,
                                "% del Portafolio": (weights_aligned * 100).round(6),
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
                                    "tickers": final_tickers,
                                    "weights": list(weights_aligned),
                                    "retorno_anual": port_ret_ann,
                                    "riesgo_anual": port_vol_ann
                                }
                                st.success(f"Resultados guardados: {RESULT_CSV} y {SUMMARY_CSV}")
