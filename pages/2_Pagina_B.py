# page2_simulation.py
import streamlit as st
import pandas as pd
import numpy as np
import io, zipfile, requests, os
import plotly.graph_objects as go

st.set_page_config(page_title="Página 2 — Simulación de Portafolio", layout="wide")
st.title("📥 Página 2 — Subir portafolio y simular")

st.markdown("""
En esta página puedes subir un CSV con la **distribución** (Ticker, porcentaje) de un portafolio 
que quieres simular. El sistema usará los artefactos precomputados (frontera, medias y covarianzas)
contenidos en el ZIP que subiste a Google Drive para:
- Calcular retorno y volatilidad anual del portafolio.
- Compararlo con la **frontera eficiente** precomputada.
- Ver si pertenece (aproximadamente) a la frontera o si está por debajo.
- Compararlo con los portafolios óptimos (GMVP y MaxSharpe).
""")

# -------------------------
# CONFIG: ZIP en Drive
# -------------------------
# Usar el ID/URL de tu ZIP en Drive (tu link ya compartido). 
# Convertimos a URL 'uc' para descarga directa.
DRIVE_FILE_ID = "1cJFHOWURl7DYEYc4r4SWvAvV3Sl7bZCB"
URL_ZIP = f"https://drive.google.com/uc?id={DRIVE_FILE_ID}"

# -------------------------
# Ejemplo CSV para descargar
# -------------------------
example_csv = "ticker,porcentaje\nAAPL,20\nMSFT,30\nTSLA,10\nAMZN,40\n"
st.download_button(
    label="Descargar CSV de ejemplo (formato)",
    data=example_csv,
    file_name="ejemplo_portafolio.csv",
    mime="text/csv"
)

st.markdown("---")
st.write("1) Sube aquí tu CSV con columnas `ticker,porcentaje` (cabecera exacta).")
uploaded = st.file_uploader("Sube CSV del usuario", type=["csv","txt"])

# -------------------------
# Helper: cargar artefactos desde zip en Drive (cache)
# -------------------------
@st.cache_data(show_spinner=False)
def load_artifacts_from_drive(url_zip):
    resp = requests.get(url_zip, timeout=30)
    resp.raise_for_status()
    z = zipfile.ZipFile(io.BytesIO(resp.content))
    # Required files: tickers.csv, mean_returns.csv, covariance.npy, frontier.csv, GMVP.csv, MaxSharpe.csv
    def read_csv_from_zip(name):
        if name in z.namelist():
            with z.open(name) as f:
                return pd.read_csv(f)
        return None
    tickers_df = read_csv_from_zip("tickers.csv")
    mean_df = read_csv_from_zip("mean_returns.csv")
    frontier_df = read_csv_from_zip("frontier.csv")
    gmvp_df = read_csv_from_zip("GMVP.csv")
    max_df = read_csv_from_zip("MaxSharpe.csv") or read_csv_from_zip("MarkShare.csv")  # accept either name
    # covariance .npy
    cov = None
    if "covariance.npy" in z.namelist():
        with z.open("covariance.npy") as f:
            cov = np.load(io.BytesIO(f.read()))
    elif "covariance.npz" in z.namelist():
        with z.open("covariance.npz") as f:
            arr = np.load(io.BytesIO(f.read()))
            cov = arr[arr.files[0]]
    # Normalize returned structures
    return {
        "tickers": tickers_df,
        "mean": mean_df,
        "cov": cov,
        "frontier": frontier_df,
        "gmvp": gmvp_df,
        "maxsharpe": max_df
    }

# try to load artifacts (do it once when first needed)
artifacts = None
artifacts_load_error = None
try:
    artifacts = load_artifacts_from_drive(URL_ZIP)
except Exception as e:
    artifacts_load_error = str(e)

# -------------------------
# Show error if artifacts not loaded
# -------------------------
if artifacts_load_error:
    st.error("No se pudieron cargar los artefactos precomputados desde Drive: " + artifacts_load_error)
    st.stop()

# Prepare master lists
master_tickers = None
mean_map = None
cov_matrix = None
frontier_df = None
gmvp_weights_df = artifacts.get("gmvp")
ms_weights_df = artifacts.get("maxsharpe")

# Attempt to parse mean and tickers from artifacts
if artifacts["tickers"] is not None:
    master_tickers = artifacts["tickers"]["ticker"].astype(str).tolist()
elif artifacts["mean"] is not None:
    # mean file may contain ticker column
    if "ticker" in artifacts["mean"].columns:
        master_tickers = artifacts["mean"]["ticker"].astype(str).tolist()
    else:
        # fallback: try index
        master_tickers = artifacts["mean"].iloc[:,0].astype(str).tolist()

# mean returns: try find column with numeric values
if artifacts["mean"] is not None:
    # Accept if file contains column mean_annual_return or MeanReturn or similar
    df_mean = artifacts["mean"].copy()
    # Try known names
    col_candidates = [c for c in df_mean.columns if "mean" in c.lower() or "return" in c.lower()]
    if len(col_candidates) == 0:
        # if single column, pick the numeric one
        for c in df_mean.columns:
            if np.issubdtype(df_mean[c].dtype, np.number):
                col_candidates.append(c)
                break
    if len(col_candidates) == 0:
        raise RuntimeError("No se encontró columna de retornos en mean_returns.csv dentro del zip.")
    mean_col = col_candidates[0]
    # If mean file stored annual values or daily depending on export; we assume daily mean (consistent con generator)
    mean_series = pd.Series(df_mean[mean_col].values, index=df_mean['ticker'] if 'ticker' in df_mean.columns else master_tickers)
    # align to master_tickers order
    mean_map = mean_series.reindex(master_tickers).astype(float)
else:
    mean_map = pd.Series(dtype=float)

cov_matrix = artifacts["cov"]  # numpy array (daily cov)
if cov_matrix is None:
    st.error("No se encontró covariance.npy en el ZIP — la simulación no puede continuar.")
    st.stop()

# frontier
frontier_df = artifacts["frontier"]
if frontier_df is None:
    st.error("No se encontró frontier.csv en el ZIP — la simulación no puede comparar con la frontera.")
    st.stop()

# If gmvp and maxsharpe exist, load
if gmvp_weights_df is not None and 'ticker' in gmvp_weights_df.columns:
    # unify format: DataFrame with ticker, weight
    try:
        gmvp_series = pd.Series(gmvp_weights_df.iloc[:,1].values, index=gmvp_weights_df.iloc[:,0].astype(str)).reindex(master_tickers).fillna(0).astype(float)
    except Exception:
        gmvp_series = pd.Series(gmvp_weights_df.values.flatten(), index=master_tickers)
else:
    gmvp_series = pd.Series(np.zeros(len(master_tickers)), index=master_tickers)

if ms_weights_df is not None and 'ticker' in ms_weights_df.columns:
    try:
        ms_series = pd.Series(ms_weights_df.iloc[:,1].values, index=ms_weights_df.iloc[:,0].astype(str)).reindex(master_tickers).fillna(0).astype(float)
    except Exception:
        ms_series = pd.Series(ms_weights_df.values.flatten(), index=master_tickers)
else:
    ms_series = pd.Series(np.zeros(len(master_tickers)), index=master_tickers)

# -------------------------
# UI: tolerance slider and actions
# -------------------------
st.write("---")
st.markdown("**Parámetros de comparación**")
tol_rel = st.slider("Tolerancia relativa para considerar 'en frontera' (porcentaje del desvío permitido)", min_value=0.0, max_value=1.0, value=0.001, step=0.0005)
st.caption("Por defecto 0.001 = 0.1%")

# -------------------------
# Parse uploaded CSV (if any)
# -------------------------
if uploaded is not None:
    try:
        user_df = pd.read_csv(uploaded)
    except Exception as e:
        st.error("No pude leer el CSV subido: " + str(e))
        st.stop()

    # normalize columns
    user_df.columns = [c.strip().lower() for c in user_df.columns]
    if 'ticker' not in user_df.columns or 'porcentaje' not in user_df.columns:
        st.error("El CSV debe tener exactamente las columnas 'ticker' y 'porcentaje' (insensible a mayúsculas).")
        st.stop()

    # Clean input
    user_df['ticker'] = user_df['ticker'].astype(str).str.strip()
    user_df['porcentaje'] = pd.to_numeric(user_df['porcentaje'], errors='coerce').fillna(0.0)
    if user_df['porcentaje'].sum() == 0:
        st.error("Los porcentajes suman 0. Deben contener valores numéricos.")
        st.stop()

    # Normalize to sum 1
    user_df['weight'] = user_df['porcentaje'] / user_df['porcentaje'].sum()

    # Map to master tickers
    master_idx = {t: i for i,t in enumerate(master_tickers)}
    not_found = [t for t in user_df['ticker'].tolist() if t not in master_idx]
    if len(not_found) > 0:
        st.warning(f"Los siguientes tickers no están en el universo precomputado y serán ignorados: {not_found[:10]}")
    # Build weight vector
    w = np.zeros(len(master_tickers), dtype=float)
    for _, row in user_df.iterrows():
        t = row['ticker']
        if t in master_idx:
            w[master_idx[t]] = row['weight']

    # Show uploaded distribution
    st.write("### Vista previa del CSV subido (normalizado)")
    preview = user_df[['ticker','porcentaje','weight']].rename(columns={'ticker':'Ticker','porcentaje':'Porcentaje','weight':'Peso_normalizado'})
    st.dataframe(preview)

    # Show 'Iniciar Simulación' button only when file uploaded
    if st.button("▶️ Iniciar Simulación"):
        # compute metrics
        # mean_map assumed daily mean (log returns). If mean_map contains annual, adapt accordingly.
        # We will compute using daily mean and daily cov, then anualize.
        means = mean_map.reindex(master_tickers).astype(float).values  # daily
        cov = cov_matrix
        # If cov is 2D numpy, good; else try to convert
        cov = np.array(cov)
        # portfolio daily return and vol
        port_ret_daily = float(np.dot(w, means))
        port_vol_daily = float(np.sqrt(np.dot(w, cov.dot(w))))
        port_ret_annual = port_ret_daily * 252
        port_vol_annual = port_vol_daily * np.sqrt(252)

        # Compare with frontier: interpolate frontier volatility at port_return_daily
        # frontier_df has Retorno_Diario and Volatilidad_Diaria columns (as in generator)
        # ensure frontier sorted by return
        ff = frontier_df.dropna().copy()
        # possible names: 'Retorno_Diario' / 'Volatilidad_Diaria'
        r_col_candidates = [c for c in ff.columns if 'retorno' in c.lower()]
        v_col_candidates = [c for c in ff.columns if 'volatilidad' in c.lower() or 'vol' in c.lower()]
        if len(r_col_candidates)==0 or len(v_col_candidates)==0:
            st.error("El archivo frontier.csv no contiene las columnas esperadas (Retorno_Diario/Volatilidad_Diaria).")
            st.stop()
        rcol = r_col_candidates[0]
        vcol = v_col_candidates[0]
        ff = ff.sort_values(rcol)
        r_vals = ff[rcol].values.astype(float)
        v_vals = ff[vcol].values.astype(float)

        # If port_ret_daily outside frontier return range -> not on frontier
        on_frontier = False
        reason = ""
        if (port_ret_daily < r_vals.min()) or (port_ret_daily > r_vals.max()):
            on_frontier = False
            reason = "El retorno del portafolio está fuera del rango de retornos de la frontera precomputada."
        else:
            # linear interp
            frontier_vol_at_ret = float(np.interp(port_ret_daily, r_vals, v_vals))
            diff = port_vol_daily - frontier_vol_at_ret
            rel = diff / frontier_vol_at_ret if frontier_vol_at_ret != 0 else diff
            on_frontier = (abs(rel) <= tol_rel)
            reason = f"Vol_port_diario - Vol_frontera = {diff:.6f} (rel {rel:.3%})"

        # Compare with GMVP and MaxSharpe by metric proximity
        # compute gmvp and ms metrics from weights in ZIP
        gmvp_weights = gmvp_series.reindex(master_tickers).fillna(0).values
        ms_weights = ms_series.reindex(master_tickers).fillna(0).values

        gmvp_ret_daily = float(np.dot(gmvp_weights, means))
        gmvp_vol_daily = float(np.sqrt(np.dot(gmvp_weights, cov.dot(gmvp_weights))))
        ms_ret_daily = float(np.dot(ms_weights, means))
        ms_vol_daily = float(np.sqrt(np.dot(ms_weights, cov.dot(ms_weights))))

        # annualize
        gmvp_ret_ann = gmvp_ret_daily * 252
        gmvp_vol_ann = gmvp_vol_daily * np.sqrt(252)
        ms_ret_ann = ms_ret_daily * 252
        ms_vol_ann = ms_vol_daily * np.sqrt(252)

        # check if equal (weights L2 small) or metrics very close
        eq_gmvp = np.linalg.norm(w - gmvp_weights) < 1e-3
        eq_ms = np.linalg.norm(w - ms_weights) < 1e-3
        # also check metrics closeness
        metrics_close_gm = (abs(port_ret_annual - gmvp_ret_ann) < 1e-3) and (abs(port_vol_annual - gmvp_vol_ann) < 1e-3)
        metrics_close_ms = (abs(port_ret_annual - ms_ret_ann) < 1e-3) and (abs(port_vol_annual - ms_vol_ann) < 1e-3)

        # Prepare results summary
        st.write("### ✅ Resultado de la simulación")
        colA, colB = st.columns(2)
        colA.metric("Retorno anual (usuario)", f"{port_ret_annual*100:.2f} %")
        colA.metric("Volatilidad anual (usuario)", f"{port_vol_annual*100:.2f} %")
        colB.metric("¿En frontera eficiente?", "Sí" if on_frontier else "No")
        if on_frontier:
            st.success("El portafolio está dentro de la frontera eficiente (dentro de la tolerancia).")
        else:
            st.error("El portafolio NO está en la frontera eficiente.")
        st.write("Detalle:", reason)

        # Indicar si coincide con óptimos
        if eq_gmvp or metrics_close_gm:
            st.info("El portafolio coincide con GMVP (aprox).")
        if eq_ms or metrics_close_ms:
            st.info("El portafolio coincide con MaxSharpe (aprox).")

        # Plot: frontier + user point + gmvp/ms
        fig = go.Figure()
        # frontier plotted annualized (x: vol ann, y: ret ann percent)
        fig.add_trace(go.Scatter(
            x=v_vals * np.sqrt(252) * 100,
            y=r_vals * 252 * 100,
            mode="lines+markers",
            name="Frontera Eficiente",
            line=dict(color="#00CFFF")
        ))
        # user point
        fig.add_trace(go.Scatter(
            x=[port_vol_annual*100], y=[port_ret_annual*100],
            mode="markers", marker=dict(color="gold", size=14, symbol="x"), name="Usuario"
        ))
        # gmvp
        fig.add_trace(go.Scatter(
            x=[gmvp_vol_ann*100], y=[gmvp_ret_ann*100],
            mode="markers", marker=dict(color="#FF4B4B", size=12, symbol="star"), name="GMVP"
        ))
        # ms
        fig.add_trace(go.Scatter(
            x=[ms_vol_ann*100], y=[ms_ret_ann*100],
            mode="markers", marker=dict(color="#00FF9D", size=12, symbol="star"), name="MaxSharpe"
        ))

        fig.update_layout(
            template="plotly_dark",
            title="Frontera Eficiente vs Portafolio Usuario",
            xaxis_title="Volatilidad Anual (%)",
            yaxis_title="Retorno Anual (%)"
        )
        st.plotly_chart(fig, use_container_width=True)

        # Prepare downloadable CSV of the simulation
        # For each ticker in user upload, include ticker, uploaded %, normalized weight, portfolio_return_annual, portfolio_volatility_annual, on_frontier
        out_df = user_df[['ticker','porcentaje','weight']].rename(columns={'ticker':'Ticker','porcentaje':'Porcentaje','weight':'Peso_normalizado'})
        out_df['Portfolio_Annual_Return_%'] = port_ret_annual*100
        out_df['Portfolio_Annual_Volatility_%'] = port_vol_annual*100
        out_df['On_Frontier'] = on_frontier
        csv_bytes = out_df.to_csv(index=False).encode('utf-8')
        st.download_button("Descargar resultados de esta simulación (CSV)", data=csv_bytes, file_name="simulacion_resultado.csv", mime="text/csv")

        # Finalizar simulación: guardar en file local para uso en página 3
        if st.button("🏁 Finalizar Simulación y Guardar"):
            saved_path = "user_simulations.csv"
            # prepare summary row
            summary = {
                "timestamp": pd.Timestamp.now(),
                "user_return_annual_%": port_ret_annual*100,
                "user_vol_annual_%": port_vol_annual*100,
                "on_frontier": on_frontier,
                "n_assets_user": int((w>0).sum())
            }
            # save detailed rows as separate CSV with appended filename or append to cumulative file
            # append summary to cumulative file
            if os.path.exists(saved_path):
                df_saved = pd.read_csv(saved_path)
                df_saved = pd.concat([df_saved, pd.DataFrame([summary])], ignore_index=True)
            else:
                df_saved = pd.DataFrame([summary])
            df_saved.to_csv(saved_path, index=False)
            # also save detailed upload for traceability
            user_details_file = f"user_sim_detail_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv"
            out_df.to_csv(user_details_file, index=False)
            st.success(f"Simulación guardada. Resumen en: {saved_path} . Detalle en: {user_details_file}")

else:
    st.info("Sube un CSV para activar la simulación (ver ejemplo).")

# -------------------------
# Footer / notas
# -------------------------
st.markdown("---")
st.caption("Notas: La comparación con la frontera usa interpolación lineal entre los puntos precomputados. "
           "La precisión depende de la densidad de puntos en frontier.csv y de la tolerancia relativa seleccionada.")
