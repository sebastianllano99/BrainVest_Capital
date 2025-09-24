import streamlit as st
import pandas as pd
import numpy as np
import os
import zipfile
import gdown
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive

# -----------------------
# Configuración
# -----------------------
CAPITAL_INICIAL = 200_000_000
ZIP_URL = "https://drive.google.com/uc?id=1sgshq-1MLrO1oToV8uu-iM4SPnvgT149"
ZIP_NAME = "acciones_2024.zip"
CARPETA_DATOS = "Acciones_2024"

# Aquí colocas el ID de la carpeta que me enviaste
CARPETA_RESULTADOS_ID = "1okVq5b56rxJeOBHlxNr84ULX1xHf7tdD"  
CCV_NAME = "CCV_resultados.csv"

# -----------------------
# Funciones para Drive
# -----------------------
@st.cache_resource
def autenticar_drive():
    gauth = GoogleAuth()
    gauth.LocalWebserverAuth()  # Esto abrirá una ventana para autenticar la primera vez
    return GoogleDrive(gauth)

def buscar_archivo(drive, nombre, carpeta_id):
    """Devuelve el archivo existente en la carpeta de Drive si existe."""
    query = f"'{carpeta_id}' in parents and trashed=false and title='{nombre}'"
    archivos = drive.ListFile({'q': query}).GetList()
    return archivos[0] if archivos else None

def subir_resultados_a_drive(resultados, drive, carpeta_id, nombre_archivo):
    """Sube los resultados al archivo maestro en Drive, creándolo si es necesario, o anexando la fila nueva."""
    archivo = buscar_archivo(drive, nombre_archivo, carpeta_id)
    if archivo:
        # Descargar versión actual
        archivo.GetContentFile("temp_ccv.csv")
        ccv = pd.read_csv("temp_ccv.csv")
        # Verificar que no haya ya una fila con el mismo grupo (opcional)
        # Aquí se añade la nueva fila
        ccv = pd.concat([ccv, resultados], ignore_index=True)
    else:
        ccv = resultados

    # Guardar el CSV actualizado localmente
    ccv.to_csv("temp_ccv.csv", index=False)

    if archivo:
        archivo.SetContentFile("temp_ccv.csv")
        archivo.Upload()
    else:
        nuevo = drive.CreateFile({
            "title": nombre_archivo,
            "parents": [{"id": carpeta_id}]
        })
        nuevo.SetContentFile("temp_ccv.csv")
        nuevo.Upload()

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

nombre_grupo = st.text_input("✍️ Ingresa el nombre de tu grupo")

if uploaded:
    try:
        df_user = pd.read_csv(uploaded)
        st.success("✅ CSV cargado correctamente")
        st.dataframe(df_user)
    except Exception as e:
        st.error(f"❌ Error leyendo tu CSV: {e}")

# -----------------------
# Botón para finalizar simulación y enviar resultados
# -----------------------
if st.button("🚀 Finalizar Simulación") and df_user is not None and nombre_grupo.strip() != "":

    st.info("Simulación en ejecución...")

    # Paso 1: Descargar ZIP de acciones si no existe
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
        df_precios = pd.DataFrame(precios)
        df_user = df_user[df_user['Ticker'].isin(tickers_validos)].reset_index(drop=True)

        df_user['Monto Invertido'] = (df_user["% del Portafolio"] / 100) * CAPITAL_INICIAL
        df_user['Cantidad Acciones'] = df_user.apply(
            lambda row: row['Monto Invertido'] / primer_dia_precios[row['Ticker']], axis=1
        )

        valores_diarios = df_precios * df_user['Cantidad Acciones'].values
        df_portafolio = valores_diarios.sum(axis=1)

        retornos_diarios = df_portafolio.pct_change().fillna(0)
        rent_anual = (1 + retornos_diarios.mean())**252 - 1
        riesgo_anual = retornos_diarios.std() * np.sqrt(252)
        sharpe = rent_anual / riesgo_anual if riesgo_anual > 0 else 0

        dias_arriba = (df_portafolio > CAPITAL_INICIAL).sum()
        dias_abajo = (df_portafolio <= CAPITAL_INICIAL).sum()

        resultados = pd.DataFrame({
            "Grupo": [nombre_grupo],
            "Rentabilidad Anualizada": [rent_anual],
            "Riesgo": [riesgo_anual],
            "Sharpe": [sharpe],
            "Días Arriba": [dias_arriba],
            "Días Abajo": [dias_abajo]
        })

        st.subheader("📈 Resultados del Portafolio")
        st.dataframe(resultados)

        # Autenticación con Drive
        drive = autenticar_drive()
        subir_resultados_a_drive(resultados, drive, CARPETA_RESULTADOS_ID, CCV_NAME)

        st.success("✅ Resultados enviados al archivo global en Drive")
