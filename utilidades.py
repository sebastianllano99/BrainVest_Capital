# utilidades.py
import streamlit as st

def aplicar_estilos(hide_streamlit_nav=True):
    """
    Aplica estilos globales. Si hide_streamlit_nav=True, oculta el navegador
    automático de páginas que Streamlit genera (sidebar / toolbar).
    """
    css = """
    <style>
    /* Oculta el navegador lateral automático (cuando existe la carpeta pages/) */
    section[data-testid="stSidebarNav"], div[data-testid="stSidebarNav"] { display: none !important; }

    /* Oculta la toolbar / botón de páginas (top-right) si existe */
    div[data-testid="stToolbar"], header[data-testid="stHeader"], button[data-testid="stToolbarButton"], button[aria-label="Toggle navigation"] { display: none !important; }

    /* Ajustes visuales pequeños que ya tenías */
    .css-1d391kg { padding-top: 10px; }
    </style>
    """
    if hide_streamlit_nav:
        st.markdown(css, unsafe_allow_html=True)


def generarMenu_horizontal():
    st.markdown(
        """
        <style>
        .stButton>button {
            border-radius: 8px;
            padding: 8px 18px;
            font-weight: 600;
            border: 1px solid #d1d5db;
            background-color: #f3f4f6;
            color: #374151;
            cursor: pointer;
            transition: all 0.2s ease;
        }
        .stButton>button:hover {
            background-color: #2563eb;
            color: white;
            border-color: #1d4ed8;
            transform: translateY(-1px);
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    cols = st.columns(4)
    with cols[0]:
        if st.button("Inicio"):
            st.session_state["current_page"] = "home"
    with cols[1]:
        if st.button("Información"):
            st.session_state["current_page"] = "pagina_a"
    with cols[2]:
        if st.button("Mi Portafolio"):
            st.session_state["current_page"] = "pagina_b"
    with cols[3]:
        if st.button("Resultados"):
            st.session_state["current_page"] = "pagina_c"
   



