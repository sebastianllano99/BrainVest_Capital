import streamlit as st
import pandas as pd
import plotly.express as px

# ==============================
# PÁGINA MI PORTAFOLIO
# ==============================
st.title("💼 Mi Portafolio de Inversión")

# Dinero inicial
monto_total = st.number_input("Monto inicial a invertir (USD)", min_value=1000, value=10000, step=500)

st.info("""
**Instrucciones**
1. Prepare un archivo CSV con dos columnas:
   - `Empresa`: Nombre o ticker de la acción.
   - `Porcentaje`: Porcentaje de inversión (debe sumar 100).
2. Suba el archivo en el recuadro de abajo.
""")

# Subida del archivo
archivo_csv = st.file_uploader("📂 Suba su archivo CSV", type=["csv"])

if archivo_csv is not None:
    try:
        df = pd.read_csv(archivo_csv)

        # Validación de columnas
        if "Empresa" not in df.columns or "Porcentaje" not in df.columns:
            st.error("❌ El archivo CSV debe tener las columnas: Empresa y Porcentaje.")
        else:
            # Validación de porcentajes
            total_pct = df["Porcentaje"].sum()
            if total_pct != 100:
                st.error(f"❌ Los porcentajes deben sumar 100. Actualmente suman {total_pct}%.")
            else:
                # Cálculo de montos
                df["Monto Invertido (USD)"] = (df["Porcentaje"] / 100) * monto_total

                st.success("✅ Portafolio cargado correctamente.")
                st.subheader("📑 Distribución del Portafolio")
                st.dataframe(df, use_container_width=True, height=400)

                # Gráfico de torta con Plotly
                fig = px.pie(df, values="Porcentaje", names="Empresa",
                             title="Distribución del Portafolio (%)",
                             template="plotly_dark", hole=0.3)
                fig.update_traces(textinfo="percent+label")
                st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        st.error(f"⚠️ Error al procesar el archivo: {e}")
