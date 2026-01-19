import streamlit as st
import google.generativeai as genai
from PIL import Image
from gtts import gTTS
from io import BytesIO
import sqlite3
import uuid
import time
import tempfile
import ast

# 1. Configurare Pagină
st.set_page_config(page_title="Profesor Liceu AI", page_icon="🎓", layout="wide")

# CSS: Ascundem meniul standard Streamlit și stilizăm chat-ul
st.markdown("""
<style>
    .stChatMessage { font-size: 16px; }
    div.stButton > button:first-child { background-color: #ff4b4b; color: white; }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. SISTEMUL DE MEMORIE (Bază de date)
# ==========================================

def get_db_connection():
    # check_same_thread=False e critic pentru Streamlit Cloud
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

# Gestionare Session ID
if "session_id" not in st.query_params:
    new_id = str(uuid.uuid4())
    st.query_params["session_id"] = new_id 
    st.session_state.session_id = new_id
else:
    st.session_state.session_id = st.query_params["session_id"]

# ==========================================
# 3. Configurare API cu ROTIRE AUTOMATĂ
# ==========================================

# Încărcăm lista de chei din Secrets
if "GOOGLE_API_KEY" in st.secrets:
    keys = st.secrets["GOOGLE_API_KEY"]
elif "GOOGLE_API_KEY" in st.secrets:
    keys = [st.secrets["GOOGLE_API_KEY"]]
else:
    k = st.sidebar.text_input("API Key:", type="password")
    keys = [k] if k else []

# Asigurare format Listă
if isinstance(keys, str):
    try:
        keys = ast.literal_eval(keys)
    except:
        keys = [keys]

if not keys:
    st.warning("⚠️ Nu s-au găsit chei API. Configurează secrets.toml.")
    st.stop()

# Indexul cheii curente
if "key_index" not in st.session_state:
    st.session_state.key_index = 0

def configure_current_key():
    if st.session_state.key_index >= len(keys):
        st.session_state.key_index = 0   
    current_key = keys[st.session_state.key_index]
    genai.configure(api_key=current_key)

configure_current_key()

# MODELUL (Gemini 2.5 Flash - cel rapid)
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
    5. Folosește "Salut" sau "Te salut" în loc de formule foarte oficiale.
        
    REGULĂ STRICTĂ: Predă exact ca la școală (nivel Gimnaziu/Liceu). 
    NU confunda elevul cu detalii despre "aproximări" sau "lumea reală" (frecare, erori) decât dacă problema o cere specific.

    GHID DE COMPORTAMENT:
    1. MATEMATICĂ:
       - Lucrează cu valori exacte ($\sqrt{2}$, $\pi$) sau standard.
       - Dacă rezultatul e $\sqrt{2}$, lasă-l $\sqrt{2}$. Nu spune "care este aproximativ 1.41".
       - Nu menționa că $\pi$ e infinit; folosește valorile din manual fără comentarii suplimentare. 
       - Explică logica din spate, nu doar calculul.
       - Dacă rezultatul e rad(2), lasă-l rad(2). Nu îl calcula aproximativ.
       - Folosește LaTeX ($...$) pentru toate formulele.

    2. FIZICĂ/CHIMIE:
       - Presupune automat "condiții ideale".
       - Tratează problema exact așa cum apare în culegere.
       - Nu menționa frecarea cu aerul, pierderile de căldură sau imperfecțiunile aparatelor de măsură.
       - Tratează problema exact așa cum apare în culegere, într-un univers matematic perfect.

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

# --- FUNCȚIE MAGICĂ PENTRU RETRY + STREAMING ---
def send_message_with_rotation(chat_session, payload):
    max_retries = len(keys)
    for attempt in range(max_retries):
        try:
            # stream=True este cheia vitezei
            response = chat_session.send_message(payload, stream=True)
            return response
        except Exception as e:
            error_msg = str(e)
            # Coduri eroare limită: 429, ResourceExhausted
            if "429" in error_msg or "ResourceExhausted" in error_msg or "Quota" in error_msg:
                st.toast(f"⚠️ Schimb motorul AI... (Cheia {st.session_state.key_index + 1} epuizată)", icon="🔄")
                st.session_state.key_index = (st.session_state.key_index + 1) % len(keys)
                configure_current_key()
                continue
            else:
                raise e
    raise Exception("Toate serverele sunt ocupate momentan.")

# ==========================================
# 4. Sidebar & Upload
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

    st.header("📁 Materiale")
    uploaded_file = st.file_uploader("Încarcă Poză sau PDF", type=["jpg", "jpeg", "png", "pdf"])

    media_content = None 
    
    if uploaded_file:
        file_type = uploaded_file.type
        if "image" in file_type:
            media_content = Image.open(uploaded_file)
            st.image(media_content, caption="Imagine atașată", use_container_width=True)
        elif "pdf" in file_type:
            st.info("📄 PDF Detectat. Se pregătește...")
            try:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                    tmp.write(uploaded_file.getvalue())
                    tmp_path = tmp.name
                
                with st.spinner("📚 Se trimite cartea la AI..."):
                    uploaded_pdf = genai.upload_file(tmp_path, mime_type="application/pdf")
                    while uploaded_pdf.state.name == "PROCESSING":
                        time.sleep(1)
                        uploaded_pdf = genai.get_file(uploaded_pdf.name)  
                    media_content = uploaded_pdf
                    st.success(f"✅ Gata! AI-ul a citit: {uploaded_file.name}")
            except Exception as e:
                st.error(f"Eroare upload PDF: {e}")

# ==========================================
# 5. Chat Logic (Cu Streaming)
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

    history_obj = []
    for msg in st.session_state.messages[:-1]:
        role_gemini = "model" if msg["role"] == "assistant" else "user"
        history_obj.append({"role": role_gemini, "parts": [msg["content"]]})

    chat_session = model.start_chat(history=history_obj)

    final_payload = []
    if media_content:
        final_payload.append("Te rog să analizezi acest document/imagine atașat:")
        final_payload.append(media_content)
    final_payload.append(user_input)

    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""
        
        try:
            # Apelăm funcția cu STREAMING
            response_stream = send_message_with_rotation(chat_session, final_payload)
            
            # Afișăm textul bucată cu bucată
            for chunk in response_stream:
                if chunk.text:
                    full_response += chunk.text
                    message_placeholder.markdown(full_response + "▌")
            
            # Text final curat
            message_placeholder.markdown(full_response)
            
            # Salvare
            st.session_state.messages.append({"role": "assistant", "content": full_response})
            save_message_to_db(st.session_state.session_id, "assistant", full_response)

            # Audio după generare
            if enable_audio:
                with st.spinner("Generez vocea..."):
                    clean_text = full_response.replace("*", "").replace("$", "")[:500]
                    if clean_text:
                        sound_file = BytesIO()
                        tts = gTTS(text=clean_text, lang='ro')
                        tts.write_to_fp(sound_file)
                        st.audio(sound_file, format='audio/mp3')

        except Exception as e:
            st.error(f"Eroare: {e}")
