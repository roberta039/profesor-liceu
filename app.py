import streamlit as st
import google.generativeai as genai
from PIL import Image

# 1. Configurare Pagină
st.set_page_config(page_title="Profesor Universal (2.5 Flash)", page_icon="⚡")
st.title("⚡ Profesor Universal")
st.caption("Powered by Gemini 2.5 Flash")

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

# --- INITIALIZARE MODEL (FIX: GEMINI 2.5 FLASH) ---
# Nu mai există selector. Folosim direct acest ID.
FIXED_MODEL_ID = "models/gemini-2.5-flash"

try:
    model = genai.GenerativeModel(
        FIXED_MODEL_ID,
        system_instruction="""Ești un profesor universal (Mate, Fizică, Chimie) răbdător și empatic.
        
        REGULĂ STRICTĂ: Predă exact ca la școală (nivel Gimnaziu/Liceu). 
        NU confunda elevul cu detalii despre "aproximări" sau "lumea reală" decât dacă problema o cere specific.

        Ghid de comportament:
        1. MATEMATICĂ: Lucrează cu valori exacte. (ex: sqrt(2) rămâne sqrt(2)).
        2. FIZICĂ/CHIMIE: Condiții ideale (fără frecare).
        3. EXPLICATII: Pas cu pas, simplu, cu LaTeX ($...$) pentru formule.
        """
    )
except Exception as e:
    st.error(f"Eroare critică: Nu pot inițializa modelul {FIXED_MODEL_ID}. Verifică dacă numele este corect sau dacă ai acces la el.")
    st.stop()

# 3. Interfața de Upload
st.sidebar.header("📁 Materiale")
uploaded_file = st.sidebar.file_uploader("Încarcă o poză", type=["jpg", "jpeg", "png"])

img = None
if uploaded_file:
    img = Image.open(uploaded_file)
    st.sidebar.image(img, caption="Imagine încărcată", use_container_width=True)

# 4. Chat History
if "messages" not in st.session_state:
    st.session_state["messages"] = [{"role": "assistant", "content": "Salut! Sunt gata de treabă. Ce problemă rezolvăm azi?"}]

for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])

# 5. Input
if user_input := st.chat_input("Scrie problema..."):
    st.session_state.messages.append({"role": "user", "content": user_input})
    st.chat_message("user").write(user_input)

    inputs = [user_input]
    if img:
        inputs.append(img)

    with st.chat_message("assistant"):
        with st.spinner("Rezolv..."):
            try:
                response = model.generate_content(inputs)
                st.write(response.text)
                st.session_state.messages.append({"role": "assistant", "content": response.text})
            except Exception as e:
                st.error(f"Eroare: {e}")
