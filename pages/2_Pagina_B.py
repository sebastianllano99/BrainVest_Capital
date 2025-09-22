import streamlit as st
import pandas as pd

# ================================
# CONFIGURACIÓN DE LA PÁGINA
# ================================
st.set_page_config(page_title="Simulación de Portafolio", layout="centered")

st.title("📊 Simulación de Portafolio")
st.write("""
Sube un CSV con columnas Ticker y % del Portafolio.  
Al cargar el archivo podrás *Iniciar Simulación, luego ver **Resultados*  
y finalmente *Finalizar / Guardar*.
""")

# ================================
# BOTÓN PARA DESCARGAR EJEMPLO
# ================================
ejemplo = pd.DataFrame({
    "Ticker": ["AAPL", "MSFT", "GOOGL"],
    "% del Portafolio": [40, 30, 30]
})

st.download_button(
    label="📂 Descargar ejemplo CSV",
    data=ejemplo.to_csv(index=False),
    file_name="ejemplo_portafolio.csv",
    mime="text/csv"
)

# ================================
# SUBIDA DE CSV
# ================================
uploaded = st.file_uploader("Sube tu CSV (Ticker, % del Portafolio)", type=["csv"])
df_user = None

if uploaded:
    try:
        df_user = pd.read_csv(uploaded)
        st.success("✅ CSV cargado correctamente")
        st.dataframe(df_user)
    except Exception as e:
        st.error(f"❌ Error leyendo tu CSV: {e}")
        st.stop()

# ================================
# FLUJO DE BOTONES
# ================================
if df_user is not None:
    if st.button("🚀 Iniciar Simulación"):
        st.info("🔄 Simulación en proceso (placeholder)...")
        
        if st.button("📊 Ver Resultados"):
            st.success("Aquí se mostrarán los resultados de la simulación (placeholder).")
            
            if st.button("💾 Finalizar y Guardar"):
                st.success("✅ Resultados guardados (placeholder).")
