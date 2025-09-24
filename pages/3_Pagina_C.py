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

# Tomamos el nombre del grupo desde el login
nombre_grupo = st.session_state.get("username", "Grupo_Desconocido")

# -----------------------
# Subida CSV
# -----------------------
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

    # Descargar/extraer ZIP si no existe
    if not os.path.exists(ZIP_NAME):
        gdown.download(ZIP_URL, ZIP_NAME, quiet=False)

    if not os.path.exists(CARPETA_DATOS):
        with zipfile.ZipFile(ZIP_NAME, 'r') as zip_ref:
            zip_ref.extractall(".")

    # -----------------------
    # Leer precios de los tickers del usuario
    # -----------------------
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
        # Distribución monetaria y cantidad de acciones (enteras)
        # -----------------------
        df_user['MontoInvertido'] = (df_user["% del Portafolio"] / 100) * CAPITAL_INICIAL
        df_user['CantidadAcciones'] = df_user.apply(
            lambda row: int(row['MontoInvertido'] // primer_dia_precios[row['Ticker']]),
            axis=1
        )
        df_user['MontoAsignado'] = df_user.apply(
            lambda row: row['CantidadAcciones'] * primer_dia_precios[row['Ticker']],
            axis=1
        )

        # -----------------------
        # Valor diario del portafolio
        # -----------------------
        valores_diarios = df_precios * df_user['CantidadAcciones'].values
        df_valores_diarios = valores_diarios.copy()
        df_valores_diarios['PortafolioTotal'] = df_valores_diarios.sum(axis=1)

        # -----------------------
        # Retornos y métricas
        # -----------------------
        retornos_diarios = df_valores_diarios['PortafolioTotal'].pct_change().fillna(0)
        rent_anual = (1 + retornos_diarios.mean())**252 - 1
        riesgo_anual = retornos_diarios.std() * np.sqrt(252)
        sharpe = rent_anual / riesgo_anual if riesgo_anual > 0 else 0

        dias_arriba = (df_valores_diarios['PortafolioTotal'] > CAPITAL_INICIAL).sum()
        dias_abajo = (df_valores_diarios['PortafolioTotal'] <= CAPITAL_INICIAL).sum()

        ganancia_prom_arriba = df_valores_diarios['PortafolioTotal'][df_valores_diarios['PortafolioTotal'] > CAPITAL_INICIAL].mean()
        perdida_prom_abajo = df_valores_diarios['PortafolioTotal'][df_valores_diarios['PortafolioTotal'] <= CAPITAL_INICIAL].mean()
        ganancia_total = df_valores_diarios['PortafolioTotal'].iloc[-1] - CAPITAL_INICIAL

        resultados = pd.DataFrame({
            "Grupo": [nombre_grupo],
            "RentabilidadAnualizada": [rent_anual],
            "Riesgo": [riesgo_anual],
            "Sharpe": [sharpe],
            "DiasArriba": [dias_arriba],
            "DiasAbajo": [dias_abajo],
            "GananciaPromArriba": [ganancia_prom_arriba],
            "PerdidaPromAbajo": [perdida_prom_abajo],
            "GananciaTotal": [ganancia_total]
        })

        # -----------------------
        # Mostrar resultados
        # -----------------------
        st.subheader("📈 Resultados del Portafolio")
        resultados_formateado = resultados.copy()
        for col in resultados_formateado.columns[1:]:
            resultados_formateado[col] = resultados_formateado[col].map(lambda x: f"{x:,.2f}")
        st.dataframe(resultados_formateado)

        st.subheader("💰 Valores diarios del portafolio")
        df_valores_diarios_form = df_valores_diarios.copy()
        df_valores_diarios_form = df_valores_diarios_form.applymap(lambda x: f"{x:,.0f}")
        st.dataframe(df_valores_diarios_form)

        # -----------------------
        # Descargar CSV resultados
        # -----------------------
        st.download_button(
            "💾 Descargar resultados CSV",
            resultados.to_csv(index=False),
            file_name=f"resultados_{nombre_grupo}.csv"
        )

        st.info("Por favor descarga los resultados para subirlos en la siguiente pestaña.")
