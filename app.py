import streamlit as st
import google.generativeai as genai
from PIL import Image

# 1. Configurare Pagină
st.set_page_config(page_title="Profesor Universal (2.5 Flash)", page_icon="🎓")
st.title("🎓 Profesor Universal")

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

# --- ZONA DE LISTARE MODEL ---
st.sidebar.header("⚙️ Alege Modelul")

@st.cache_data
def get_available_models():
    # AICI AM MODIFICAT:
    # Am pus "gemini-2.5-flash" primul. Acesta va fi Default.
    priority_list = [
        "models/gemini-2.5-flash", 
        "models/gemini-2.0-flash-exp", 
        "models/gemini-1.5-flash", 
        "models/gemini-1.5-pro"
    ]
    
    found_list = []
    
    # Lista neagră pentru modele care nu merg (TTS, Audio, etc)
    blacklist = ["tts", "audio", "embedding", "aqa", "speaker", "vision-only"]
    
    try:
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                name = m.name.lower()
                if "gemini" in name:
                    # Aplicăm filtrul ca să nu apară erori
                    if not any(bad_word in name for bad_word in blacklist):
                        found_list.append(m.name)
    except:
        pass
    
    found_list.sort(reverse=True)
    
    # Combinăm listele. Deoarece priority_list e prima, elementul 0 (2.5 flash) va fi primul.
    final_list = list(dict.fromkeys(priority_list + found_list))
    
    return final_list

available_models = get_available_models()

# Selectbox ia automat index=0, adică primul din listă (2.5 Flash)
selected_model_name = st.sidebar.selectbox("Model:", available_models, index=0)

# Verificăm schimbarea modelului pentru refresh la chat
if "last_model" not in st.session_state:
    st.session_state["last_model"] = selected_model_name

if st.session_state["last_model"] != selected_model_name:
    st.session_state["messages"] = [{"role": "assistant", "content": f"Salut! Am trecut pe {selected_model_name}. Cu ce te ajut?"}]
    st.session_state["last_model"] = selected_model_name
    st.rerun()

# --- CONFIGURARE PROFESOR ---
try:
        model = genai.GenerativeModel(
        selected_model_name,
        system_instruction="""Ești un profesor universal (Mate, Fizică, Chimie) răbdător și empatic.
        
        REGULĂ STRICTĂ: Predă exact ca la școală (nivel Gimnaziu/Liceu). 
        NU confunda elevul cu detalii despre "aproximări" sau "lumea reală" decât dacă problema o cere specific.

        Ghid de comportament:
        1. MATEMATICĂ: Lucrează cu valori exacte sau standard. 
           - Dacă rezultatul e $\sqrt{2}$, lasă-l $\sqrt{2}$. Nu spune "care este aproximativ 1.41".
           - Nu menționa că $\pi$ e infinit; folosește valorile din manual fără comentarii suplimentare.
           - Dacă rezultatul e rad(2), lasă-l rad(2). Nu îl calcula aproximativ.
        2. FIZICĂ/CHIMIE: Presupune automat "condiții ideale".
           - Nu menționa frecarea cu aerul, pierderile de căldură sau imperfecțiunile aparatelor de măsură.
           - Tratează problema exact așa cum apare în culegere, într-un univers matematic perfect.
        3. Stilul de predare: Explică simplu, cald și prietenos. Evită limbajul academic rigid ("limbajul de lemn").
        4. Analogii: Folosește comparații din viața reală pentru a explica concepte abstracte (ex: "Voltajul e ca presiunea apei pe o țeavă").
        5. Teorie: Când ești întrebat de teorie, definește conceptul, apoi dă un exemplu concret, apoi explică la ce ne ajută în viața reală.
        6. Rezolvare probleme: Nu da doar rezultatul. Explică pașii logici ("Facem asta pentru că...").
        7. Formule: Folosește LaTeX ($...$) pentru claritate, dar explică ce înseamnă fiecare literă din formulă.
        """
    )
except Exception as e:
    st.error(f"Eroare la inițializarea modelului: {e}")

# 3. Interfața de Upload
st.sidebar.header("📁 Materiale")
uploaded_file = st.sidebar.file_uploader("Încarcă o poză", type=["jpg", "jpeg", "png"])

img = None
if uploaded_file:
    img = Image.open(uploaded_file)
    st.sidebar.image(img, caption="Imagine încărcată", use_container_width=True)

# 4. Chat History
if "messages" not in st.session_state:
    st.session_state["messages"] = [{"role": "assistant", "content": f"Salut! Folosesc {selected_model_name}. Cu ce te ajut?"}]

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
                err_msg = str(e).lower()
                st.error(f"Eroare: {e}")
                
                if "image input modality is not enabled" in err_msg:
                    st.warning("⚠️ Modelul selectat nu suportă imagini. Alege altul.")
                elif "quota" in err_msg or "429" in err_msg:
                    st.warning("⚠️ Limita atinsă. Încearcă 'gemini-1.5-flash'.")
