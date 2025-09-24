import streamlit as st
import sqlite3
import pandas as pd

# Conectar a la misma base
conn = sqlite3.connect("jugadores.db")
c = conn.cursor()

# Crear tabla resultados si no existe
c.execute('''
    CREATE TABLE IF NOT EXISTS resultados (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        grupo TEXT UNIQUE,
        rentabilidad REAL,
        riesgo REAL,
        sharpe REAL,
        dias_arriba INTEGER,
        dias_abajo INTEGER,
        ganancia_prom_arriba REAL,
        perdida_prom_abajo REAL,
        ganancia_total REAL
    )
''')
conn.commit()

st.title("📊 Resultados de la Simulación")
st.write("Cada grupo puede subir sus resultados aquí y ver los de los demás.")

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

        if st.button("📥 Subir"):
            for _, row in df.iterrows():
                c.execute('''
                    INSERT INTO resultados (grupo,rentabilidad,riesgo,sharpe,
                        dias_arriba,dias_abajo,ganancia_prom_arriba,
                        perdida_prom_abajo,ganancia_total)
                    VALUES (?,?,?,?,?,?,?,?,?)
                    ON CONFLICT(grupo) DO UPDATE SET
                        rentabilidad=excluded.rentabilidad,
                        riesgo=excluded.riesgo,
                        sharpe=excluded.sharpe,
                        dias_arriba=excluded.dias_arriba,
                        dias_abajo=excluded.dias_abajo,
                        ganancia_prom_arriba=excluded.ganancia_prom_arriba,
                        perdida_prom_abajo=excluded.perdida_prom_abajo,
                        ganancia_total=excluded.ganancia_total
                ''', tuple(row))
            conn.commit()
            st.success("Resultados guardados correctamente 🎉")

    else:
        st.error("❌ El CSV no tiene las columnas esperadas.")

# Botón refrescar para ver todos los resultados
if st.button("🔄 Actualizar"):
    c.execute("SELECT grupo,rentabilidad,riesgo,sharpe,dias_arriba,dias_abajo,ganancia_total FROM resultados")
    rows = c.fetchall()
    if rows:
        df_total = pd.DataFrame(rows, columns=[
            "Grupo","Rentabilidad","Riesgo","Sharpe","Días Arriba","Días Abajo","Ganancia Total"
        ])
        st.dataframe(df_total)

        # Podio por Sharpe (puedes cambiar el criterio)
        st.subheader("🏆 Top 3 por Sharpe Ratio")
        top3 = df_total.sort_values("Sharpe", ascending=False).head(3)
        st.table(top3)
    else:
        st.info("Aún no hay resultados guardados.")
