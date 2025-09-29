import streamlit as st
import pandas as pd
import sqlite3
import uuid
import datetime


st.title("Resultados de la Simulación (compartidos)")
st.write("Sube tu CSV y todos los usuarios verán los resultados en conjunto. Usa `Actualizar` para recargar nuevos envíos.")

# --------------------------
# Identificador único por sesión (para poder borrar solo tus filas)
# --------------------------
if "uploader_id" not in st.session_state:
    st.session_state.uploader_id = str(uuid.uuid4())

# --------------------------
# Conexión a SQLite en disco (archivo compartido en el servidor)
# --------------------------
DB_PATH = "resultados.db"  # archivo en el servidor; si prefieres que desaparezca con reinicio del servidor, borralo al reiniciar
conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=30)
c = conn.cursor()

# Crear tabla con columnas extra para seguimiento
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
    GananciaTotal REAL,
    uploader_id TEXT,
    uploaded_at TEXT
)
''')
conn.commit()

# --------------------------
# Panel lateral: opciones de limpieza y expiración
# --------------------------
st.sidebar.header("Opciones de convivencia")
expiry_enabled = st.sidebar.checkbox("Auto-expirar resultados (activar)", value=True)
expiry_minutes = st.sidebar.number_input("Expirar tras (minutos)", min_value=1, value=60, step=1)

st.sidebar.markdown("---")
if st.sidebar.button("Eliminar mis resultados (solo los míos)"):
    c.execute("DELETE FROM resultados WHERE uploader_id = ?", (st.session_state.uploader_id,))
    conn.commit()
    st.sidebar.success("Tus resultados han sido eliminados.")

# Confirmación para limpiar todo
if "confirm_clear" not in st.session_state:
    st.session_state.confirm_clear = False

if st.sidebar.button("🧹 Limpiar todo (vaciar tabla)"):
    st.session_state.confirm_clear = True

if st.session_state.confirm_clear:
    if st.sidebar.button("Confirmar: Vaciar toda la tabla"):
        c.execute("DELETE FROM resultados")
        conn.commit()
        st.sidebar.success("Tabla vaciada.")
        st.session_state.confirm_clear = False
    if st.sidebar.button("Cancelar"):
        st.session_state.confirm_clear = False

st.sidebar.markdown("---")
st.sidebar.write("ID de esta sesión (para depuración):")
st.sidebar.code(st.session_state.uploader_id)

# --------------------------
# Subida de CSV
# --------------------------
archivo = st.file_uploader("📂 Sube tu archivo CSV con resultados", type=["csv"])

expected_cols = [
    "Grupo","RentabilidadAnualizada","Riesgo","Sharpe",
    "DiasArriba","DiasAbajo","GananciaPromArriba",
    "PerdidaPromAbajo","GananciaTotal"
]

if archivo is not None:
    try:
        df = pd.read_csv(archivo)
    except Exception as e:
        st.error(f"Error leyendo CSV: {e}")
        df = None

    if df is not None:
        if all(col in df.columns for col in expected_cols):
            st.success("✅ Archivo válido")
            st.dataframe(df)
            if st.button("Subir a la base compartida"):
                # añadir metadatos
                df_to_store = df[expected_cols].copy()
                df_to_store["uploader_id"] = st.session_state.uploader_id
                df_to_store["uploaded_at"] = datetime.datetime.utcnow().isoformat()
                # append a la tabla
                df_to_store.to_sql("resultados", conn, if_exists="append", index=False)
                conn.commit()
                st.success("Resultados subidos correctamente.")
        else:
            st.error("❌ El CSV no contiene las columnas esperadas. Columnas esperadas:")
            st.write(expected_cols)

# --------------------------
# Función para limpiar expirados
# --------------------------
def limpiar_expirados():
    if expiry_enabled:
        cutoff = (datetime.datetime.utcnow() - datetime.timedelta(minutes=expiry_minutes)).isoformat()
        c.execute("DELETE FROM resultados WHERE uploaded_at < ?", (cutoff,))
        conn.commit()

# --------------------------
# Botón actualizar (recarga desde DB)
# --------------------------
if st.button("🔄 Actualizar"):
    limpiar_expirados()
    st.session_state["reloaded_at"] = datetime.datetime.utcnow().isoformat()
    st.success("Datos recargados.")

# Carga inicial / siempre muestra la vista actualizada si no hay estado previo
df_total = pd.read_sql("SELECT * FROM resultados ORDER BY uploaded_at DESC", conn)

if df_total.empty:
    st.info("Aún no hay resultados cargados.")
else:
    st.subheader("📊 Resultados de todos los grupos")
    st.dataframe(df_total)

    st.subheader("🏆 Top 3 por Sharpe Ratio")
    try:
        top3 = df_total.sort_values("Sharpe", ascending=False).head(3)
        st.table(top3)
    except Exception as e:
        st.error(f"No se puede calcular Top 3: {e}")

    st.subheader("✨ Menciones Especiales")
    try:
        mas_rentable = df_total.loc[df_total["GananciaTotal"].astype(float).idxmax()]
        st.write(f"**Más rentable:** {mas_rentable['Grupo']} con {float(mas_rentable['GananciaTotal']):.2f}")
    except Exception:
        st.write("**Más rentable:** no disponible")

    try:
        mas_seguro = df_total.loc[df_total["Riesgo"].astype(float).idxmin()]
        st.write(f"**Más seguro:** {mas_seguro['Grupo']} con riesgo {float(mas_seguro['Riesgo']):.2f}")
    except Exception:
        st.write("**Más seguro:** no disponible")

    try:
        mas_consistente = df_total.loc[df_total["DiasArriba"].astype(int).idxmax()]
        st.write(f"**Más consistente:** {mas_consistente['Grupo']} con {int(mas_consistente['DiasArriba'])} días arriba")
    except Exception:
        st.write("**Más consistente:** no disponible")
