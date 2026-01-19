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
import re  # <--- ACEASTA ERA LIPSA

# ==========================================
# 1. CONFIGURARE PAGINĂ & CSS
# ==========================================
st.set_page_config(page_title="Profesor Liceu AI", page_icon="🎓", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
    .stChatMessage { font-size: 16px; }
    div.stButton > button:first-child { background-color: #ff4b4b; color: white; }
    
    /* Ascundem footer-ul standard Streamlit */
    footer {visibility: hidden;}
    
    /* Stil pentru containerul SVG (desene) */
    .svg-container {
        background-color: white;
        padding: 20px;
        border-radius: 10px;
        border: 1px solid #ddd;
        text-align: center;
        margin: 10px 0;
        overflow: auto;
        max-width: 100%;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. SISTEM DE MEMORIE (Bază de date)
# ==========================================
def get_db_connection():
    return sqlite3.connect('chat_history.db', check_same_thread=False)

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
# 3. ROTIRE API & CONFIGURARE
# ==========================================

raw_keys = None
if "GOOGLE_API_KEYS" in st.secrets:
    raw_keys = st.secrets["GOOGLE_API_KEYS"]
elif "GOOGLE_API_KEY" in st.secrets:
    raw_keys = [st.secrets["GOOGLE_API_KEY"]]
else:
    k = st.sidebar.text_input("API Key (Manual):", type="password")
    raw_keys = [k] if k else []

keys = []
if raw_keys:
    if isinstance(raw_keys, str):
        try:
            raw_keys = ast.literal_eval(raw_keys)
        except:
            raw_keys = [raw_keys]
    
    if isinstance(raw_keys, list):
        for k in raw_keys:
            if k and isinstance(k, str):
                clean_k = k.strip().strip('"').strip("'")
                if clean_k:
                    keys.append(clean_k)

if not keys:
    st.error("❌ Nu am găsit nicio cheie API validă.")
    st.stop()

if "key_index" not in st.session_state:
    st.session_state.key_index = 0

# --- PROMPT-UL SISTEMULUI (Hărți + Salut) ---
SYSTEM_PROMPT = """
ROL: Ești un profesor de liceu din România, universal (Mate, Fizică, Chimie, Literatură si Gramatica Romana, Franceza, Engleza, Geografie, Istorie, Informatica), bărbat, cu experiență în pregătirea pentru BAC.
    
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
    5. NU SALUTA în fiecare mesaj. Salută DOAR la începutul unei conversații noi.
    6. Dacă elevul pune o întrebare directă, răspunde DIRECT la subiect, fără introduceri de genul "Salut, desigur...".
    7. Folosește "Salut" sau "Te salut" în loc de formule foarte oficiale.
        
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

    5. FUNCȚIE SPECIALĂ - DESENARE (SVG):
           Dacă elevul cere un desen, o diagramă, o figură geometrică sau o hartă schematică:
           1. Generează cod SVG valid, curat, pe fundal alb sau transparent.
           2. Codul SVG trebuie să fie încadrat STRICT între aceste tag-uri speciale:
           [[DESEN_SVG]]
            <svg viewBox="0 0 500 400" xmlns="http://www.w3.org/2000/svg"> ... </svg>
           [[/DESEN_SVG]]
           3. Nu folosi markdown (```xml). Doar tag-urile mele.

    6. REGULI SPECIFICE PENTRU HĂRȚI (GEOGRAFIE):
           - NU desena un simplu pătrat sau dreptunghi pentru o țară!
           - Folosește tag-ul <path> sau <polygon> cu mai multe puncte (minim 10-15 puncte) pentru a aproxima forma țării.
           - Râurile să fie linii albastre (<path stroke="blue">).
           - Adaugă etichete text (<text>).
    
    7. MATERIALE UPLOADATE (Cărți/PDF):
           - Dacă primești o carte, păstrează sensul original în rezumate/traduceri.
           - Dacă elevul încarcă o poză sau un PDF, analizează tot conținutul înainte de a răspunde.
           - Păstrează sensul original al textelor din manuale.
    """

# Configurare Filtre de Siguranță
safety_settings = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
]

# --- FUNCȚIE GENERATOR CU ROTIRE ---
def run_chat_with_rotation(history_obj, payload):
    max_retries = len(keys) * 2
    
    for attempt in range(max_retries):
        try:
            if st.session_state.key_index >= len(keys):
                 st.session_state.key_index = 0
            
            current_key = keys[st.session_state.key_index]
            genai.configure(api_key=current_key)
            
            model = genai.GenerativeModel(
                "models/gemini-2.5-flash", 
                system_instruction=SYSTEM_PROMPT,
                safety_settings=safety_settings
            )
            chat = model.start_chat(history=history_obj)
            
            response_stream = chat.send_message(payload, stream=True)
            
            for chunk in response_stream:
                try:
                    text_part = chunk.text
                    if text_part:
                        yield text_part
                except ValueError:
                    continue
            return 

        except Exception as e:
            error_msg = str(e)
            
            if "503" in error_msg or "overloaded" in error_msg:
                st.toast("🐢 Serverele Google sunt aglomerate. Reîncerc...", icon="⏳")
                time.sleep(2)
                continue
                
            elif "400" in error_msg or "429" in error_msg or "ResourceExhausted" in error_msg or "Quota" in error_msg or "API key not valid" in error_msg:
                st.toast(f"⚠️ Schimb motorul AI (Cheia {st.session_state.key_index + 1})...", icon="🔄")
                st.session_state.key_index = (st.session_state.key_index + 1) % len(keys)
                continue
            else:
                raise e
    
    raise Exception("Serviciul este momentan indisponibil. Încearcă mai târziu.")

# ==========================================
# 4. SIDEBAR & UPLOAD
# ==========================================
st.title("🎓 Profesor Liceu AI")

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
        genai.configure(api_key=keys[st.session_state.key_index])
        file_type = uploaded_file.type

        if "image" in file_type:
            media_content = Image.open(uploaded_file)
            st.image(media_content, caption="Imagine atașată", use_container_width=True)
        elif "pdf" in file_type:
            st.info("📄 PDF Detectat. Se procesează...")
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
                    st.success(f"✅ Gata: {uploaded_file.name}")
            except Exception as e:
                st.error(f"Eroare upload PDF: {e}")

# ==========================================
# 5. CHAT LOGIC (CU RANDAREE SVG)
# ==========================================

# Funcție ajutătoare pentru afișarea mesajelor cu SVG randat
def render_message_with_svg(content):
    if "[[DESEN_SVG]]" in content and "[[/DESEN_SVG]]" in content:
        try:
            parts = content.split("[[DESEN_SVG]]")
            before_svg = parts[0]
            remaining = parts[1]
            
            svg_parts = remaining.split("[[/DESEN_SVG]]")
            svg_code = svg_parts[0].strip()
            after_svg = svg_parts[1] if len(svg_parts) > 1 else ""
            
            if before_svg.strip():
                st.markdown(before_svg)
            
            if "<svg" in svg_code and "</svg>" in svg_code:
                 start_idx = svg_code.find("<svg")
                 end_idx = svg_code.find("</svg>") + 6
                 clean_svg = svg_code[start_idx:end_idx]
                 st.markdown(f'<div class="svg-container">{clean_svg}</div>', unsafe_allow_html=True)
            else:
                 st.error("Eroare la randarea desenului: Cod SVG invalid.")
            
            if after_svg.strip():
                st.markdown(after_svg)
        except Exception as e:
            st.error(f"Eroare la procesarea desenului: {e}")
            st.markdown(content)
    else:
        st.markdown(content)

# Încărcare istoric
if "messages" not in st.session_state or not st.session_state.messages:
    st.session_state.messages = load_history_from_db(st.session_state.session_id)

# Afișare istoric
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        if msg["role"] == "assistant":
            render_message_with_svg(msg["content"])
        else:
            st.markdown(msg["content"])

# Input utilizator
if user_input := st.chat_input("Întreabă profesorul..."):
    
    st.chat_message("user").write(user_input)
    st.session_state.messages.append({"role": "user", "content": user_input})
    save_message_to_db(st.session_state.session_id, "user", user_input)

    history_obj = []
    for msg in st.session_state.messages[:-1]:
        role_gemini = "model" if msg["role"] == "assistant" else "user"
        history_obj.append({"role": role_gemini, "parts": [msg["content"]]})

    final_payload = []
    if media_content:
        final_payload.append("Te rog să analizezi acest document/imagine atașat:")
        final_payload.append(media_content)
    final_payload.append(user_input)

    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""
        
        try:
            stream_generator = run_chat_with_rotation(history_obj, final_payload)
            
            for text_chunk in stream_generator:
                full_response += text_chunk
                
                # În timp ce scrie, dacă detectăm începutul unui desen, arătăm un mesaj de așteptare
                if "[[DESEN_SVG]]" in full_response:
                     # Folosim Regex pentru a ascunde blocul de cod SVG în timpul generării
                     preview = full_response.replace("[[DESEN_SVG]]", "\n\n*🎨 Se desenează diagrama...*\n\n").replace("[[/DESEN_SVG]]", "")
                     preview = re.sub(r'\*🎨 Se desenează diagrama\...\*\n\n.*', '*🎨 Se desenează diagrama...*', preview, flags=re.DOTALL)
                     message_placeholder.markdown(preview + "▌")
                else:
                     message_placeholder.markdown(full_response + "▌")

            # Finalizare
            message_placeholder.empty()
            render_message_with_svg(full_response)

            st.session_state.messages.append({"role": "assistant", "content": full_response})
            save_message_to_db(st.session_state.session_id, "assistant", full_response)

            if enable_audio:
                with st.spinner("Generez vocea..."):
                    # Eliminăm desenul din audio
                    text_for_audio = re.sub(r'\[\[DESEN_SVG\]\].*?\[\[/DESEN_SVG\]\]', ' (Am desenat schema pe tablă) ', full_response, flags=re.DOTALL)
                    
                    clean_text = text_for_audio.replace("*", "").replace("$", "").replace("#", "")[:600]
                    
                    if clean_text.strip():
                        sound_file = BytesIO()
                        tts = gTTS(text=clean_text, lang='ro')
                        tts.write_to_fp(sound_file)
                        st.audio(sound_file, format='audio/mp3')

        except Exception as e:
            st.error(f"A apărut o eroare: {e}")
