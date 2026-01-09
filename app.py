import streamlit as st
import google.generativeai as genai
from PIL import Image

# 1. Configurare Pagină
st.set_page_config(page_title="Profesorul de Mate (Gemini)", page_icon="🎓")
st.title("🎓 Proful de Mate - Gemini Native")
st.caption("Rezolvă probleme din poze folosind biblioteca oficială Google")

# 2. Configurare API Key
# Încercăm să luăm cheia din Secrets, altfel o cerem în sidebar
if "GOOGLE_API_KEY" in st.secrets:
    api_key = st.secrets["GOOGLE_API_KEY"]
else:
    api_key = st.sidebar.text_input("Introdu Google API Key:", type="password")

if not api_key:
    st.info("Introdu cheia Google API pentru a începe.")
    st.stop()

# Configurare Google GenAI
try:
    genai.configure(api_key=api_key)
    # Inițializăm modelul cu instrucțiuni de sistem (Persona)
    model = genai.GenerativeModel(
        'gemini-1.5-flash',
        system_instruction="""Ești un profesor de matematică expert și răbdător.
        1. Când primești o imagine, analizează ecuațiile sau geometria din ea.
        2. Rezolvă problema pas cu pas.
        3. Explică logica într-un mod simplu, în limba română.
        4. Folosește LaTeX pentru formule matematice clare.
        """
    )
except Exception as e:
    st.error(f"Eroare la configurare: {e}")
    st.stop()

# 3. Interfața de Upload
st.sidebar.header("Zona de Lucru")
uploaded_file = st.sidebar.file_uploader("Încarcă o poză cu problema", type=["jpg", "jpeg", "png"])

img = None
if uploaded_file:
    # Încărcăm imaginea folosind PIL (Pillow)
    img = Image.open(uploaded_file)
    st.sidebar.image(img, caption="Imaginea ta", use_container_width=True)
    st.sidebar.success("Imagine pregătită!")

# 4. Istoric Chat
if "messages" not in st.session_state:
    st.session_state["messages"] = [
        {"role": "assistant", "content": "Salut! Sunt gata. Poți să încarci o poză sau să scrii o problemă."}
    ]

for msg in st.session_state.messages:
    # Google folosește "model" în loc de "assistant" în unele contexte, dar noi păstrăm convenția vizuală
    role = msg["role"]
    st.chat_message(role).write(msg["content"])

# 5. Input și Generare
if user_input := st.chat_input("Întreabă profesorul..."):
    # Afișăm mesajul utilizatorului
    st.session_state.messages.append({"role": "user", "content": user_input})
    st.chat_message("user").write(user_input)

    # Pregătim inputul pentru Gemini
    # Gemini acceptă o listă care poate conține text și imagini
    inputs = [user_input]
    if img:
        inputs.append(img)
        note = " (analizez imaginea...)"
    else:
        note = ""

    with st.chat_message("assistant"):
        with st.spinner(f"Calculez soluția...{note}"):
            try:
                # Apelăm direct API-ul Google
                response = model.generate_content(inputs)
                
                # Extragem textul
                response_text = response.text
                
                st.write(response_text)
                st.session_state.messages.append({"role": "assistant", "content": response_text})
            except Exception as e:
                st.error(f"Eroare la generare: {e}")
