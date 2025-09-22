import streamlit as st
import pandas as pd
import numpy as np
import io
import zipfile
import gdown
import os

# ================================
# CONFIGURACIÓN DE LA PÁGINA
# ================================
#st.set_page_config(page_title="📄 Página 2 — Simulación de Portafolio", layout="wide")

st.title("📄 Página 2 — Simulación de Portafolio")
st.write("""
En esta página podrás **subir tu propio portafolio en formato CSV**, 
simular su comportamiento y comparar sus resultados con los portafolios óptimos 
(GMVP y Max Sharpe) que tenemos precomputados.  
""")

# ================================
# DESCARGA DE EJEMPLO DE CSV
# ================================
ejemplo = pd.DataFrame({
    "Ticker": ["AAPL", "MSFT", "GOOGL", "AMZN"],
    "% del Portafolio": [25, 25, 25, 25]
})
csv_ejemplo = ejemplo.to_csv(index=False)

st.download_button(
    label="📥 Descargar Ejemplo de CSV",
    data=csv_ejemplo,
    file_name="ejemplo_portafolio.csv",
    mime="text/csv"
)

# ================================
# SUBIDA DE ARCHIVO DEL USUARIO
# ================================
st.subheader("📤 Sube tu archivo CSV")
uploaded_file = st.file_uploader("Selecciona tu archivo CSV con la composición del portafolio", type="csv")

df_user = None
if uploaded_file is not None:
    try:
        df_user = pd.read_csv(uploaded_file)
        st.success("✅ Archivo cargado correctamente")
        st.dataframe(df_user)
    except Exception as e:
        st.error(f"❌ Error al leer el archivo: {e}")

# ================================
# DESCARGA Y CARGA DE DATOS HISTÓRICOS
# ================================
st.info("📥 Cargando artefactos precomputados desde Google Drive...")

# ID del ZIP en Google Drive
ZIP_FILE_ID = "1cJFHOWURl7DYEYc4r4SWvAvV3Sl7bZCB"
ZIP_OUTPUT = "datos_acciones.zip"
DATA_FOLDER = "acciones"

try:
    if not os.path.exists(DATA_FOLDER):
        gdown.download(f"https://drive.google.com/uc?id={ZIP_FILE_ID}", ZIP_OUTPUT, quiet=False)
        with zipfile.ZipFile(ZIP_OUTPUT, "r") as zip_ref:
            zip_ref.extractall(DATA_FOLDER)

    st.success("✅ Datos históricos cargados correctamente")
except Exception as e:
    st.error(f"❌ No se pudieron cargar los artefactos precomputados desde Drive: {e}")

# ================================
# LECTURA DE LOS ARCHIVOS CSV
# ================================
dataframes = {}
if os.path.exists(DATA_FOLDER):
    for file in os.listdir(DATA_FOLDER):
        if file.endswith(".csv"):
            ticker = file.split("_")[0].upper()  # 👉 extrae solo el ticker
            try:
                df = pd.read_csv(os.path.join(DATA_FOLDER, file))
                if "Adj Close" in df.columns:
                    dataframes[ticker] = df
                else:
                    st.warning(f"⚠️ {file} no tiene columna 'Adj Close'.")
            except Exception as e:
                st.warning(f"⚠️ No se pudo cargar {file}: {e}")

# ================================
# SIMULACIÓN DEL PORTAFOLIO
# ================================
if df_user is not None and not df_user.empty:
    if st.button("🚀 Iniciar Simulación"):
        try:
            # Normalizar nombres de columnas del CSV del usuario
            df_user.columns = [col.strip().lower() for col in df_user.columns]

            # Detectar columnas de ticker y pesos
            col_ticker = None
            col_weight = None
            for col in df_user.columns:
                if "tick" in col:
                    col_ticker = col
                if "por" in col or "%" in col or "weight" in col:
                    col_weight = col

            if col_ticker is None or col_weight is None:
                st.error("❌ El CSV debe contener columnas con 'Ticker' y 'Porcentaje'.")
            else:
                # Normalizar pesos
                df_user[col_weight] = df_user[col_weight] / df_user[col_weight].sum()

                tickers = [t.upper() for t in df_user[col_ticker].tolist()]
                weights = df_user[col_weight].values

                # Construir matriz de retornos
                returns_data = []
                valid_tickers = []
                for ticker in tickers:
                    if ticker in dataframes:
                        df = dataframes[ticker]
                        returns = df["Adj Close"].pct_change().dropna()
                        returns_data.append(returns)
                        valid_tickers.append(ticker)
                    else:
                        st.error(f"❌ No se encontraron datos históricos para {ticker}.")

                if returns_data:
                    returns_matrix = pd.concat(returns_data, axis=1)
                    returns_matrix.columns = valid_tickers

                    mean_returns = returns_matrix.mean()
                    cov_matrix = returns_matrix.cov()

                    # Retorno y volatilidad del portafolio del usuario
                    port_return = np.dot(weights[:len(valid_tickers)], mean_returns) * 252  # anualizado
                    port_vol = np.sqrt(np.dot(weights[:len(valid_tickers)].T,
                                              np.dot(cov_matrix * 252, weights[:len(valid_tickers)])))

                    st.subheader("📌 Resultados de tu Portafolio")
                    st.write(f"**Retorno anual esperado:** {port_return:.2%}")
                    st.write(f"**Volatilidad anual esperada:** {port_vol:.2%}")

                    # Guardar resultados en session_state
                    st.session_state["simulacion_resultados"] = {
                        "user": {"retorno": float(port_return), "riesgo": float(port_vol)},
                        "acciones": valid_tickers,
                        "pesos": weights[:len(valid_tickers)].tolist()
                    }

                    # Exportar resultados
                    results_df = pd.DataFrame({
                        "Ticker": valid_tickers,
                        "% del Portafolio": weights[:len(valid_tickers)] * 100,
                        "Portafolio": "Usuario"
                    })

                    st.download_button(
                        label="💾 Descargar resultados en CSV",
                        data=results_df.to_csv(index=False),
                        file_name="resultado_usuario.csv",
                        mime="text/csv"
                    )

                    st.success("✅ Simulación finalizada. Resultados listos para comparar en Página 3.")

        except Exception as e:
            st.error(f"❌ Error en la simulación: {e}")

