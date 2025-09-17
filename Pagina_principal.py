# Pagina_principal.py
import streamlit as st
import os
import sqlite3
import utilidades as util
import importlib.util, sys

st.set_page_config(page_title="Simulación Bursátil", layout="wide")

# ================== BASE DE DATOS (Jugadores) ==================
conn = sqlite3.connect("jugadores.db")
c = conn.cursor()
c.execute('''
    CREATE TABLE IF NOT EXISTS jugadores (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT UNIQUE,
        perfil TEXT
    )
''')
conn.commit()

# ================== PERFILES ==================
passwords = {
    "4539": "Conservador", "6758": "Conservador",
    "8795": "Moderado", "7906": "Moderado",
    "1357": "Arriesgado", "8745": "Arriesgado"
}

# ================== LOGIN ==================
def login_screen():
    st.title("Ingreso a la Simulación")
    username = st.text_input("Nombre del grupo")
    password = st.text_input("Contraseña", type="password")

    if st.button("Ingresar"):
        if password in passwords:
            perfil = passwords[password]
            c.execute("SELECT * FROM jugadores WHERE nombre = ?", (username,))
            data = c.fetchone()
            if data is None:
                c.execute("INSERT INTO jugadores (nombre, perfil) VALUES (?, ?)", (username, perfil))
                conn.commit()
            st.session_state["logged_in"] = True
            st.session_state["username"] = username
            st.session_state["perfil"] = perfil
            st.success(f"Bienvenido {username} | Perfil asignado: {perfil}")
            st.rerun()
        else:
            st.error("Contraseña incorrecta")

# ================== ESTADO DE SESIÓN ==================
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
if "current_page" not in st.session_state:
    st.session_state["current_page"] = "home"

# ---------------------------
# Aplicar estilos para ocultar el navegador automático de Streamlit
# (esto hace que la lista lateral/top-right NO aparezca en la pantalla de login)
# ---------------------------
util.aplicar_estilos(hide_streamlit_nav=True)

# ================== FLUJO PRINCIPAL ==================
if not st.session_state["logged_in"]:
    login_screen()
else:
    # Mostrar tu menú horizontal personalizado (sigue funcionando)
    util.generarMenu_horizontal()

    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

    if st.session_state["current_page"] == "home":
        st.title("BrainVest Capital")
        st.subheader("Crea tu propio portafolio de manera inteligente")
        st.write("Visualiza y analiza datos históricos de acciones de más de 400 empresas.")

        # Imagen desde GitHub RAW (HTML para evitar errores con st.image)
        img_url = "https://raw.githubusercontent.com/sebastianllano99/Portafolio/ef70520d06116183958a87132ba1056d95287779/IMG_2734.PNG"
        st.markdown(
            f"""
            <div style="text-align: center;">
                <img src="{img_url}" width="100%" />
            </div>
            """,
            unsafe_allow_html=True
        )

    elif st.session_state["current_page"] == "pagina_a":
        page_path = os.path.join(BASE_DIR, "pages", "1_Pagina_A.py")
    elif st.session_state["current_page"] == "pagina_b":
        page_path = os.path.join(BASE_DIR, "pages", "2_Pagina_B.py")
    elif st.session_state["current_page"] == "pagina_c":
        page_path = os.path.join(BASE_DIR, "pages", "3_Pagina_C.py")

    # Cargar la página seleccionada
    if st.session_state["current_page"] != "home":
        if not os.path.exists(page_path):
            st.error(f"No se encontró el archivo en: {page_path}")
        else:
            spec = importlib.util.spec_from_file_location("pagina", page_path)
            pagina = importlib.util.module_from_spec(spec)
            sys.modules["pagina"] = pagina
            spec.loader.exec_module(pagina)





