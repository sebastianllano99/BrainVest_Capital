# 3_Pagina_C.py
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

# Obtener el nombre del grupo desde el login
nombre_grupo = st.session_state.get("username", "Grupo_Anonimo")

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
            precios[ticker] = df_ticker['Close']  # Precios diarios
            primer_dia_precios[ticker] = df_ticker['Open'].iloc[0]  # Precio de apertura primer día
            tickers_validos.append(ticker)
        else:
            st.warning(f"⚠️ No se encontró archivo para {ticker}, se ignorará.")

    if not precios:
        st.error("❌ No hay tickers válidos para simular.")
    else:
        # DataFrame de precios alineado
        df_precios = pd.DataFrame(precios)
        df_user = df_user[df_user['Ticker'].isin(tickers_validos)].reset_index(drop=True)

        # Paso 3: Calcular monto invertido y cantidad de acciones (enteros)
        df_user['Monto Destinado'] = (df_user["% del Portafolio"] / 100) * CAPITAL_INICIAL
        df_user['Cantidad Acciones'] = (df_user['Monto Destinado'] / df_user['Ticker'].map(primer_dia_precios)).apply(np.floor)
        df_user['Monto Real Invertido'] = df_user['Cantidad Acciones'] * df_user['Ticker'].map(primer_dia_precios)

        # Paso 4: Calcular valor diario de cada acción
        valores_diarios = df_precios * df_user['Cantidad Acciones'].values
        df_valores_diarios = valores_diarios.copy()
        df_valores_diarios['Suma Diaria Portafolio'] = df_valores_diarios.sum(axis=1)

        # Paso 5: Calcular métricas
        df_portafolio = df_valores_diarios['Suma Diaria Portafolio']
        retornos_diarios = df_portafolio.pct_change().fillna(0)
        rent_anual = (1 + retornos_diarios.mean())**252 - 1
        riesgo_anual = retornos_diarios.std() * np.sqrt(252)
        sharpe = rent_anual / riesgo_anual if riesgo_anual > 0 else 0

        dias_arriba = (df_portafolio > CAPITAL_INICIAL).sum()
        dias_abajo = (df_portafolio <= CAPITAL_INICIAL).sum()

        ganancia_promedio_arriba = ((df_portafolio[df_portafolio > CAPITAL_INICIAL] - CAPITAL_INICIAL).mean() 
                                    if dias_arriba > 0 else 0)
        perdida_promedio_abajo = ((CAPITAL_INICIAL - df_portafolio[df_portafolio <= CAPITAL_INICIAL]).mean() 
                                  if dias_abajo > 0 else 0)
        ganancia_total = df_portafolio.iloc[-1] - CAPITAL_INICIAL

        # Paso 6: Mostrar resultados
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
        st.dataframe(resultados.style.format("{:.2f}"))

        st.subheader("💰 Valores diarios del portafolio")
        st.dataframe(df_valores_diarios.style.format("{:,.0f}"))

        # Paso 7: Descargar resultados
        st.download_button(
            "💾 Descargar resultados CSV",
            resultados.to_csv(index=False),
            file_name=f"resultados_{nombre_grupo}.csv"
        )

        st.info("Por favor descarga los resultados para que los subas en la siguiente pestaña.")
