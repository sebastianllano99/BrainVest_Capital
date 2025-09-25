import streamlit as st
import pandas as pd

st.title("Resultados de la Simulación")
st.write("Cada grupo puede subir sus resultados aquí y ver los de los demás (solo mientras la app esté abierta).")

# Inicializar almacenamiento en memoria si no existe
if "resultados" not in st.session_state:
    st.session_state.resultados = pd.DataFrame(columns=[
        "Grupo","Rentabilidad","Riesgo","Sharpe","Días Arriba","Días Abajo","Ganancia Total"
    ])

# Subir CSV
archivo = st.file_uploader("Sube tu archivo CSV con resultados", type=["csv"])

if archivo is not None:
    df = pd.read_csv(archivo)
    
    # Validar que tenga las columnas correctas
    columnas = ["Grupo","RentabilidadAnualizada","Riesgo","Sharpe",
                "DiasArriba","DiasAbajo","GananciaPromArriba",
                "PerdidaPromAbajo","GananciaTotal"]
    
    if all(col in df.columns for col in columnas):
        st.success("Archivo válido ✅")
        st.dataframe(df)

        if st.button(" Subir"):
            for _, row in df.iterrows():
                # Reemplazar si ya existe el grupo
                st.session_state.resultados = st.session_state.resultados[
                    st.session_state.resultados["Grupo"] != row["Grupo"]
                ]

                st.session_state.resultados = pd.concat([
                    st.session_state.resultados,
                    pd.DataFrame([{
                        "Grupo": row["Grupo"],
                        "Rentabilidad": row["RentabilidadAnualizada"],
                        "Riesgo": row["Riesgo"],
                        "Sharpe": row["Sharpe"],
                        "Días Arriba": row["DiasArriba"],
                        "Días Abajo": row["DiasAbajo"],
                        "Ganancia Total": row["GananciaTotal"]
                    }])
                ], ignore_index=True)

            st.success("Resultados guardados correctamente ✅")

    else:
        st.error("❌ El CSV no tiene las columnas esperadas.")

# Botón refrescar para ver todos los resultados
if st.button(" Actualizar"):
    if not st.session_state.resultados.empty:
        df_total = st.session_state.resultados.copy()
        st.dataframe(df_total)

        # Podio oficial por Sharpe
        st.subheader("🏆 Top 3 por Sharpe Ratio")
        top3 = df_total.sort_values("Sharpe", ascending=False).head(3)
        st.table(top3)

        # 🔹 Menciones especiales
        st.subheader("✨ Menciones Especiales")

        # Más rentable (mayor ganancia total)
        mas_rentable = df_total.loc[df_total["Ganancia Total"].idxmax()]
        st.write(f" **Más rentable:** {mas_rentable['Grupo']} con {mas_rentable['Ganancia Total']:.2f}")

        # Más seguro (menor riesgo)
        mas_seguro = df_total.loc[df_total["Riesgo"].idxmin()]
        st.write(f" **Más seguro:** {mas_seguro['Grupo']} con riesgo {mas_seguro['Riesgo']:.2f}")

        # Más consistente (más días arriba)
        mas_consistente = df_total.loc[df_total["Días Arriba"].idxmax()]
        st.write(f" **Más consistente:** {mas_consistente['Grupo']} con {mas_consistente['Días Arriba']} días arriba")

    else:
        st.info("Aún no hay resultados cargados.")
