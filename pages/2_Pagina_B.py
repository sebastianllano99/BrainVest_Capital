import streamlit as st
import pandas as pd
import altair as alt
import sys, os

#  Ajuste para que encuentre utilidades.py
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
import utilidades as util

# Ocultamos sidebar y aplicamos estilos
util.aplicar_estilos()

#  Bloqueamos acceso directo
if "current_page" not in st.session_state or st.session_state["current_page"] != "pagina_b":
    st.warning(" Accede a esta sección solo desde el menú superior en la página principal.")
    st.stop()

# Si entra correctamente desde el menú horizontal
util.generarMenu_horizontal()
st.title("📈 Simulación")

#  Entrada de datos 
start, end, symbol = util.get_input()
df = util.get_data(symbol, start, end)
company_name = util.get_company_name(symbol)

# Normalizar columnas 
df = df.rename(columns=lambda x: x.strip().lower().replace(" ", "_"))

if df.empty:
    st.warning("No hay datos para el rango de fechas seleccionado.")
else:
    st.subheader(f"{company_name} - Retornos diarios")

    if "precio_cierre" in df.columns:
        # Convertir a número antes de calcular retornos
        df["precio_cierre"] = pd.to_numeric(df["precio_cierre"], errors="coerce")
        df["retorno_diario"] = df["precio_cierre"].pct_change()

        chart = alt.Chart(df.dropna()).mark_line(color="green").encode(
            x=alt.X("fecha:T", title="Fecha", axis=alt.Axis(format="%b %Y", labelAngle=-45)),
            y=alt.Y("retorno_diario:Q", title="Retorno Diario")
        ).properties(width=700, height=400).interactive()
        st.altair_chart(chart, use_container_width=True)
    else:
        st.error(" No encontré columna de precio de cierre")

    # --- Tabla estadística ---
    util.mostrar_tabla_estadistica(df, " Estadísticas comparativas")
