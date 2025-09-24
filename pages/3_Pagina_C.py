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

# -----------------------
# Interfaz
# -----------------------
st.title("Simulación de Portafolio")

st.write("""
Sube un CSV con columnas `Ticker` y `% del Portafolio`.
Puedes descargar el ejemplo para guiarte en el formato correcto.
""")

ejemplo = pd.DataFrame({
    "Ticker": ["AAPL", "MSFT", "GOOGL"],
    "% del Portafolio": [40, 30, 30]
})
st.download_button(
    "📥 Descargar ejemplo CSV",
    ejemplo.to_csv(index=False),
    file_name="ejemplo_portafolio.csv"
)

uploaded = st.file_uploader("📂 Sube tu CSV (Ticker, % del Portafolio)", type=["csv"])
df_user = None

# Tomar el nombre del grupo directamente del login
nombre_grupo = st.session_state.get("username", "")

# -----------------------
# Leer CSV subido
# -----------------------
if uploaded:
    try:
        df_user = pd.read_csv(uploaded)
        st.success("✅ CSV cargado correctamente")
        st.dataframe(df_user)
    except Exception as e:
        st.error(f"❌ Error leyendo tu CSV: {e}")

# -----------------------
# Botón Finalizar Simulación
# -----------------------
if st.button("🚀 Finalizar Simulación") and df_user is not None and nombre_grupo != "":

    st.info("Simulación en ejecución...")

    # Paso 1: Descargar/Extraer ZIP
    if not os.path.exists(ZIP_NAME):
        gdown.download(ZIP_URL, ZIP_NAME, quiet=False)

    if not os.path.exists(CARPETA_DATOS):
        with zipfile.ZipFile(ZIP_NAME, 'r') as zip_ref:
            zip_ref.extractall(".")

    # Paso 2: Leer precios de los tickers del usuario
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
        # Alinear tickers válidos
        df_precios = pd.DataFrame(precios)
        df_user = df_user[df_user['Ticker'].isin(tickers_validos)].reset_index(drop=True)

        # Paso 3: Distribución monetaria y cantidad de acciones
        df_user['Monto Invertido'] = (df_user["% del Portafolio"] / 100) * CAPITAL_INICIAL
        df_user['Cantidad Acciones'] = df_user.apply(
            lambda row: row['Monto Invertido'] / primer_dia_precios[row['Ticker']], axis=1
        )

        # Mostrar tabla de distribución monetaria
        st.subheader("💰 Distribución de inversión por acción")
        st.dataframe(df_user[['Ticker', '% del Portafolio', 'Monto Invertido', 'Cantidad Acciones']])

        # Paso 4: Valor diario del portafolio
        valores_diarios = df_precios * df_user['Cantidad Acciones'].values
        df_portafolio = valores_diarios.sum(axis=1)

        # Paso 5: Métricas de rentabilidad y riesgo
        retornos_diarios = df_portafolio.pct_change().fillna(0)
        rent_anual = (1 + retornos_diarios.mean())**252 - 1
        riesgo_anual = retornos_diarios.std() * np.sqrt(252)
        sharpe = rent_anual / riesgo_anual if riesgo_anual > 0 else 0

        dias_arriba = (df_portafolio > CAPITAL_INICIAL)
        dias_abajo = (df_portafolio <= CAPITAL_INICIAL)
        num_arriba = dias_arriba.sum()
        num_abajo = dias_abajo.sum()

        # Ganancia/Pérdida por día
        ganancia_diaria = df_portafolio - CAPITAL_INICIAL
        ganancia_prom_arriba = ganancia_diaria[dias_arriba].mean() if num_arriba > 0 else 0
        perdida_prom_abajo = ganancia_diaria[dias_abajo].mean() if num_abajo > 0 else 0
        ganancia_total = ganancia_diaria.iloc[-1]

        # Paso 6: Mostrar resultados
        st.subheader("📈 Resultados del Portafolio")
        st.write(f"Rentabilidad anualizada: {rent_anual:.2%}")
        st.write(f"Riesgo (volatilidad anualizada): {riesgo_anual:.2%}")
        st.write(f"Sharpe Ratio: {sharpe:.2f}")
        st.write(f"Días por encima del capital inicial: {num_arriba} | Ganancia promedio: ${ganancia_prom_arriba:,.0f}")
        st.write(f"Días por debajo del capital inicial: {num_abajo} | Pérdida promedio: ${perdida_prom_abajo:,.0f}")
        st.write(f"Ganancia/Pérdida total al final del año: ${ganancia_total:,.0f}")

        # Paso 7: Descargar resultados CSV
        resultados = pd.DataFrame({
            "Grupo": [nombre_grupo],
            "Rentabilidad Anualizada": [rent_anual],
            "Riesgo": [riesgo_anual],
            "Sharpe": [sharpe],
            "Días Arriba": [num_arriba],
            "Días Abajo": [num_abajo],
            "Ganancia Promedio Arriba": [ganancia_prom_arriba],
            "Pérdida Promedio Abajo": [perdida_prom_abajo],
            "Ganancia Total": [ganancia_total]
        })
        st.download_button(
            "💾 Descargar resultados CSV",
            resultados.to_csv(index=False),
            file_name=f"resultados_{nombre_grupo}.csv"
        )
        st.info("Por favor descarga los resultados para subirlos en la siguiente pestaña.")

