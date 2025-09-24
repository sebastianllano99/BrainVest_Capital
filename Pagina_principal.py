import streamlit as st
import os
import sqlite3
import utilidades as util
import importlib.util, sys

st.set_page_config(page_title="Simulación Bursátil", layout="wide")

# BASE DE DATOS 
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

#  PERFILES 
passwords = {
    "4539": "Conservador", "6758": "Conservador",
    "8795": "Moderado", "7906": "Moderado",
    "1357": "Arriesgado", "8745": "Arriesgado"
}

# LOGIN 
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

# ESTADO DE SESIÓN 
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
if "current_page" not in st.session_state:
    st.session_state["current_page"] = "home"

# Aplicar estilos
util.aplicar_estilos(hide_streamlit_nav=True)

# FLUJO PRINCIPAL 
if not st.session_state["logged_in"]:
    login_screen()
else:
    # Menú horizontal
    util.generarMenu_horizontal()

    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    PAGES_DIR = os.path.join(BASE_DIR, "pages")

    # HOME
    if st.session_state["current_page"] == "home":
        st.title("BrainVest Capital")
        st.subheader("Crea tu propio portafolio de manera inteligente")
        st.write("Visualiza y analiza datos históricos de acciones de más de 400 empresas.")

        img_url = "https://raw.githubusercontent.com/sebastianllano99/Portafolio/ef70520d06116183958a87132ba1056d95287779/IMG_2734.PNG"
        st.markdown(
            f"""
            <div style="text-align: center;">
                <img src="{img_url}" width="100%" />
            </div>
            """,
            unsafe_allow_html=True
        )

    # PÁGINAS
    else:
                mapping = {
            "pagina_a": "1_Pagina_A.py",
            "pagina_b": "2_Pagina_B.py",
            "pagina_c": "3_Pagina_C.py",
            "pagina_d": "4_Pagina_D.py"  
        }


        page_file = mapping.get(st.session_state["current_page"])
        if page_file:
            page_path = os.path.join(PAGES_DIR, page_file)
            if not os.path.exists(page_path):
                st.error(f"No se encontró el archivo en: {page_path}")
            else:
                spec = importlib.util.spec_from_file_location("pagina", page_path)
                pagina = importlib.util.module_from_spec(spec)
                sys.modules["pagina"] = pagina
                spec.loader.exec_module(pagina)

