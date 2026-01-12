import streamlit as st
import google.generativeai as genai
from PIL import Image
import re

# 1. Configurare Pagină
st.set_page_config(page_title="Profesor Universal (AI 3.0 Ready)", page_icon="🧠")
st.title("🧠 Profesor Universal (Logic Sort)")

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

# --- ALGORITMUL DE SELECTIE INTELIGENTĂ ---
def calculate_model_score(model_name):
    # Această funcție dă o notă fiecărui model.
    # Cu cât scorul e mai mare, cu atât modelul e mai bun.
    score = 0
    name = model_name.lower()
    
    # 1. PUNCTAJ PENTRU VERSIUNE (3.0 > 2.5 > 2.0 > 1.5)
    if "3" in name: score += 30000
    elif "2.5" in name: score += 25000
    elif "2.0" in name: score += 20000
    elif "1.5" in name: score += 15000
    
    # 2. PUNCTAJ PENTRU CAPACITATE
    if "deep think" in name: score += 5000    # Cel mai deștept
    if "ultra" in name: score += 4000
    if "pro" in name: score += 3000           # Standardul Gold
    if "flash" in name: score += 1000         # Rapid
    if "lite" in name: score += 500
    if "nano" in name: score += 100
    if "preview" in name: score -= 1          # Preferăm versiunile stabile
    
    return score

def get_best_model_smart():
    try:
        all_models = []
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                if "gemini" in m.name and "embedding" not in m.name and "aqa" not in m.name:
                    all_models.append(m.name)
        
        # Sortăm modelele în funcție de SCORUL calculat
        all_models.sort(key=calculate_model_score, reverse=True)
        
        if all_models:
            return all_models[0]
        else:
            return "models/gemini-1.5-flash"
            
    except Exception as e:
        return "models/gemini-1.5-flash"

# Aflăm campionul
best_model_name = get_best_model_smart()

# Afișăm statusul
st.sidebar.header("🤖 Status")
st.sidebar.success(f"Model selectat:\n**{best_model_name}**")

# Logica de sărbătoare pentru viitor
if "gemini-3" in best_model_name:
    st.sidebar.balloons()
    st.toast("🎉 WOW! Gemini 3 este activ!")
elif "deep think" in best_model_name:
    st.toast("🧠 Modul Deep Think activat!")

# --- INITIALIZARE MODEL ---
try:
    model = genai.GenerativeModel(
        best_model_name,
        system_instruction="""Ești un profesor universal (Mate, Fizică, Chimie) răbdător și empatic.
        
        REGULĂ STRICTĂ: Predă exact ca la școală (nivel Gimnaziu/Liceu). 
        NU confunda elevul cu detalii despre "aproximări" sau "lumea reală" decât dacă problema o cere specific.

        Ghid de comportament:
        1. MATEMATICĂ: Lucrează cu valori exacte sau standard. 
           - Dacă rezultatul e rad(2), lasă-l rad(2). Nu îl calcula aproximativ.
        2. FIZICĂ/CHIMIE: Presupune automat "condiții ideale".
        3. EXPLICATII: Explică pas cu pas, simplu, folosind LaTeX ($...$) pentru formule.
        """
    )
except Exception as e:
    st.error(f"Eroare la inițializarea modelului {best_model_name}: {e}")

# 3. Interfața de Upload
st.sidebar.header("📁 Materiale")
uploaded_file = st.sidebar.file_uploader("Încarcă o poză", type=["jpg", "jpeg", "png"])

img = None
if uploaded_file:
    img = Image.open(uploaded_file)
    st.sidebar.image(img, caption="Imagine încărcată", use_container_width=True)

# 4. Chat History
if "messages" not in st.session_state:
    st.session_state["messages"] = [{"role": "assistant", "content": f"Salut! Sunt conectat la {best_model_name}. Cu ce te ajut?"}]

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
