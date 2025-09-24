import streamlit as st
import pandas as pd
import numpy as np
import os
import zipfile
import gdown

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
CAPITAL_INICIAL = 200_000_000  # Ejemplo 200 millones

if uploaded:
    try:
        df_user = pd.read_csv(uploaded)
        st.success("✅ CSV cargado correctamente")
        st.dataframe(df_user)
    except Exception as e:
        st.error(f"❌ Error leyendo tu CSV: {e}")

# -----------------------
# Botón iniciar simulación
# -----------------------
if st.button("🚀 Iniciar Simulación") and df_user is not None:

    st.info("Simulación en ejecución...")

    # -----------------------
    # Paso 1: Descargar y extraer ZIP de Drive
    # -----------------------
    ZIP_URL = "https://drive.google.com/uc?id=1sgshq-1MLrO1oToV8uu-iM4SPnvgT149"
    ZIP_NAME = "acciones_2024.zip"
    CARPETA_DATOS = "Acciones_2024"

    if not os.path.exists(ZIP_NAME):
        gdown.download(ZIP_URL, ZIP_NAME, quiet=False)

    if not os.path.exists(CARPETA_DATOS):
        with zipfile.ZipFile(ZIP_NAME, 'r') as zip_ref:
            zip_ref.extractall(".")

    # -----------------------
    # Paso 2: Leer precios de los tickers del usuario
    # -----------------------
    precios = {}
    primer_dia_precios = {}
    tickers_validos = []

    for ticker in df_user['Ticker']:
        file_path = os.path.join(CARPETA_DATOS, f"{ticker}.csv")
        if os.path.exists(file_path):
            df_ticker = pd.read_csv(file_path, parse_dates=['Date']).sort_values('Date')
            df_ticker = df_ticker.set_index('Date')
            precios[ticker] = df_ticker['Close']  # Precios diarios para portafolio
            primer_dia_precios[ticker] = df_ticker['Open'].iloc[0]  # Open primer día
            tickers_validos.append(ticker)
        else:
            st.warning(f"⚠️ No se encontró archivo para {ticker}, se ignorará.")

    if not precios:
        st.error("❌ No hay tickers válidos para simular.")
    else:
        # DataFrame de precios alineado con tickers válidos
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
        rentabilidad_acumulada = df_portafolio.iloc[-1] / df_portafolio.iloc[0] - 1
        rentabilidad_anualizada = (1 + retornos_diarios.mean())**252 - 1
        riesgo_anualizado = retornos_diarios.std() * np.sqrt(252)
        sharpe_ratio = rentabilidad_anualizada / riesgo_anualizado

        dias_arriba = (df_portafolio > CAPITAL_INICIAL).sum()
        dias_abajo = (df_portafolio <= CAPITAL_INICIAL).sum()

        # -----------------------
        # Paso 6: Mostrar resultados
        # -----------------------
        st.subheader("📈 Resultados del Portafolio")
        st.write(f"Rentabilidad anualizada: {rentabilidad_anualizada:.2%}")
        st.write(f"Riesgo (volatilidad anualizada): {riesgo_anualizado:.2%}")
        st.write(f"Sharpe Ratio: {sharpe_ratio:.2f}")
        st.write(f"Días por encima del capital inicial: {dias_arriba}")
        st.write(f"Días por debajo del capital inicial: {dias_abajo}")

        # -----------------------
        # Paso 7: Guardar resultados en CSV
        # -----------------------
        resultados = pd.DataFrame({
            "Grupo": ["Nombre_Grupo"],  # Aquí podrías usar el nombre de la sesión
            "Rentabilidad Anualizada": [rentabilidad_anualizada],
            "Riesgo": [riesgo_anualizado],
            "Sharpe": [sharpe_ratio],
            "Días Arriba": [dias_arriba],
            "Días Abajo": [dias_abajo]
        })
        st.download_button(
            "💾 Descargar resultados CSV",
            resultados.to_csv(index=False),
            file_name="resultados_portafolio.csv"
        )

        # -----------------------
        # Paso 8: Medallas (ejemplo estático)
        # -----------------------
        st.subheader("🏅 Medallas y Reconocimientos")
        st.write("🥇 Mejor Sharpe Ratio: Grupo Alfa")
        st.write("🥇 Mayor Rentabilidad: Grupo Gama")
        st.write("🥇 Menor Riesgo: Grupo Delta")
        st.write("🥈 Buen equilibrio: Grupo Beta")
