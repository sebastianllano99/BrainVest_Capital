# utilidades.py
import streamlit as st

def aplicar_estilos():
    st.markdown(
        """
        <style>
        section[data-testid="stSidebarNav"] {display: none !important;}
        div[data-testid="stSidebarNav"] {display: none !important;}
        .css-1d391kg { padding-top: 10px; }
        </style>
        """,
        unsafe_allow_html=True
    )

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
        if st.button("Inicio"): st.session_state["current_page"] = "home"
    with cols[1]:
        if st.button("Página A"): st.session_state["current_page"] = "pagina_a"
    with cols[2]:
        if st.button("Página B"): st.session_state["current_page"] = "pagina_b"
    with cols[3]:
        if st.button("Página C"): st.session_state["current_page"] = "pagina_c"
