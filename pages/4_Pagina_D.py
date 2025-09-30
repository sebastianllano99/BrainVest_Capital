import streamlit as st
import pandas as pd
import sqlite3

# st.set_page_config(page_title="Resultados de la Simulación", layout="wide")

st.title("📊 Resultados de la Simulación")
st.write(
    "Cada grupo puede subir sus resultados aquí y verlos en el tablero compartido. "
    "⚠️ Los datos se eliminarán cuando el administrador use la opción de borrar."
)

# -----------------------------
# Configuración base de datos
# -----------------------------
DB_FILE = "resultados.db"
conn = sqlite3.connect(DB_FILE, check_same_thread=False)
c = conn.cursor()

# Crear tabla con las 10 columnas (forzando estructura correcta)
c.execute("""
CREATE TABLE IF NOT EXISTS resultados (
    Grupo TEXT,
    RentabilidadAnualizada REAL,
    Riesgo REAL,
    Sharpe REAL,
    DiasArriba INTEGER,
    DiasAbajo INTEGER,
    GananciaPromArriba REAL,
    PerdidaPromAbajo REAL,
    GananciaTotal REAL,
    CapitalSobrante REAL
)
""")
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
        "PerdidaPromAbajo","GananciaTotal","CapitalSobrante"
    ]

    if all(col in df.columns for col in columnas):
        st.success("✅ Archivo válido")
        st.dataframe(df)

        if st.button("⬆️ Subir al tablero"):
            try:
                df[columnas].to_sql("resultados", conn, if_exists="append", index=False)
                st.success("Resultados agregados al tablero compartido.")
            except Exception as e:
                st.error(f"❌ Error al guardar en la base de datos: {e}")
    else:
        st.error("❌ El CSV no tiene las columnas esperadas.")

# -----------------------------
# Botón para actualizar
# -----------------------------
if st.button("🔄 Actualizar tablero"):
    st.rerun()

# -----------------------------
# Mostrar resultados acumulados
# -----------------------------
df_total = pd.read_sql("SELECT * FROM resultados", conn)

if not df_total.empty:
    st.subheader("📊 Resultados acumulados")
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

    menor_sobrante = df_total.loc[df_total["CapitalSobrante"].idxmin()]
    st.write(f"**Menor capital sobrante:** {menor_sobrante['Grupo']} con sobrante {menor_sobrante['CapitalSobrante']:.2f}")
else:
    st.info("Aún no se han cargado resultados.")

# -----------------------------
# Borrar con contraseña
# -----------------------------
st.subheader("🗑️ Administración")

password = st.text_input("Ingrese contraseña para borrar todos los resultados", type="password")

if st.button("Borrar todo"):
    if password == "4539":
        c.execute("DELETE FROM resultados")
        conn.commit()
        st.warning("✅ Todos los resultados han sido eliminados.")
    else:
        st.error("❌ Contraseña incorrecta. No se borraron los datos.")
