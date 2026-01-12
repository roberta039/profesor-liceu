import streamlit as st
import google.generativeai as genai
from PIL import Image

# 1. Configurare Pagină
st.set_page_config(page_title="Profesor Universal (Filtered)", page_icon="🎓")
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

# --- ZONA DE LISTARE INTELIGENTĂ CU FILTRE ---
st.sidebar.header("⚙️ Alege Modelul")

@st.cache_data
def get_available_models():
    # 1. Lista modelelor sigure care știm că VĂD poze
    priority_list = ["models/gemini-2.0-flash-exp", "models/gemini-1.5-flash", "models/gemini-1.5-pro"]
    found_list = []
    
    # Cuvinte interzise (modele care nu ne trebuie la Mate)
    blacklist = ["tts", "audio", "embedding", "aqa", "speaker", "vision-only"]
    
    try:
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                name = m.name.lower()
                # Verificăm să fie Gemini
                if "gemini" in name:
                    # Verificăm să NU fie în lista neagră
                    if not any(bad_word in name for bad_word in blacklist):
                        found_list.append(m.name)
    except:
        pass
    
    found_list.sort(reverse=True)
    # Eliminăm duplicatele și punem prioritarele primele
    final_list = list(dict.fromkeys(priority_list + found_list))
    
    return final_list

available_models = get_available_models()

# Selectorul Manual
selected_model_name = st.sidebar.selectbox("Model:", available_models, index=0)

# Verificăm schimbarea modelului pentru refresh
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
        1. MATEMATICĂ: Lucrează cu valori exacte. (ex: sqrt(2) rămâne sqrt(2)).
        2. FIZICĂ/CHIMIE: Condiții ideale (fără frecare).
        3. EXPLICATII: Pas cu pas, simplu, cu LaTeX ($...$) pentru formule.
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
                # Tratarea erorilor specifice
                err_msg = str(e).lower()
                st.error(f"Eroare: {e}")
                
                if "image input modality is not enabled" in err_msg:
                    st.warning("⚠️ Modelul selectat este 'ORB' (nu suportă imagini). Te rog selectează un model 'Flash' sau 'Pro' din listă.")
                elif "quota" in err_msg or "429" in err_msg:
                    st.warning("⚠️ Limita gratuită atinsă pentru acest model. Schimbă pe 'gemini-1.5-flash'.")
