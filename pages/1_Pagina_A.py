import streamlit as st
import os
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import gdown
import zipfile
from deep_translator import GoogleTranslator
import datetime
from gnews import GNews

# ==============================
# CONFIGURACIÓN DE DATOS
# ==============================
ZIP_FILE_ID = "19R9zQNq5vmNuP3l2BMvN0V7rmNvegGas"
CARPETA_DATOS = "acciones"
ZIP_NAME = "acciones.zip"

def download_and_unzip():
    """Descarga el ZIP desde Google Drive y lo descomprime en CARPETA_DATOS."""
    url = f"https://drive.google.com/uc?export=download&id={ZIP_FILE_ID}"
    st.info("Descargando base de datos desde Google Drive, por favor espera...")
    gdown.download(url, ZIP_NAME, quiet=False)
    with zipfile.ZipFile(ZIP_NAME, "r") as zf:
        zf.extractall(CARPETA_DATOS)

if not os.path.exists(CARPETA_DATOS) or len(os.listdir(CARPETA_DATOS)) == 0:
    download_and_unzip()

# Buscar CSV en la carpeta
archivos = []
for root, _, files in os.walk(CARPETA_DATOS):
    for f in files:
        if f.endswith(".csv"):
            archivos.append(os.path.join(root, f))

archivos = sorted(archivos)

if not archivos:
    st.error("No se encontraron archivos CSV en la carpeta.")
    st.stop()

# Diccionario {ticker: ruta}
tickers = {os.path.basename(f).split("_")[0]: f for f in archivos}

# ==============================
# NAVEGACIÓN
# ==============================
st.sidebar.title("📌 Navegación")
pagina = st.sidebar.radio("Selecciona una página:", ["📊 Análisis Histórico", "📰 Noticias"])

# ==============================
# PÁGINA DE ANÁLISIS HISTÓRICO
# ==============================
if pagina == "📊 Análisis Histórico":
    st.title("📊 Visualización de Históricos de Empresas")

    ticker = st.selectbox("Seleccione una empresa:", sorted(tickers.keys()))
    st.session_state["ticker"] = ticker  # guardamos selección para compartirla

    ruta = tickers[ticker]
    df = pd.read_csv(ruta)

    # Formateo
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df = df.sort_values(by="Date")

    if "Return" not in df.columns:
        df["Return"] = df["Adj Close"].pct_change() * 100
    df["Cumulative Return"] = (1 + df["Return"] / 100).cumprod() - 1

    # =======================
    # Tabla
    st.subheader(f"📑 Datos históricos - {ticker}")
    st.dataframe(df, use_container_width=True, height=400)

    # =======================
    # Estilos de gráficos
    fondo = "#0d1b2a"
    texto = "#e0e1dd"
    verde = "#00ff7f"
    azul = "#1f77b4"
    rojo = "#ff4d4d"
    naranja = "#ff6f61"

    def rango_xaxis():
        return dict(
            rangeselector=dict(
                buttons=list([
                    dict(count=1, label="1 mes", step="month", stepmode="backward"),
                    dict(count=6, label="6 meses", step="month", stepmode="backward"),
                    dict(count=1, label="1 año", step="year", stepmode="backward"),
                    dict(count=3, label="3 años", step="year", stepmode="backward"),
                    dict(step="all", label="Todo")
                ]),
                font=dict(color=texto),
                bgcolor=fondo
            ),
            rangeslider=dict(visible=True),
            tickformat="%d-%b-%Y",
            color=texto
        )

    # =======================
    # Gráfico Precio
    st.subheader("💵 Evolución del Precio Ajustado (Adj Close)")
    fig_price = px.line(
        df, x="Date", y="Adj Close",
        title=f"Evolución histórica de {ticker}",
        labels={"Date": "Fecha", "Adj Close": "Precio Ajustado"},
        template="plotly_dark"
    )
    fig_price.update_traces(line=dict(width=3, color=verde))
    fig_price.update_xaxes(**rango_xaxis())
    fig_price.update_layout(
        height=500,
        font=dict(size=15, family="Arial", color=texto),
        hovermode="x unified",
        plot_bgcolor=fondo,
        paper_bgcolor=fondo,
        title_font_color=verde
    )
    st.plotly_chart(fig_price, use_container_width=True)

    # =======================
    # Gráfico Volumen
    st.subheader("📈 Volumen de Transacciones")
    opcion_vol = st.selectbox("Frecuencia del volumen", ["Diario", "Semanal", "Mensual"])
    df_vol = df.copy()

    if opcion_vol == "Semanal":
        df_vol = df.resample("W", on="Date")["Volume"].sum().reset_index()
    elif opcion_vol == "Mensual":
        df_vol = df.resample("M", on="Date")["Volume"].sum().reset_index()

    fig_vol = px.line(
        df_vol, x="Date", y="Volume",
        title=f"Volumen de transacciones ({opcion_vol}) - {ticker}",
        labels={"Date": "Fecha", "Volume": "Acciones Negociadas"},
        template="plotly_dark"
    )
    fig_vol.update_traces(line=dict(width=2.5, color=naranja))
    fig_vol.update_xaxes(**rango_xaxis())
    fig_vol.update_layout(
        height=450,
        font=dict(size=14, family="Arial", color=texto),
        hovermode="x unified",
        plot_bgcolor=fondo,
        paper_bgcolor=fondo,
        title_font_color=naranja
    )
    st.plotly_chart(fig_vol, use_container_width=True)

    # =======================
    # Gráfico Retornos
    st.subheader("📊 Retornos de la Acción")
    opcion_ret = st.selectbox("Frecuencia de retornos", ["Diario", "Semanal", "Mensual"])
    df_ret = df.copy()

    if opcion_ret == "Semanal":
        df_ret = df.resample("W", on="Date").agg(
            {"Return": "mean", "Cumulative Return": "last"}
        ).reset_index()
    elif opcion_ret == "Mensual":
        df_ret = df.resample("M", on="Date").agg(
            {"Return": "mean", "Cumulative Return": "last"}
        ).reset_index()

    fig_ret = go.Figure()
    fig_ret.add_trace(go.Scatter(
        x=df_ret["Date"], y=df_ret["Return"],
        mode="lines", name="Retorno (%)",
        line=dict(color=verde, width=2), opacity=0.8
    ))
    fig_ret.add_trace(go.Scatter(
        x=df_ret["Date"], y=df_ret["Cumulative Return"] * 100,
        mode="lines", name="Retorno Acumulado (%)",
        line=dict(color=azul, width=3)
    ))
    fig_ret.update_xaxes(**rango_xaxis())
    fig_ret.update_layout(
        height=500,
        xaxis_title="Fecha", yaxis_title="Retorno (%)",
        template="plotly_dark",
        font=dict(size=15, family="Arial", color=texto),
        hovermode="x unified",
        plot_bgcolor=fondo,
        paper_bgcolor=fondo,
        title=f"Retornos ({opcion_ret}) - {ticker}",
        title_font_color=azul,
        legend=dict(
            orientation="h",
            yanchor="bottom", y=1.02,
            xanchor="right", x=1,
            font=dict(size=13, color=texto)
        )
    )
    st.plotly_chart(fig_ret, use_container_width=True)

# ==============================
# PÁGINA DE NOTICIAS
# ==============================
elif pagina == "📰 Noticias":
    ticker = st.sidebar.selectbox("Seleccione una empresa para ver noticias:", sorted(tickers.keys()))

    st.title(f"📰 Noticias de {ticker}")

    traducir = st.sidebar.checkbox("Traducir al español", value=True)

    # Filtros de fecha
    year = st.sidebar.number_input("Año:", min_value=2000, max_value=datetime.date.today().year, value=datetime.date.today().year)
    month = st.sidebar.number_input("Mes (1-12):", min_value=1, max_value=12, value=datetime.date.today().month)

    if st.button("🔄 Buscar noticias"):
        google_news = GNews(language="en", country="US", period="30d", max_results=10)
        try:
            noticias = google_news.get_news_by_date(
                query=ticker,
                from_date=datetime.date(year, month, 1),
                to_date=datetime.date(year, month, 28)  # hasta el 28 por seguridad
            )
        except Exception as e:
            st.error(f"Error al consultar noticias: {e}")
            noticias = []

        if not noticias:
            st.info("⚠️ No se encontraron noticias para el rango seleccionado.")
        else:
            for n in noticias[:10]:
                titulo = n["title"]
                desc = n.get("description", "Sin resumen disponible")
                fecha = n.get("published date", "Sin fecha")
                url_noticia = n.get("url", "#")

                if traducir:
                    try:
                        titulo = GoogleTranslator(source="en", target="es").translate(titulo)
                        desc = GoogleTranslator(source="en", target="es").translate(desc)
                    except Exception:
                        pass

                st.subheader(titulo)
                st.caption(f"Publicado: {fecha}")
                st.write(desc)
                st.markdown(f"[Leer más]({url_noticia})")
                st.markdown("---")
