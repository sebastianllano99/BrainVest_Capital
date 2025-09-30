# pagina_resultados_db_fix.py
import streamlit as st
import pandas as pd
import sqlite3
import os

st.title("📊 Resultados de la Simulación (robusto contra esquemas)")

# -----------------------------
# Configuración
# -----------------------------
DB_FILE = "resultados.db"
conn = sqlite3.connect(DB_FILE, check_same_thread=False)
c = conn.cursor()

# columnas esperadas y tipos
COLUMNS = [
    "Grupo","RentabilidadAnualizada","Riesgo","Sharpe",
    "DiasArriba","DiasAbajo","GananciaPromArriba",
    "PerdidaPromAbajo","GananciaTotal","CapitalSobrante"
]
COL_TYPES = {
    "Grupo": "TEXT",
    "RentabilidadAnualizada": "REAL",
    "Riesgo": "REAL",
    "Sharpe": "REAL",
    "DiasArriba": "INTEGER",
    "DiasAbajo": "INTEGER",
    "GananciaPromArriba": "REAL",
    "PerdidaPromAbajo": "REAL",
    "GananciaTotal": "REAL",
    "CapitalSobrante": "REAL"
}

# -----------------------------
# Funciones utilitarias DB
# -----------------------------
def table_exists(conn, name="resultados"):
    cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (name,))
    return cur.fetchone() is not None

def get_table_columns(conn, name="resultados"):
    if not table_exists(conn, name):
        return []
    cur = conn.execute(f"PRAGMA table_info({name})")
    return [row[1] for row in cur.fetchall()]

def create_table(conn, name="resultados"):
    cols_def = ",\n".join([f"{col} {COL_TYPES[col]}" for col in COLUMNS])
    conn.execute(f"CREATE TABLE IF NOT EXISTS {name} ({cols_def})")
    conn.commit()

def add_missing_columns(conn, missing, name="resultados"):
    for col in missing:
        try:
            conn.execute(f"ALTER TABLE {name} ADD COLUMN {col} {COL_TYPES[col]}")
            conn.commit()
        except Exception as e:
            # si falla, relanzamos la excepción para manejarla fuera
            raise RuntimeError(f"No se pudo añadir la columna '{col}': {e}")

# Asegurar tabla base: si no existe, crearla
create_table(conn, "resultados")

# Si existe pero faltan columnas, intentar añadirlas
existing_cols = get_table_columns(conn, "resultados")
missing_cols = [c for c in COLUMNS if c not in existing_cols]
if missing_cols:
    try:
        add_missing_columns(conn, missing_cols, "resultados")
        st.info(f"Se añadieron automáticamente las columnas faltantes: {missing_cols}")
    except Exception as e:
        st.error(f"No fue posible añadir automáticamente estas columnas: {missing_cols}.")
        st.write("Error:", e)
        st.warning("Puedes recrear la tabla (borrará TODOS los datos) con el botón abajo si estás de acuerdo.")

# Botón para recrear la tabla de cero (opcional)
if st.button("⚠️ Recrear tabla resultados (BORRAR TODO)"):
    c.execute("DROP TABLE IF EXISTS resultados")
    conn.commit()
    create_table(conn, "resultados")
    st.success("Tabla 'resultados' recreada con la estructura correcta (datos anteriores eliminados).")

# -----------------------------
# Subida de CSV (robusta)
# -----------------------------
archivo = st.file_uploader("📂 Sube tu archivo CSV con resultados", type=["csv"])

def normalize_column_name(s: str) -> str:
    # limpia BOM y espacios
    return s.replace("\ufeff", "").strip()

def find_matching_column(expected, df_columns):
    # intenta encontrar la mejor coincidencia insensible a mayúsculas/espacios/underscores
    exp_norm = expected.strip().lower().replace(" ", "").replace("_", "")
    for col in df_columns:
        col_norm = normalize_column_name(col).lower().replace(" ", "").replace("_", "")
        if col_norm == exp_norm:
            return col
    # fallback: match case-insensitive exact strip
    for col in df_columns:
        if normalize_column_name(col).strip().lower() == expected.strip().lower():
            return col
    return None

if archivo is not None:
    df_raw = pd.read_csv(archivo)
    # limpiar nombres de columnas leídos
    df_raw.columns = [normalize_column_name(c) for c in df_raw.columns]

    # construir df_ready con las columnas en el orden esperado
    df_ready = pd.DataFrame()
    missing_in_csv = []
    for col in COLUMNS:
        match = find_matching_column(col, df_raw.columns)
        if match:
            df_ready[col] = df_raw[match]
        else:
            missing_in_csv.append(col)
            # rellenar con defaults (0 o "")
            if COL_TYPES[col].upper().startswith("INT") or COL_TYPES[col].upper() == "REAL":
                df_ready[col] = 0
            else:
                df_ready[col] = ""

    if missing_in_csv:
        st.warning(f"Las siguientes columnas no estaban en el CSV y se rellenaron con valores por defecto: {missing_in_csv}")

    # Asegurar tipos antes de insertar
    for col in COLUMNS:
        if COL_TYPES[col].upper().startswith("INT"):
            df_ready[col] = pd.to_numeric(df_ready[col], errors='coerce').fillna(0).astype(int)
        elif COL_TYPES[col].upper() == "REAL":
            df_ready[col] = pd.to_numeric(df_ready[col], errors='coerce').fillna(0.0)
        else:
            df_ready[col] = df_ready[col].astype(str)

    st.subheader("Vista previa (columnas normalizadas y en orden esperado)")
    st.dataframe(df_ready.head(50))

    if st.button("⬆️ Subir al tablero"):
        try:
            # volver a chequear esquema y añadir columnas faltantes si quedara alguna
            existing_cols = get_table_columns(conn, "resultados")
            missing_cols = [c for c in COLUMNS if c not in existing_cols]
            if missing_cols:
                add_missing_columns(conn, missing_cols, "resultados")
                st.info(f"Se añadieron columnas faltantes antes del INSERT: {missing_cols}")

            # finalmente insertar (solo columnas esperadas, en orden)
            df_ready[COLUMNS].to_sql("resultados", conn, if_exists="append", index=False)
            st.success("Resultados agregados al tablero compartido.")
        except Exception as e:
            st.error("❌ Error al guardar en la base de datos:")
            st.write(e)
            st.write("Columnas existentes en la tabla:", get_table_columns(conn, "resultados"))
            st.write("Columnas preparadas en el DataFrame:", df_ready.columns.tolist())

# -----------------------------
# Mostrar resultados acumulados (formateados para lectura)
# -----------------------------
def formato_numero(x, decimales=2):
    try:
        return f"{x:,.{decimales}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return x

df_total = pd.read_sql("SELECT * FROM resultados", conn)

if not df_total.empty:
    st.subheader("📊 Resultados acumulados")
    # formatear copia para mostrar (no se altera la db)
    df_show = df_total.copy()
    for col in ["RentabilidadAnualizada","Riesgo","Sharpe","GananciaPromArriba","PerdidaPromAbajo","GananciaTotal","CapitalSobrante"]:
        if col in df_show.columns:
            df_show[col] = df_show[col].map(lambda v: formato_numero(v,2))
    st.dataframe(df_show)

    st.subheader("🏆 Top 3 por Sharpe Ratio")
    top3 = df_total.sort_values("Sharpe", ascending=False).head(3)
    st.table(top3)

    st.subheader("✨ Menciones Especiales")
    try:
        mas_rentable = df_total.loc[df_total["GananciaTotal"].idxmax()]
        st.write(f"**Más rentable:** {mas_rentable['Grupo']} con {formato_numero(mas_rentable['GananciaTotal'],2)}")
    except Exception:
        pass
    try:
        mas_seguro = df_total.loc[df_total["Riesgo"].idxmin()]
        st.write(f"**Más seguro:** {mas_seguro['Grupo']} con riesgo {formato_numero(mas_seguro['Riesgo'],2)}")
    except Exception:
        pass
    try:
        mas_consistente = df_total.loc[df_total["DiasArriba"].idxmax()]
        st.write(f"**Más consistente:** {mas_consistente['Grupo']} con {int(mas_consistente['DiasArriba'])} días arriba")
    except Exception:
        pass
    try:
        menor_sobrante = df_total.loc[df_total["CapitalSobrante"].idxmin()]
        st.write(f"**Menor capital sobrante:** {menor_sobrante['Grupo']} con {formato_numero(menor_sobrante['CapitalSobrante'],2)}")
    except Exception:
        pass
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
