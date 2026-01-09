import streamlit as st
import google.generativeai as genai
from PIL import Image

# 1. Configurare Pagină
st.set_page_config(page_title="Profesorul de Mate (Universal)", page_icon="🎓")
st.title("🎓 Proful de Mate - Selector Modele")

# 2. Configurare API Key
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
except Exception as e:
    st.error(f"Eroare la configurare cheie: {e}")
    st.stop()

# --- ZONA DE DEBUGGING (Găsirea modelelor) ---
st.sidebar.header("⚙️ Setări Model")

@st.cache_data # Salvăm lista ca să nu o cerem la fiecare click
def get_available_models():
    try:
        model_list = []
        for m in genai.list_models():
            # Căutăm modele care suportă generare de conținut
            if 'generateContent' in m.supported_generation_methods:
                model_list.append(m.name)
        return model_list
    except Exception as e:
        st.sidebar.error(f"Nu pot lista modelele: {e}")
        return ["models/gemini-1.5-flash"] # Fallback

available_models = get_available_models()
selected_model_name = st.sidebar.selectbox("Alege Modelul:", available_models, index=0)

# Inițializăm modelul ales
try:
    model = genai.GenerativeModel(
        selected_model_name,
        system_instruction="""Ești un profesor de matematică expert. 
        Rezolvă problemele pas cu pas. Explică clar în limba română. 
        Folosește LaTeX pentru formule."""
    )
except Exception as e:
    st.error(f"Eroare la inițializarea modelului {selected_model_name}: {e}")

# 3. Interfața de Upload
st.sidebar.header("📁 Materiale")
uploaded_file = st.sidebar.file_uploader("Încarcă o poză", type=["jpg", "jpeg", "png"])

img = None
if uploaded_file:
    img = Image.open(uploaded_file)
    st.sidebar.image(img, caption="Imagine încărcată", use_container_width=True)

# 4. Chat History
if "messages" not in st.session_state:
    st.session_state["messages"] = [{"role": "assistant", "content": f"Salut! Folosesc modelul {selected_model_name}. Cu ce te ajut?"}]

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
                st.info("Sfat: Încearcă să selectezi alt model din meniul din stânga.")
