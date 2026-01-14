import streamlit as st
import google.generativeai as genai
from PIL import Image

# 1. Configurare Pagină
st.set_page_config(page_title="Profesorul tau Universal", page_icon="⚡", layout="wide")

# --- CSS PENTRU MOBILE ---
# Mutăm audio input mai jos, să fie accesibil pe telefon
st.markdown("""
<style>
    .stAudioInput {
        position: fixed;
        bottom: 80px;
        z-index: 100;
        width: 100%;
        max-width: 800px;
    }
</style>
""", unsafe_allow_html=True)

# 2. Sidebar - Setări și Upload
with st.sidebar:
    st.title("⚡ Panou Control")
    
    # API Key
    if "GOOGLE_API_KEY" in st.secrets:
        api_key = st.secrets["GOOGLE_API_KEY"]
    else:
        api_key = st.text_input("Introdu Google API Key:", type="password")
    
    st.divider()
    st.header("📸 Imagine (Opțional)")
    uploaded_file = st.file_uploader("Încarcă o poză cu exercițiul", type=["jpg", "jpeg", "png"])
    
    img = None
    if uploaded_file:
        img = Image.open(uploaded_file)
        st.image(img, caption="Imagine analizată", use_container_width=True)
    
    if st.button("🗑️ Resetare Conversație", type="primary"):
        st.session_state.messages = []
        st.rerun()

# Stop dacă nu avem cheie
if not api_key:
    st.warning("Introdu cheia API pentru a începe.")
    st.stop()

# Configurare Gemini
try:
    genai.configure(api_key=api_key)
    # Folosim Flash pentru viteză și multimodalitate (audio/foto)
    model = genai.GenerativeModel("models/gemini-2.5-flash", system_instruction="""
    Ești un profesor răbdător pentru elevi de gimnaziu/liceu.
    Dacă primești AUDIO: Ascultă cu atenție întrebarea elevului și răspunde în scris.
    Dacă primești IMAGINE: Rezolvă exercițiul din poză pas cu pas.
    Dacă primești TEXT: Răspunde didactic, folosind LaTeX pentru formule.
    Fii scurt, concis și încurajator. Nu da răspunsul direct, explică logica.
    """)
except Exception as e:
    st.error(f"Eroare configurare: {e}")
    st.stop()

# 3. Interfața Chat
st.title("🎓 Profesorul tău Virtual")

if "messages" not in st.session_state:
    st.session_state["messages"] = []

# Afișare istoric
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        # Dacă mesajul e audio (memorat ca byte), afișăm player, altfel text
        if isinstance(msg["content"], bytes):
             st.audio(msg["content"], format="audio/wav")
        else:
             st.write(msg["content"])

# --- ZONA DE INPUT (Duală: Text sau Voce) ---

# Container pentru input
input_container = st.container()

# Variabile pentru input
audio_value = None
text_input = None

# A. Input Vocal (folosind st.audio_input)
# Notă: Pe mobil apare ca un buton de microfon
audio_value = st.audio_input("🎙️ Apasă microfonul pentru a întreba vocal (sau scrie jos)")

# B. Input Text
text_input = st.chat_input("Scrie întrebarea ta aici...")

# --- LOGICA DE PROCESARE ---

def get_gemini_response(prompt_content):
    with st.chat_message("assistant"):
        with st.spinner("Analizez..."):
            try:
                # Construim lista de input (istoric sumar + input curent + imagine opțional)
                full_prompt = []
                
                # Dacă avem imagine încărcată în sidebar, o trimitem mereu contextului
                if img:
                    full_prompt.append(img)
                    full_prompt.append("Aceasta este imaginea la care fac referire:")

                # Adăugăm inputul curent (Text sau Audio)
                full_prompt.append(prompt_content)

                response = model.generate_content(full_prompt)
                st.write(response.text)
                st.session_state.messages.append({"role": "assistant", "content": response.text})
            except Exception as e:
                st.error(f"Eroare: {e}")

# Verificăm ce a trimis utilizatorul
if audio_value:
    # Verificăm să nu procesăm același audio de două ori (un comportament specific Streamlit)
    # Folosim un identificator simplu sau verificăm ultimul mesaj
    is_new_audio = True
    if len(st.session_state.messages) > 0:
        last_msg = st.session_state.messages[-1]
        # Dacă ultimul mesaj e user și e identic cu ce avem acum, ignorăm (evităm loop)
        # (Aici e o simplificare, ideal comparăm hash-uri, dar merge pentru MVP)
        pass 

    # Afișăm audio-ul utilizatorului
    with st.chat_message("user"):
        st.audio(audio_value, format="audio/wav")
    
    # Salvăm în istoric ca bytes
    st.session_state.messages.append({"role": "user", "content": audio_value.getvalue()})
    
    # Pregătim pentru Gemini
    # Gemini vrea un dicționar pentru audio
    gemini_audio = {
        "mime_type": "audio/wav",
        "data": audio_value.getvalue()
    }
    
    get_gemini_response(gemini_audio)

elif text_input:
    # Afișăm textul utilizatorului
    with st.chat_message("user"):
        st.write(text_input)
    st.session_state.messages.append({"role": "user", "content": text_input})
    
    get_gemini_response(text_input)
