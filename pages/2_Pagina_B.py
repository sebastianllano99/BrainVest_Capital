import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

def mi_portafolio():
    st.title("📊 Mi Portafolio de Inversión")

    # Dinero inicial para invertir
    monto_total = st.number_input("Monto inicial a invertir (USD)", min_value=1000, value=10000, step=500)

    st.info("""
    **Instrucciones**  
    1. Descargue o prepare un archivo CSV con dos columnas:  
       - `Empresa`: Nombre o ticker de la acción.  
       - `Porcentaje`: Porcentaje de inversión destinado a esa acción.  
    2. Asegúrese de que la suma de porcentajes sea igual a 100.  
    3. Suba el archivo CSV en el recuadro de abajo.
    """)

    # Subida del archivo CSV
    archivo_csv = st.file_uploader("📂 Suba su archivo CSV con la distribución del portafolio", type=["csv"])

    if archivo_csv is not None:
        try:
            df = pd.read_csv(archivo_csv)

            # Validación de columnas
            if "Empresa" not in df.columns or "Porcentaje" not in df.columns:
                st.error("❌ El archivo CSV debe contener las columnas: Empresa y Porcentaje.")
                return

            # Validación de porcentajes
            total_pct = df["Porcentaje"].sum()
            if total_pct != 100:
                st.error(f"❌ Los porcentajes deben sumar 100. Actualmente suman {total_pct}%.")
                return

            # Cálculo de montos por empresa
            df["Monto Invertido (USD)"] = (df["Porcentaje"] / 100) * monto_total

            st.success("✅ Portafolio cargado correctamente.")
            st.write("### Distribución del Portafolio")
            st.dataframe(df, use_container_width=True)

            # Gráfico de torta
            fig, ax = plt.subplots()
            ax.pie(df["Porcentaje"], labels=df["Empresa"], autopct='%1.1f%%', startangle=90)
            ax.axis("equal")  # Hacer el gráfico circular
            st.pyplot(fig)

        except Exception as e:
            st.error(f"⚠️ Error al procesar el archivo: {e}")
