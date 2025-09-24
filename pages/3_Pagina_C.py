# 3_Pagina_C_Fraccionarias.py
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
st.title("Simulación de Portafolio con Acciones Fraccionarias")

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

# Nombre del grupo desde login
nombre_grupo = st.session_state.get("username", "Grupo_Desconocido")

# -----------------------
# Botón finalizar simulación
# -----------------------
if st.button("🚀 Finalizar Simulación") and uploaded is not None:

    st.info("Simulación en ejecución...")

    try:
        df_user = pd.read_csv(uploaded)
        st.success("✅ CSV cargado correctamente")
        st.dataframe(df_user)
    except Exception as e:
        st.error(f"❌ Error leyendo tu CSV: {e}")
        st.stop()

    # Descargar/extraer ZIP si no existe
    if not os.path.exists(ZIP_NAME):
        gdown.download(ZIP_URL, ZIP_NAME, quiet=False)

    if not os.path.exists(CARPETA_DATOS):
        with zipfile.ZipFile(ZIP_NAME, 'r') as zip_ref:
            zip_ref.extractall(".")

    # -----------------------
    # Leer precios de los tickers
    # -----------------------
    precios = {}
    tickers_validos = []

    for ticker in df_user['Ticker']:
        file_path = os.path.join(CARPETA_DATOS, f"{ticker}.csv")
        if os.path.exists(file_path):
            df_ticker = pd.read_csv(file_path, parse_dates=['Date']).sort_values('Date')
            df_ticker = df_ticker.set_index('Date')
            precios[ticker] = df_ticker['Adj Close']  # usamos siempre Adjusted Close
            tickers_validos.append(ticker)
        else:
            st.warning(f"⚠️ No se encontró archivo para {ticker}, se ignorará.")

    if not precios:
        st.error("❌ No hay tickers válidos para simular.")
        st.stop()

    df_precios = pd.DataFrame(precios).sort_index()
    df_user = df_user[df_user['Ticker'].isin(tickers_validos)].reset_index(drop=True)

    # -----------------------
    # Distribución monetaria y acciones fraccionarias
    # -----------------------
    df_user['MontoAsignado'] = (df_user["% del Portafolio"] / 100) * CAPITAL_INICIAL

    fecha_inicio = df_precios.index[0]
    precios_iniciales = df_precios.loc[fecha_inicio]

    df_user['CantidadAcciones'] = df_user.apply(
        lambda row: row['MontoAsignado'] / precios_iniciales[row['Ticker']],
        axis=1
    )

    st.subheader("💵 Distribución Monetaria Inicial por Acción")
    st.dataframe(df_user)

    # -----------------------
    # Valores diarios del portafolio
    # -----------------------
    valores_diarios = df_precios * df_user.set_index("Ticker")['CantidadAcciones']
    valores_diarios['PortafolioTotal'] = valores_diarios.sum(axis=1)

    # Validación inicial
    valor_inicial = valores_diarios.iloc[0]['PortafolioTotal']
    st.write(f"💡 Capital inicial configurado: {CAPITAL_INICIAL:,.0f}")
    st.write(f"💡 Valor del portafolio en el día 1: {valor_inicial:,.0f}")

    df_valores_diarios_form = valores_diarios.copy()
    df_valores_diarios_form = df_valores_diarios_form.applymap(lambda x: f"{x:,.0f}")

    st.subheader("📊 Valores Diarios por Acción")
    st.dataframe(df_valores_diarios_form)

    # -----------------------
    # Retornos y métricas
    # -----------------------
    retornos_diarios = valores_diarios['PortafolioTotal'].pct_change().fillna(0)
    rent_anual = (1 + retornos_diarios.mean())**252 - 1
    riesgo_anual = retornos_diarios.std() * np.sqrt(252)
    sharpe = rent_anual / riesgo_anual if riesgo_anual > 0 else 0

    dias_arriba = (valores_diarios['PortafolioTotal'] > CAPITAL_INICIAL).sum()
    dias_abajo = (valores_diarios['PortafolioTotal'] <= CAPITAL_INICIAL).sum()
    ganancia_prom_arriba = valores_diarios['PortafolioTotal'][valores_diarios['PortafolioTotal'] > CAPITAL_INICIAL].mean()
    perdida_prom_abajo = valores_diarios['PortafolioTotal'][valores_diarios['PortafolioTotal'] <= CAPITAL_INICIAL].mean()
    ganancia_total = valores_diarios['PortafolioTotal'].iloc[-1] - CAPITAL_INICIAL

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

    st.subheader("📈 Resultados del Portafolio")
    resultados_formateado = resultados.copy()
    for col in resultados_formateado.columns[1:]:
        resultados_formateado[col] = resultados_formateado[col].map(lambda x: f"{x:,.2f}")
    st.dataframe(resultados_formateado)

    # -----------------------
    # Descargar CSV resultados
    # -----------------------
    st.download_button(
        "💾 Descargar resultados CSV",
        resultados.to_csv(index=False),
        file_name=f"resultados_{nombre_grupo}.csv"
    )

    st.info("Por favor descarga los resultados para subirlos en la siguiente pestaña.")
