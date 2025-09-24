import streamlit as st
import pandas as pd
import numpy as np
import os
import zipfile
import gdown
import sqlite3

# -----------------------
# Configuración
# -----------------------
CAPITAL_INICIAL = 200_000_000
ZIP_URL = "https://drive.google.com/uc?id=1sgshq-1MLrO1oToV8uu-iM4SPnvgT149"
ZIP_NAME = "acciones_2024.zip"
CARPETA_DATOS = "Acciones_2024"

# Conexión a DB de login para obtener nombre de grupo
conn = sqlite3.connect("jugadores.db")
c = conn.cursor()

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

# Obtener nombre de grupo desde login
nombre_grupo = st.session_state.get("username", "Grupo_Anonimo")

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
        # Paso 3: Calcular distribución monetaria
        # -----------------------
        df_user['Monto Invertido'] = (df_user["% del Portafolio"] / 100) * CAPITAL_INICIAL
        df_user['Cantidad Acciones'] = df_user.apply(
            lambda row: row['Monto Invertido'] / primer_dia_precios[row['Ticker']], axis=1
        )

        st.subheader("💰 Distribución Monetaria por Acción")
        df_dist = df_user[['Ticker', '% del Portafolio', 'Monto Invertido', 'Cantidad Acciones']].copy()
        df_dist = df_dist.rename(columns={"% del Portafolio": "Porcentaje Portafolio"})
        st.dataframe(df_dist)

        # -----------------------
        # Paso 4: Valor diario del portafolio
        # -----------------------
        valores_diarios_accion = df_precios * df_user['Cantidad Acciones'].values
        df_portafolio = valores_diarios_accion.sum(axis=1)

        st.subheader("📊 Valor Diario de Cada Acción")
        st.write("Valor diario de cada acción según la cantidad de acciones compradas.")
        st.dataframe(valores_diarios_accion)

        # -----------------------
        # Paso 5: Ganancia / Pérdida diaria
        # -----------------------
        ganancia_perdida_accion = valores_diarios_accion - df_user['Monto Invertido'].values
        st.subheader("📈 Ganancia/Pérdida Diaria por Acción")
        st.dataframe(ganancia_perdida_accion)

        # -----------------------
        # Paso 6: Métricas del portafolio
        # -----------------------
        retornos_diarios = df_portafolio.pct_change().fillna(0)
        rent_anual = (1 + retornos_diarios.mean())**252 - 1
        riesgo_anual = retornos_diarios.std() * np.sqrt(252)
        sharpe = rent_anual / riesgo_anual if riesgo_anual > 0 else 0

        dias_arriba = (df_portafolio > CAPITAL_INICIAL).sum()
        dias_abajo = (df_portafolio <= CAPITAL_INICIAL).sum()

        # Ganancia promedio días arriba y pérdida promedio días abajo
        ganancia_promedio_arriba = (df_portafolio[df_portafolio > CAPITAL_INICIAL] - CAPITAL_INICIAL).mean() if dias_arriba>0 else 0
        perdida_promedio_abajo = (df_portafolio[df_portafolio <= CAPITAL_INICIAL] - CAPITAL_INICIAL).mean() if dias_abajo>0 else 0
        ganancia_total = df_portafolio.iloc[-1] - CAPITAL_INICIAL

        resultados = pd.DataFrame({
            "Grupo": [nombre_grupo],
            "Rentabilidad Anualizada": [rent_anual],
            "Riesgo": [riesgo_anual],
            "Sharpe": [sharpe],
            "Dias Arriba": [dias_arriba],
            "Dias Abajo": [dias_abajo],
            "Ganancia Promedio Arriba": [ganancia_promedio_arriba],
            "Perdida Promedio Abajo": [perdida_promedio_abajo],
            "Ganancia Total": [ganancia_total]
        })

        st.subheader("📈 Resultados del Portafolio")
        st.dataframe(resultados)

        # -----------------------
        # Paso 7: Descargar resultados
        # -----------------------
        st.download_button(
            "💾 Descargar resultados CSV",
            resultados.to_csv(index=False),
            file_name=f"resultados_{nombre_grupo}.csv"
        )
        st.info("Por favor descarga los resultados para subirlos en la siguiente pestaña.")
