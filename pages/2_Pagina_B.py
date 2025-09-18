import os
import streamlit as st
import pandas as pd
import plotly.express as px
import io

# -------------------------
# Config
# -------------------------
CAPITAL_TOTAL = 500_000_000  # 500 millones COP (fijo)

DATA_FOLDER = "acciones"  # carpeta donde están los CSV de Yahoo (igual que en Página A)

# -------------------------
# Interfaz
# -------------------------
st.title("📊 Mi Portafolio de Inversión")
st.info(f"💰 El monto total disponible para invertir es **${CAPITAL_TOTAL:,.0f} COP** (fijo).")

st.warning(
    """
🔔 **Recuerda**:
- El CSV debe contener **dos columnas**: `Ticker` y `Porcentaje` (el nombre puede estar en mayúsculas o minúsculas).
- `Ticker` debe coincidir exactamente con los nombres de archivo que tengas en la carpeta `acciones/` (ej. `AAPL.csv` → ticker `AAPL`).
- La suma de `Porcentaje` debe ser **100** (puedes usar decimales).
"""
)

# -------------------------
# Detectar tickers disponibles (valida contra la carpeta 'acciones')
# -------------------------
available_tickers = set()
if os.path.isdir(DATA_FOLDER):
    for root, _, files in os.walk(DATA_FOLDER):
        for f in files:
            if f.lower().endswith(".csv"):
                available_tickers.add(os.path.splitext(os.path.basename(f))[0])
else:
    # Si no existe la carpeta, solo avisamos; el check de existencia de tickers se omitirá.
    st.info(f"Nota: la carpeta `{DATA_FOLDER}` no se encontró. La validación automática de tickers será omitida.")

# -------------------------
# Botón para descargar CSV ejemplo
# -------------------------
# si hay tickers en la carpeta, usamos algunos como ejemplo; si no, usamos tickers genéricos
if available_tickers:
    sample_tickers = list(available_tickers)[:4]
else:
    sample_tickers = ["AAPL", "MSFT", "GOOG", "AMZN"]

sample_df = pd.DataFrame({"Ticker": sample_tickers, "Porcentaje": [40, 30, 20, 10]})
csv_bytes = sample_df.to_csv(index=False).encode("utf-8")
st.download_button(
    label="⬇️ Descargar CSV de ejemplo",
    data=csv_bytes,
    file_name="ejemplo_portafolio.csv",
    mime="text/csv",
)

st.markdown("---")

# -------------------------
# Subida del CSV
# -------------------------
uploaded = st.file_uploader("📂 Sube tu archivo CSV (Ticker, Porcentaje)", type=["csv"])

if uploaded is not None:
    try:
        # leer CSV
        df = pd.read_csv(uploaded)

        # normalizar nombres de columnas (insensible a mayúsculas)
        cols_map = {c.lower().strip(): c for c in df.columns}
        if "ticker" not in cols_map or "porcentaje" not in cols_map:
            st.error("❌ El CSV debe contener las columnas `Ticker` y `Porcentaje` (pueden estar en cualquier mayúscula/minúscula).")
        else:
            # renombrar a columnas estándar
            df = df.rename(columns={cols_map["ticker"]: "Ticker", cols_map["porcentaje"]: "Porcentaje"})

            # limpieza y tipos
            df["Ticker"] = df["Ticker"].astype(str).str.strip()
            df["Porcentaje"] = pd.to_numeric(df["Porcentaje"], errors="coerce")

            if df["Porcentaje"].isnull().any():
                st.error("❌ Hay valores no numéricos en la columna `Porcentaje`. Corrige el CSV.")
            else:
                suma_pct = df["Porcentaje"].sum()

                # permitir pequeña tolerancia (ej: 0.01)
                if abs(suma_pct - 100) > 0.01:
                    st.error(f"❌ Los porcentajes deben sumar 100. Actualmente suman {suma_pct:.6f}.")
                else:
                    # Validar que los tickers existan en la carpeta (si la carpeta existe)
                    if available_tickers:
                        missing = [t for t in df["Ticker"] if t not in available_tickers]
                        if missing:
                            st.error(
                                "❌ Algunos tickers del CSV no se encontraron en la carpeta 'acciones':\n\n"
                                + ", ".join(missing)
                                + "\n\nCorrige los tickers o agrega los archivos correspondientes a 'acciones/'."
                            )
                            st.stop()

                    # calcular montos
                    df["Inversion (COP)"] = (df["Porcentaje"] / 100.0 * CAPITAL_TOTAL).round(0).astype(int)

                    # guardar solo en sesión (no persistente)
                    st.session_state["portafolio"] = df.copy()

                    # mostrar resultados
                    st.subheader("📋 Distribución del Portafolio")
                    st.dataframe(df, use_container_width=True)

                    total_invertido = int(df["Inversion (COP)"].sum())
                    st.success(f"✅ Portafolio válido. Total invertido: {total_invertido:,.0f} COP (de {CAPITAL_TOTAL:,.0f} COP)")

                    # gráfico torta con plotly
                    fig = px.pie(df, names="Ticker", values="Porcentaje",
                                 title="Distribución del Portafolio (%)",
                                 template="plotly_dark", hole=0.3)
                    fig.update_traces(textinfo="percent+label")
                    st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        st.error(f"⚠️ Error al procesar el archivo: {e}")
else:
    st.info("📥 Sube un CSV para ver la distribución. Puedes descargar el ejemplo arriba.")
