import streamlit as st
import pandas as pd

st.set_page_config(page_title="Simulación de Resultados", layout="wide")

st.title("Resultados de la Simulación")
st.write("Cada grupo puede subir sus resultados aquí y verlos. "
         "⚠️ Sus datos se borrarán automáticamente al cerrar la pestaña o reiniciar la app.")

# -----------------------------
# Inicializar sesión
# -----------------------------
if "resultados" not in st.session_state:
    st.session_state.resultados = pd.DataFrame()

# -----------------------------
# Subida de CSV
# -----------------------------
archivo = st.file_uploader("Sube tu archivo CSV con resultados", type=["csv"])

if archivo is not None:
    df = pd.read_csv(archivo)
    
    columnas = [
        "Grupo","RentabilidadAnualizada","Riesgo","Sharpe",
        "DiasArriba","DiasAbajo","GananciaPromArriba",
        "PerdidaPromAbajo","GananciaTotal"
    ]
    
    if all(col in df.columns for col in columnas):
        st.success("✅ Archivo válido")
        st.dataframe(df)

        if st.button("Subir"):
            st.session_state.resultados = df.copy()
            st.success("Resultados guardados (solo en tu sesión).")
    else:
        st.error("❌ El CSV no tiene las columnas esperadas.")

# -----------------------------
# Mostrar resultados del usuario
# -----------------------------
if not st.session_state.resultados.empty:
    df_total = st.session_state.resultados.copy()

    st.subheader("📊 Resultados cargados")
    st.dataframe(df_total)

    st.subheader("🏆 Top 3 por Sharpe Ratio")
    top3 = df_total.sort_values("Sharpe", ascending=False).head(3)
    st.table(top3)

    st.subheader("✨ Menciones Especiales")

    mas_rentable = df_total.loc[df_total["GananciaTotal"].idxmax()]
    st.write(f"**Más rentable:** {mas_rentable['Grupo']} con {mas_rentable['GananciaTotal']:.2f}")

    mas_seguro = df_total.loc[df_total["Riesgo"].idxmin()]
    st.write(f"**Más seguro:** {mas_seguro['Grupo']} con riesgo {mas_seguro['Riesgo']:.2f}")

    mas_consistente = df_total.loc[df_total["DiasArriba"].idxmax()]
    st.write(f"**Más consistente:** {mas_consistente['Grupo']} con {mas_consistente['DiasArriba']} días arriba")

else:
    st.info("Aún no has cargado resultados.")
