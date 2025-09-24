import streamlit as st
import pandas as pd
import numpy as np
import os
import zipfile
import gdown

# -----------------------
# Configuración
# -----------------------
CAPITAL_INICIAL = 200_000_000
ZIP_URL = "https://drive.google.com/uc?id=1sgshq-1MLrO1oToV8uu-iM4SPnvgT149"
ZIP_NAME = "acciones_2024.zip"
CARPETA_DATOS = "Acciones_2024"

# -----------------------
# Interfaz
# -----------------------
st.title("Simulación de Portafolio")

st.write("""
Sube un CSV con columnas `Ticker` y `% del Portafolio`.  
Puedes descargar el ejemplo para guiarte en el formato correcto.
""")

# Ejemplo CSV
ejemplo = pd.DataFrame({
    "Ticker": ["AAPL", "MSFT", "GOOGL"],
    "% del Portafolio": [40, 30, 30]
})
st.download_button(
    "📥 Descargar ejemplo CSV",
    ejemplo.to_csv(index=False),
    file_name="ejemplo_portafolio.csv"
)

# Subida CSV usuario
uploaded = st.file_uploader("📂 Sube tu CSV (Ticker, % del Portafolio)", type=["csv"])
df_user = None

# Usar el nombre de grupo desde el login
if "username" in st.session_state:
    nombre_grupo = st.session_state["username"]
else:
    st.error("❌ No se detectó sesión activa. Por favor inicia sesión.")
    st.stop()

if uploaded:
    try:
        df_user = pd.read_csv(uploaded)
        st.success("✅ CSV cargado correctamente")
        st.dataframe(df_user)
    except Exception as e:
        st.error(f"❌ Error leyendo tu CSV: {e}")

# -----------------------
# Botón finalizar simulación
# -----------------------
if st.button("🚀 Finalizar Simulación") and df_user is not None:

    st.info("Simulación en ejecución...")

    # Paso 1: descargar/extraer ZIP si no existe
    if not os.path.exists(ZIP_NAME):
        gdown.download(ZIP_URL, ZIP_NAME, quiet=False)

    if not os.path.exists(CARPETA_DATOS):
        with zipfile.ZipFile(ZIP_NAME, 'r') as zip_ref:
            zip_ref.extractall(".")

    # Paso 2: leer precios reales de los tickers del usuario
    precios = {}
    primer_dia_precios = {}
    tickers_validos = []

    for ticker in df_user['Ticker']:
        file_path = os.path.join(CARPETA_DATOS, f"{ticker}.csv")
        if os.path.exists(file_path):
            df_ticker = pd.read_csv(file_path, parse_dates=['Date']).sort_values('Date')
            df_ticker = df_ticker.set_index('Date')
            precios[ticker] = df_ticker['Close']
            primer_dia_precios[ticker] = df_ticker['Open'].iloc[0]
            tickers_validos.append(ticker)
        else:
            st.warning(f"⚠️ No se encontró archivo para {ticker}, se ignorará.")

    if not precios:
        st.error("❌ No hay tickers válidos para simular.")
    else:
        df_precios = pd.DataFrame(precios)
        df_user = df_user[df_user['Ticker'].isin(tickers_validos)].reset_index(drop=True)

        # -----------------------
        # Paso 3: Calcular monto invertido y cantidad de acciones
        # -----------------------
        df_user['Monto Invertido'] = (df_user["% del Portafolio"] / 100) * CAPITAL_INICIAL
        df_user['Cantidad Acciones'] = df_user.apply(
            lambda row: row['Monto Invertido'] / primer_dia_precios[row['Ticker']], axis=1
        )

        # -----------------------
        # Paso 4: Calcular valor diario del portafolio
        # -----------------------
        valores_diarios = df_precios * df_user['Cantidad Acciones'].values
        df_portafolio = valores_diarios.sum(axis=1)

        # -----------------------
        # Paso 5: Calcular métricas
        # -----------------------
        retornos_diarios = df_portafolio.pct_change().fillna(0)
        rentabilidad_anualizada = (1 + retornos_diarios.mean())**252 - 1
        riesgo_anualizado = retornos_diarios.std() * np.sqrt(252)
        sharpe_ratio = rentabilidad_anualizada / riesgo_anualizado if riesgo_anualizado > 0 else 0

        dias_arriba = (df_portafolio > CAPITAL_INICIAL)
        dias_abajo = (df_portafolio <= CAPITAL_INICIAL)

        ganancia_promedio_arriba = (df_portafolio[dias_arriba] - CAPITAL_INICIAL).mean() if dias_arriba.sum() > 0 else 0
        perdida_promedio_abajo = (df_portafolio[dias_abajo] - CAPITAL_INICIAL).mean() if dias_abajo.sum() > 0 else 0
        ganancia_total = df_portafolio.iloc[-1] - CAPITAL_INICIAL

        resultados = pd.DataFrame({
            "Grupo": [nombre_grupo],
            "Rentabilidad Anualizada": [rentabilidad_anualizada],
            "Riesgo": [riesgo_anualizado],
            "Sharpe": [sharpe_ratio],
            "Días Arriba": [dias_arriba.sum()],
            "Días Abajo": [dias_abajo.sum()],
            "Ganancia Promedio Arriba": [ganancia_promedio_arriba],
            "Pérdida Promedio Abajo": [perdida_promedio_abajo],
            "Ganancia Total": [ganancia_total]
        })

        # -----------------------
        # Paso 6: Mostrar resultados
        # -----------------------
        st.subheader("📈 Resultados del Portafolio")
        st.dataframe(resultados)

        # -----------------------
        # Paso 7: Descargar resultados
        # -----------------------
        st.download_button(
            "💾 Descargar resultados CSV",
            resultados.to_csv(index=False, encoding='utf-8-sig'),
            file_name=f"resultados_{nombre_grupo}.csv"
        )

        st.info("📌 Por favor descarga los resultados para subirlos en la siguiente pestaña.")
