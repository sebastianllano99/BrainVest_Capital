import streamlit as st
import pandas as pd
import sqlite3

st.title("📊 Resultados de la Simulación")

st.write(
    "Cada grupo puede subir sus resultados aquí y verlos en el tablero compartido. "
    "Los datos se eliminarán cuando el administrador use la opción de borrar."
)

# -----------------------------
# Configuración base de datos
# -----------------------------
DB_FILE = "resultados.db"
conn = sqlite3.connect(DB_FILE, check_same_thread=False)
c = conn.cursor()

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
archivo = st.file_uploader(" Sube tu archivo CSV con resultados", type=["csv"])

columnas = [
    "Grupo","RentabilidadAnualizada","Riesgo","Sharpe",
    "DiasArriba","DiasAbajo","GananciaPromArriba",
    "PerdidaPromAbajo","GananciaTotal","CapitalSobrante"
]

if archivo is not None:
    df = pd.read_csv(archivo)

    if all(col in df.columns for col in columnas):
        st.success("Archivo válido")
        st.dataframe(df)

        grupo = df["Grupo"].iloc[0]  # Nombre del grupo del archivo

        # Validar si ya existe registro para este grupo
        c.execute("SELECT COUNT(*) FROM resultados WHERE Grupo = ?", (grupo,))
        existe = c.fetchone()[0]

        if existe > 0:
            st.warning(f"⚠️ El grupo **{grupo}** ya subió un archivo. "
                       f"Debe eliminarlo primero antes de subir uno nuevo.")
        else:
            if st.button("Subir al tablero"):
                df[columnas].to_sql("resultados", conn, if_exists="append", index=False)
                st.success("Resultados agregados al tablero compartido.")
    else:
        st.error(" El CSV no tiene las columnas esperadas.")

# -----------------------------
# Botón para actualizar
# -----------------------------
if st.button(" Actualizar tablero"):
    st.rerun()

# -----------------------------
# Mostrar resultados acumulados
# -----------------------------
df_total = pd.read_sql("SELECT * FROM resultados", conn)

# Función para formatear valores monetarios con separadores
def formato_monetario(valor):
    return "${:,.2f}".format(valor)

if not df_total.empty:
    st.subheader("Resultados acumulados")
    st.dataframe(df_total)

    st.subheader("🏆 Top 3 por Sharpe Ratio")
    top3 = df_total.sort_values("Sharpe", ascending=False).head(3)
    st.table(top3)

    st.subheader("✨ Menciones Especiales")
    mas_rentable = df_total.loc[df_total["GananciaTotal"].idxmax()]
    st.write(f"**Más rentable:** {mas_rentable['Grupo']} con {formato_monetario(mas_rentable['GananciaTotal'])}")

    mas_seguro = df_total.loc[df_total["Riesgo"].idxmin()]
    st.write(f"**Más seguro:** {mas_seguro['Grupo']} con riesgo {mas_seguro['Riesgo']:.2f}")

    mas_consistente = df_total.loc[df_total["DiasArriba"].idxmax()]
    st.write(f"**Más consistente:** {mas_consistente['Grupo']} con {mas_consistente['DiasArriba']} días arriba")

    menor_sobrante = df_total.loc[df_total["CapitalSobrante"].idxmin()]
    st.write(f"**Menor capital sobrante:** {menor_sobrante['Grupo']} con {formato_monetario(menor_sobrante['CapitalSobrante'])}")

else:
    st.info("Aún no se han cargado resultados.")

# -----------------------------
# Borrar con contraseña
# -----------------------------
st.subheader("Administración")

# Contraseña completamente oculta
password = st.text_input("Ingrese contraseña para borrar todos los resultados", type="password", help="La contraseña no será visible al escribirla.")

if st.button("Borrar todo"):
    if password == "4825":
        c.execute("DELETE FROM resultados")
        conn.commit()
        st.warning("Todos los resultados han sido eliminados.")
    else:
        st.error("Contraseña incorrecta. No se borraron los datos.")
