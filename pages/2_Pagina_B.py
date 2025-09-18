import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

# --- CONFIGURACIÓN INICIAL ---
#st.set_page_config(page_title="Mi Portafolio", layout="wide")

# --- CAPITAL DISPONIBLE ---
CAPITAL_TOTAL = 500_000_000  # 500 millones COP (fijo)

# --- TÍTULO ---
st.title("📊 Mi Portafolio de Inversión")

# --- INSTRUCCIONES ---
st.info(
    """
    Recuerda que el archivo **CSV** debe estar organizado con las siguientes columnas:
    - **Accion** → Nombre de la acción.  
    - **Ticker** → Símbolo bursátil de la acción.  
    - **Porcentaje** → Porcentaje de inversión en esa acción (ejemplo: 25 para 25%).  

    El total de los porcentajes debe sumar **100%**, ya que se invierten exactamente **500 millones de COP**.
    """
)

# --- SUBIDA DE ARCHIVO ---
archivo = st.file_uploader("📂 Sube tu archivo CSV de portafolio", type=["csv"])

if archivo is not None:
    try:
        # Leer CSV
        df = pd.read_csv(archivo)

        # Validar columnas
        columnas_esperadas = {"Accion", "Ticker", "Porcentaje"}
        if not columnas_esperadas.issubset(df.columns):
            st.error("❌ El CSV no tiene las columnas correctas. Debe contener: Accion, Ticker, Porcentaje.")
        else:
            # Calcular inversión por acción
            df["Porcentaje"] = df["Porcentaje"].astype(float)
            suma_porcentajes = df["Porcentaje"].sum()

            if suma_porcentajes != 100:
                st.error(f"⚠️ Los porcentajes deben sumar **100%**. Actualmente suman {suma_porcentajes:.2f}%.")
            else:
                df["Inversion (COP)"] = (df["Porcentaje"] / 100) * CAPITAL_TOTAL

                # Mostrar tabla
                st.subheader("📋 Detalle del Portafolio")
                st.dataframe(df, use_container_width=True)

                # Mostrar total invertido
                total_invertido = df["Inversion (COP)"].sum()
                st.success(f"✅ Portafolio válido. Total invertido: {total_invertido:,.0f} COP de {CAPITAL_TOTAL:,.0f} COP")

                # --- GRÁFICO DE TORTA ---
                fig, ax = plt.subplots()
                ax.pie(df["Porcentaje"], labels=df["Ticker"], autopct="%1.1f%%", startangle=90)
                ax.set_title("Distribución del Portafolio (%)")
                st.pyplot(fig)

    except Exception as e:
        st.error(f"Error al procesar el archivo: {e}")
else:
    st.warning("☝️ Por favor, sube un archivo CSV para continuar.")

