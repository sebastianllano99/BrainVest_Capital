import streamlit as st
import pandas as pd
import numpy as np
import os
import zipfile
import io

# ================================
# CONFIGURACIÓN DE LA PÁGINA
# ================================
#st.set_page_config(page_title="Página 2 — Simulación de Portafolio", layout="wide")

st.title("📊 Página 2 — Simulación de Portafolio")
st.markdown("""
En esta página podrás **subir la composición de tu portafolio en formato CSV**  
y simular su rendimiento con base en los datos históricos procesados.  

**Pasos:**
1. Descarga el archivo CSV de ejemplo y úsalo como plantilla.  
2. Llena la columna de `% del Portafolio` asegurándote que la suma sea **100%**.  
3. Sube tu archivo CSV en el cargador.  
4. Pulsa **Iniciar Simulación** para calcular métricas y compararlas con la frontera eficiente.
""")

# ================================
# DESCARGA DE CSV DE EJEMPLO
# ================================
example_df = pd.DataFrame({
    "Ticker": ["AAPL", "MSFT", "GOOGL"],
    "% del Portafolio": [40, 35, 25]
})

buffer = io.StringIO()
example_df.to_csv(buffer, index=False)
st.download_button(
    label="📥 Descargar CSV de ejemplo",
    data=buffer.getvalue(),
    file_name="ejemplo_portafolio.csv",
    mime="text/csv"
)

st.divider()

# ================================
# SUBIDA DEL ARCHIVO DEL USUARIO
# ================================
uploaded_file = st.file_uploader("📂 Sube tu archivo CSV de portafolio", type=["csv"])

df_user = None
if uploaded_file is not None:
    try:
        df_user = pd.read_csv(uploaded_file)
        st.success("✅ Archivo cargado correctamente")
        st.dataframe(df_user)
    except Exception as e:
        st.error(f"❌ Error al leer el archivo: {e}")

# ================================
# CARGAR DATOS DE HISTÓRICOS (ZIP)
# ================================
ZIP_PATH = "acciones.zip"  # <-- ajusta si el ZIP está en otra ruta
dataframes = {}

if os.path.exists(ZIP_PATH):
    try:
        with zipfile.ZipFile(ZIP_PATH, "r") as z:
            for filename in z.namelist():
                if filename.endswith(".csv"):
                    with z.open(filename) as f:
                        df = pd.read_csv(f, parse_dates=["Date"])
                        ticker = os.path.splitext(os.path.basename(filename))[0]
                        df.set_index("Date", inplace=True)
                        dataframes[ticker] = df
        st.info("📂 Datos históricos cargados correctamente desde el ZIP.")
    except Exception as e:
        st.error(f"❌ No se pudieron cargar los datos del ZIP: {e}")
else:
    st.warning("⚠️ No se encontró el archivo ZIP con los históricos (`acciones.zip`).")

# ================================
# SIMULACIÓN DEL PORTAFOLIO
# ================================
if df_user is not None and not df_user.empty:
    if st.button("🚀 Iniciar Simulación"):
        try:
            # Normalizar pesos (asegurar 100%)
            df_user["% del Portafolio"] = df_user["% del Portafolio"] / df_user["% del Portafolio"].sum()

            tickers = df_user["Ticker"].tolist()
            weights = df_user["% del Portafolio"].values

            # Construir matriz de retornos
            returns_data = []
            for ticker in tickers:
                if ticker in dataframes:
                    df = dataframes[ticker]
                    returns = df["Adj Close"].pct_change().dropna()
                    returns_data.append(returns)
                else:
                    st.error(f"❌ No se encontraron datos históricos para {ticker}.")
                    returns_data = []
                    break

            if returns_data:
                returns_matrix = pd.concat(returns_data, axis=1)
                returns_matrix.columns = tickers

                mean_returns = returns_matrix.mean()
                cov_matrix = returns_matrix.cov()

                # Cálculo del portafolio del usuario
                port_return = np.dot(weights, mean_returns) * 252  # anualizado
                port_vol = np.sqrt(np.dot(weights.T, np.dot(cov_matrix * 252, weights)))

                st.subheader("📌 Resultados de tu Portafolio")
                st.write(f"**Retorno anual esperado:** {port_return:.2%}")
                st.write(f"**Volatilidad anual esperada:** {port_vol:.2%}")

                # Guardar resultados
                results_df = pd.DataFrame({
                    "Ticker": tickers,
                    "% del Portafolio": weights * 100,
                    "Portafolio": "Usuario"
                })

                results_path = "resultado_usuario.csv"
                results_df.to_csv(results_path, index=False)

                st.download_button(
                    label="💾 Descargar resultados en CSV",
                    data=results_df.to_csv(index=False),
                    file_name="resultado_usuario.csv",
                    mime="text/csv"
                )

                st.success("✅ Simulación finalizada. Resultados listos para comparar en Página 3.")

        except Exception as e:
            st.error(f"❌ Error en la simulación: {e}")

st.divider()
st.markdown("🔚 Cuando hayas terminado, puedes continuar a **Página 3** para comparar con la frontera eficiente.")

