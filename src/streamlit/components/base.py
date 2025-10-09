import streamlit as st


def init_page_config():
    st.set_page_config(
        layout="wide",
        initial_sidebar_state="expanded",
        menu_items={
            "Get help": "https://sample.com",
        },
    )
