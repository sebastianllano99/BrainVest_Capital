import streamlit as st
import pandas as pd
import sqlite3

st.title("Resultados de la Simulación")
st.write("Cada grupo puede subir sus resultados aquí y verlos en conjunto. "
         "✅ Los datos se guardan en una base compartida.")

# -----------------------------
# Conexión a SQLite
# -----------------------------
conn = sqlite3.connect("resultados.db", check_same_thread=False)
c = conn.cursor()

# Crear tabla si no existe
c.execute('''
CREATE TABLE IF NOT EXISTS resultados (
    Grupo TEXT,
    RentabilidadAnualizada REAL,
    Riesgo REAL,
    Sharpe REAL,
    DiasArriba INTEGER,
    DiasAbajo INTEGER,
    GananciaPromArriba REAL,
    PerdidaPromAbajo REAL,
    GananciaTotal REAL
)
''')
conn.commit()

# -----------------------------
# Subida de CSV
# -----------------------------
archivo = st.file_uploader("📂 Sube tu archivo CSV con resultados", type=["csv"])

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

        if st.button("Subir a base compartida"):
            df.to_sql("resultados", conn, if_exists="append", index=False)
            st.success("Resultados guardados en la base compartida.")
    else:
        st.error("❌ El CSV no tiene las columnas esperadas.")

# -----------------------------
# Mostrar resultados de todos
# -----------------------------
if st.button("🔄 Actualizar"):
    st.session_state["actualizar"] = True

if "actualizar" in st.session_state and st.session_state["actualizar"]:
    df_total = pd.read_sql("SELECT * FROM resultados", conn)

    if not df_total.empty:
        st.subheader("📊 Resultados de todos los grupos")
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
        st.info("Aún no hay resultados cargados.")
