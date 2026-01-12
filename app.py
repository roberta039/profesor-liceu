import streamlit as st
import google.generativeai as genai
from PIL import Image
import re # Pentru a extrage numerele din versiune

# 1. Configurare Pagină
st.set_page_config(page_title="Profesor Universal (AI 3.0 Ready)", page_icon="🧠")
st.title("🧠 Profesor Universal (Logic Sort)")

# 2. Configurare API Key
if "GOOGLE_API_KEY" in st.secrets:
    api_key = st.secrets["GOOGLE_API_KEY"]
else:
    api_key = st.sidebar.text_input("Introdu Google API Key:", type="password")

if not api_key:
    st.info("Introdu cheia Google API pentru a începe.")
    st.stop()

try:
    genai.configure(api_key=api_key)
except Exception as e:
    st.error(f"Eroare la configurare cheie: {e}")
    st.stop()

# --- ALGORITMUL DE SELECTIE INTELIGENTĂ ---
def calculate_model_score(model_name):
    """
    Această funcție dă o notă fiecărui model bazat pe lista ta din poză.
    Cu cât 
