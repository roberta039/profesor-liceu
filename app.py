import streamlit as st
import google.generativeai as genai
from PIL import Image
from gtts import gTTS
from io import BytesIO
import sqlite3
import uuid
import time
import tempfile

# 1. Configurare Pagină
st.set_page_config(page_title="Profesor Liceu AI", page_icon="🎓", layout="wide")

st.markdown("""
<style>
    .stChatMessage { font-size: 16px; }
    div.stButton > button:first-child { background-color: #ff4b4b; color: white; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. SISTEMUL DE MEMORIE (Bază de date)
# ==========================================

def get_db_connection():
    conn = sqlite3.connect('chat_history.db', check_same_thread=False)
    return conn

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS history 
                 (session_id TEXT, role TEXT, content TEXT, timestamp REAL)''')
    conn.commit()
    conn.close()

def save_message_to_db(session_id, role, content):
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("INSERT INTO history VALUES (?, ?, ?, ?)", (session_id, role, content, time.time()))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Eroare DB: {e}")

def load_history_from_db(session_id):
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT role, content FROM history WHERE session_id=? ORDER BY timestamp ASC", (session_id,))
        data = c.fetchall()
        conn.close()
        return [{"role": row[0], "content": row[1]} for row in data]
    except:
        return []

def clear_history_db(session_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("DELETE FROM history WHERE session_id=?", (session_id,))
    conn.commit()
    conn.close()

init_db()

if "session_id" not in st.query_params:
    new_id = str(uuid.uuid4())
    st.query_params["session_id"] = new_id 
    st.session_state.session_id = new_id
else:
    st.session_state.session_id = st.query_params["session_id"]

# ==========================================
# 3. Configurare API cu ROTIRE AUTOMATĂ
# ==========================================

# 1. Încărcăm lista de chei
if "api_keys" in st.secrets:
    keys = st.secrets["api_keys"]
else:
    # Fallback dacă testezi local fără secrets și vrei input manual (doar prima cheie)
    k = st.sidebar.text_input("API Key:", type="password")
    keys = [k] if k else []

if not keys:
    st.info("Lipsesc cheile API.")
    st.stop()

# 2. Gestionăm indexul cheii curente în sesiune
if "key_index" not in st.session_state:
    st.session_state.key_index = 0

def configure_current_key():
    current_key = keys[st.session_state.key_index]
    genai.configure(api_key=current_key)

# Configurăm inițial cu prima cheie (sau cea la care am rămas)
configure_current_key()

# Definim Modelul (Aici pui System Instruction-ul tău mare)
model = genai.GenerativeModel("models/gemini-1.5-flash", 
    system_instruction="... (AICI PUI PROMPTUL TĂU MARE) ..."
)

# --- FUNCȚIE MAGICĂ PENTRU RETRY ---
def send_message_with_rotation(chat_session, payload):
    """
    Această funcție încearcă să trimită mesajul.
    Dacă eșuează din cauza limitei, schimbă cheia și încearcă din nou.
    """
    max_retries = len(keys) # Încercăm maxim o dată pe fiecare cheie
    
    for attempt in range(max_retries):
        try:
            # Încercăm să generăm răspunsul
            response = chat_session.send_message(payload)
            return response
            
        except Exception as e:
            error_msg = str(e)
            # Verificăm dacă eroarea este de cotă (429) sau resursă epuizată
            if "429" in error_msg or "ResourceExhausted" in error_msg or "Quota" in error_msg:
                print(f"⚠️ Cheia {st.session_state.key_index} a expirat. Schimb cheia...")
                
                # Trecem la următoarea cheie
                st.session_state.key_index = (st.session_state.key_index + 1) % len(keys)
                
                # Reconfigurăm global biblioteca genai
                configure_current_key()
                
                # Continuăm bucla (următoarea iterație va încerca din nou cu noua cheie)
                continue
            else:
                # Dacă e altă eroare (ex: conținut interzis, eroare de server), o aruncăm mai departe
                raise e
    
    # Dacă am trecut prin toate cheile și tot nu merge
    raise Exception("Toate cheile API sunt epuizate momentan. Te rog revino mai târziu.")

genai.configure(api_key=api_key)

model = genai.GenerativeModel("models/gemini-2.5-flash", 
    system_instruction="""
    ROL: Ești un profesor de liceu din România, universal (Mate, Fizică, Chimie, Literatură), bărbat, cu experiență în pregătirea pentru BAC.
    
    REGULI DE IDENTITATE (STRICT):
    1. Folosește EXCLUSIV genul masculin când vorbești despre tine.
       - Corect: "Sunt sigur", "Sunt pregătit", "Am fost atent", "Sunt bucuros".
       - GREȘIT: "Sunt sigură", "Sunt pregătită".
    2. Te prezinți ca "Domnul Profesor" sau "Profesorul tău virtual".
          TON ȘI ADRESARE (CRITIC):
    3. Vorbește DIRECT, la persoana I singular.
       - CORECT: "Salut, sunt aici să te ajut." / "Te ascult." / "Sunt pregătit."
       - GREȘIT: "Domnul profesor este aici." / "Profesorul te va ajuta."
    4. Fii cald, natural, apropiat și scurt. Evită introducerile pompoase.
    5. Folosește "Salut" sau "Te salut" în loc de formule foarte oficiale, dar păstrează respectul.
        
        REGULĂ STRICTĂ: Predă exact ca la școală (nivel Gimnaziu/Liceu). 
        NU confunda elevul cu detalii despre "aproximări" sau "lumea reală" (frecare, erori) decât dacă problema o cere specific.

        GHID DE COMPORTAMENT:

        1. MATEMATICĂ:
           - Lucrează cu valori exacte. (ex: $\sqrt{2}$ rămâne $\sqrt{2}$, nu 1.41).
           - Explică logica din spate, nu doar calculul.
           - Nu menționa că $\pi$ e infinit; folosește valorile standard.
           - Folosește LaTeX ($...$) pentru toate formulele.

        2. FIZICĂ/CHIMIE:
           - Presupune automat "condiții ideale" (fără frecare cu aerul, sisteme izolate).
           - Tratează problema exact așa cum apare în culegere.
           - Nu confunda elevul cu detalii de nivel universitar.

        3. LIMBA ȘI LITERATURA ROMÂNĂ (CRITIC):
           - Respectă STRICT programa școlară de BAC din România și canoanele criticii (G. Călinescu, E. Lovinescu, T. Vianu).
           - ATENȚIE MAJORA: Ion Creangă (Harap-Alb) este Basm Cult, dar specificul lui este REALISMUL (umanizarea fantasticului, oralitatea), nu romantismul.
           - La poezie: Încadrează corect (Romantism - Eminescu, Modernism - Blaga/Arghezi, Simbolism - Bacovia).
           - Structurează răspunsurile ca un eseu de BAC (Ipoteză -> Argumente (pe text) -> Concluzie).

        4. STIL DE PREDARE:
           - Explică simplu, cald și prietenos. Evită "limbajul de lemn".
           - Folosește analogii pentru concepte grele (ex: "Curentul e ca debitul apei").
           - La teorie: Definiție -> Exemplu Concret -> Aplicație.
           - La probleme: Explică pașii logici ("Facem asta pentru că..."), nu da doar calculul.

        5. MATERIALE UPLOADATE (Cărți/PDF):
           - Dacă primești o carte, păstrează sensul original în rezumate/traduceri.
           - Dacă elevul încarcă o poză sau un PDF, analizează tot conținutul înainte de a răspunde.
           - Păstrează sensul original al textelor din manuale.
        """
    )

# ==========================================
# 4. Sidebar & Upload (Codul Tău Integrat)
# ==========================================
st.title("🎓 Profesor Liceu")

with st.sidebar:
    st.header("⚙️ Opțiuni")
    if st.button("🗑️ Șterge Istoricul", type="primary"):
        clear_history_db(st.session_state.session_id)
        st.session_state.messages = []
        st.rerun()
    
    enable_audio = st.checkbox("🔊 Voce", value=False)
    st.divider()

    # --- CODUL TĂU NOU AICI ---
    st.header("📁 Materiale")
    uploaded_file = st.file_uploader("Încarcă Poză sau PDF", type=["jpg", "jpeg", "png", "pdf"])

    media_content = None # Variabila care va fi trimisă la AI
    
    if uploaded_file:
        file_type = uploaded_file.type
        
        if "image" in file_type:
            # Procesare Imagine
            media_content = Image.open(uploaded_file)
            st.image(media_content, caption="Imagine atașată", use_container_width=True)
            
        elif "pdf" in file_type:
            # Procesare PDF cu File API
            st.info("📄 PDF Detectat. Se pregătește...")
            
            try:
                # 1. Salvăm temporar
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                    tmp.write(uploaded_file.getvalue())
                    tmp_path = tmp.name
                
                # 2. Upload către Google (doar dacă nu l-am încărcat deja în această sesiune pentru a economisi timp)
                # Notă: Într-o aplicație simplă, re-upload-ul e ok. 
                # Pentru optimizare, am putea folosi session_state, dar File API e rapid pe Flash.
                with st.spinner("📚 Se trimite cartea la AI..."):
                    uploaded_pdf = genai.upload_file(tmp_path, mime_type="application/pdf")
                    
                    # Așteptăm ca fișierul să fie procesat (Active)
                    while uploaded_pdf.state.name == "PROCESSING":
                        time.sleep(1)
                        uploaded_pdf = genai.get_file(uploaded_pdf.name)
                        
                    media_content = uploaded_pdf
                    st.success(f"✅ Gata! AI-ul a citit: {uploaded_file.name}")
                    
            except Exception as e:
                st.error(f"Eroare upload PDF: {e}")

# ==========================================
# 5. Chat Logic
# ==========================================

if "messages" not in st.session_state or not st.session_state.messages:
    st.session_state.messages = load_history_from_db(st.session_state.session_id)

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if user_input := st.chat_input("Scrie aici..."):
    
    st.chat_message("user").write(user_input)
    st.session_state.messages.append({"role": "user", "content": user_input})
    save_message_to_db(st.session_state.session_id, "user", user_input)

    # Construim lista de mesaje pentru AI
    history_obj = []
    for msg in st.session_state.messages[:-1]:
        role_gemini = "model" if msg["role"] == "assistant" else "user"
        history_obj.append({"role": role_gemini, "parts": [msg["content"]]})

    chat_session = model.start_chat(history=history_obj)

    # PREGĂTIM PAYLOAD-ul (Mesaj + Fișier dacă există)
    final_payload = []
    
    # Adăugăm fișierul (PDF sau Imagine) dacă a fost încărcat acum
    if media_content:
        # Instrucțiune pentru AI despre fișier
        final_payload.append("Te rog să analizezi acest document/imagine atașat:")
        final_payload.append(media_content)
    
    # Adăugăm întrebarea elevului
    final_payload.append(user_input)

    with st.chat_message("assistant"):
        with st.spinner("Profesorul analizează..."):
            try:
                response = chat_session.send_message(final_payload)
                text_response = response.text
                
                st.markdown(text_response)
                
                st.session_state.messages.append({"role": "assistant", "content": text_response})
                save_message_to_db(st.session_state.session_id, "assistant", text_response)

                if enable_audio:
                    clean_text = text_response.replace("*", "").replace("$", "")[:500]
                    if clean_text:
                        sound_file = BytesIO()
                        tts = gTTS(text=clean_text, lang='ro')
                        tts.write_to_fp(sound_file)
                        st.audio(sound_file, format='audio/mp3')

            except Exception as e:
                st.error(f"Eroare: {e}")
