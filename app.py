import streamlit as st
import google.generativeai as genai
from PIL import Image
import tempfile
from gtts import gTTS
from io import BytesIO
import sqlite3
import uuid
import time

# 1. Configurare Pagină
st.set_page_config(page_title="Profesor Liceu AI", page_icon="🎓", layout="wide")

# CSS pentru aspect
st.markdown("""
<style>
    .stChatMessage { ensure-font-size: 16px; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. SISTEMUL DE MEMORIE (Bază de date)
# ==========================================

def init_db():
    conn = sqlite3.connect('chat_history.db')
    c = conn.cursor()
    # Creăm tabelul dacă nu există
    c.execute('''CREATE TABLE IF NOT EXISTS history 
                 (session_id TEXT, role TEXT, content TEXT, timestamp REAL)''')
    conn.commit()
    conn.close()

def save_message_to_db(session_id, role, content):
    conn = sqlite3.connect('chat_history.db')
    c = conn.cursor()
    c.execute("INSERT INTO history VALUES (?, ?, ?, ?)", (session_id, role, content, time.time()))
    conn.commit()
    conn.close()

def load_history_from_db(session_id):
    conn = sqlite3.connect('chat_history.db')
    c = conn.cursor()
    c.execute("SELECT role, content FROM history WHERE session_id=? ORDER BY timestamp ASC", (session_id,))
    data = c.fetchall()
    conn.close()
    return [{"role": row[0], "content": row[1]} for row in data]

def clear_history_db(session_id):
    conn = sqlite3.connect('chat_history.db')
    c = conn.cursor()
    c.execute("DELETE FROM history WHERE session_id=?", (session_id,))
    conn.commit()
    conn.close()

# Inițializăm baza de date la pornire
init_db()

# Gestionare Session ID (identificatorul elevului)
if "session_id" not in st.query_params:
    # Dacă nu are ID, generăm unul nou
    new_id = str(uuid.uuid4())
    st.query_params["session_id"] = new_id
    st.session_state.session_id = new_id
else:
    # Dacă are ID în URL, îl folosim pe acela
    st.session_state.session_id = st.query_params["session_id"]

# ==========================================
# 3. Configurare API
# ==========================================
if "GOOGLE_API_KEY" in st.secrets:
    api_key = st.secrets["GOOGLE_API_KEY"]
else:
    api_key = st.sidebar.text_input("Introdu Google API Key:", type="password")

if not api_key:
    st.warning("Te rog introdu cheia API în sidebar.")
    st.stop()

genai.configure(api_key=api_key)
model = genai.GenerativeModel("models/gemini-2.5-flash", 
    system_instruction="""Ești un profesor universal (Mate, Fizică, Chimie, Literatură) răbdător și empatic.
        
        REGULĂ STRICTĂ: Predă exact ca la școală (nivel Gimnaziu/Liceu). 
        NU confunda elevul cu detalii despre "aproximări" sau "lumea reală" (frecare, erori) decât dacă problema o cere specific.

        GHID DE COMPORTAMENT:

        1. MATEMATICĂ:
           - Lucrează cu valori exacte. (ex: $\sqrt{2}$ rămâne $\sqrt{2}$, nu 1.41).
           - Nu menționa că $\pi$ e infinit; folosește valorile standard.
           - Folosește LaTeX ($...$) pentru toate formulele.

        2. FIZICĂ/CHIMIE:
           - Presupune automat "condiții ideale" (fără frecare cu aerul, sisteme izolate).
           - Tratează problema exact așa cum apare în culegere.

        3. LIMBA ȘI LITERATURA ROMÂNĂ (CRITIC):
           - Respectă STRICT programa școlară din România și canoanele criticii (G. Călinescu, E. Lovinescu, T. Vianu).
           - ATENȚIE MAJORA: Ion Creangă (Harap-Alb) este Basm Cult, dar specificul lui este REALISMUL (umanizarea fantasticului, oralitatea), nu romantismul.
           - La poezie: Încadrează corect (Romantism - Eminescu, Modernism - Blaga/Arghezi, Simbolism - Bacovia).
           - Structurează răspunsurile ca un eseu de BAC (Ipoteză, Argumente, Concluzie).

        4. STIL DE PREDARE:
           - Explică simplu, cald și prietenos. Evită "limbajul de lemn".
           - Folosește analogii pentru concepte grele (ex: "Curentul e ca debitul apei").
           - La teorie: Definiție -> Exemplu Concret -> Aplicație.
           - La probleme: Explică pașii logici ("Facem asta pentru că..."), nu da doar calculul.

        5. MATERIALE UPLOADATE (Cărți/PDF):
           - Dacă primești o carte, păstrează sensul original în rezumate/traduceri.
        """
    )
# ==========================================
# 4. Sidebar & Butoane
# ==========================================
st.title("🎓 Profesor Liceu")

st.sidebar.header("⚙️ Opțiuni")

# BUTON RESET TEMA
if st.sidebar.button("🗑️ Temă Nouă (Șterge Memoria)", type="primary"):
    clear_history_db(st.session_state.session_id)
    st.session_state.messages = []
    st.rerun()

enable_audio = st.sidebar.checkbox("🔊 Activează Vocea", value=False)
st.sidebar.divider()

uploaded_files = st.sidebar.file_uploader("Încarcă materiale (Poză/PDF)", type=["jpg", "png", "pdf"], accept_multiple_files=True)

# Procesare imagini (pentru sesiunea curentă - imaginile nu se salvează în DB pt a nu o bloca)
current_images = []
if uploaded_files:
    for up_file in uploaded_files:
        if "image" in up_file.type:
            img = Image.open(up_file)
            current_images.append(img)
            st.sidebar.image(img, caption="Imagine încărcată", use_container_width=True)

# ==========================================
# 5. Încărcare Istoric și Chat
# ==========================================

# Încărcăm mesajele din DB în Session State dacă e gol
if "messages" not in st.session_state or not st.session_state.messages:
    db_messages = load_history_from_db(st.session_state.session_id)
    st.session_state.messages = db_messages

# Afișare mesaje anterioare
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ==========================================
# 6. Logică Input Utilizator
# ==========================================
if user_input := st.chat_input("Întreabă profesorul..."):
    
    # 1. Afișăm și salvăm mesajul utilizatorului
    st.session_state.messages.append({"role": "user", "content": user_input})
    save_message_to_db(st.session_state.session_id, "user", user_input) # <--- SALVARE DB
    st.chat_message("user").write(user_input)

    # 2. Pregătim Payload pentru AI
    payload = []
    if current_images:
        payload.extend(current_images)
    payload.append(user_input)
    
    # Construim istoricul pentru AI (fără a retrimite imagini vechi, doar text)
    history_obj = []
    for msg in st.session_state.messages[:-1]: 
        role_gemini = "model" if msg["role"] == "assistant" else "user"
        history_obj.append({"role": role_gemini, "parts": [msg["content"]]})

    chat_session = model.start_chat(history=history_obj)

    # 3. Generăm răspunsul
    with st.chat_message("assistant"):
        with st.spinner("Gândesc..."):
            try:
                response = chat_session.send_message(payload)
                text_response = response.text
                
                st.markdown(text_response)
                
                # 4. Salvăm răspunsul AI
                st.session_state.messages.append({"role": "assistant", "content": text_response})
                save_message_to_db(st.session_state.session_id, "assistant", text_response) # <--- SALVARE DB

                # Audio (Opțional)
                if enable_audio:
                    clean_text = text_response.replace("*", "").replace("$", "")[:500]
                    sound_file = BytesIO()
                    tts = gTTS(text=clean_text, lang='ro')
                    tts.write_to_fp(sound_file)
                    st.audio(sound_file, format='audio/mp3')

            except Exception as e:
                st.error(f"Eroare: {e}")
