import streamlit as st
import google.generativeai as genai
from PIL import Image

# 1. Configurare Pagină
st.set_page_config(page_title="Profesor Universal (Auto)", page_icon="🧠")
st.title("🧠 Profesor Universal (Auto-Pilot)")

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
    # Dăm note modelelor. Scorul mare câștigă.
    score = 0
    name = model_name.lower()
    
    # 1. Punctaj Versiune
    if "3" in name: score += 30000
    elif "2.5" in name: score += 25000
    elif "2.0" in name: score += 20000
    elif "1.5" in name: score += 15000
    
    # 2. Punctaj Capacitate
    if "deep think" in name: score += 5000
    if "ultra" in name: score += 4000
    if "pro" in name: score += 3000
    if "flash" in name: score += 1000
    
    # Penalizăm preview-urile dacă există varianta stabilă, dar le păstrăm dacă sunt singurele
    if "preview" in name: score -= 1 
    
    return score

def get_best_model_smart():
    try:
        all_models = []
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                if "gemini" in m.name and "embedding" not in m.name and "aqa" not in m.name:
                    all_models.append(m.name)
        
        # Sortăm după SCOR
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

# Logica de sărbătoare
if "gemini-3" in best_model_name:
    st.sidebar.balloons()
    st.toast("🎉 Gemini 3 este activ!")

# --- INITIALIZARE MODEL ---
try:
    # AICI ERA EROAREA: Acum folosim 'best_model_name' corect
    model = genai.GenerativeModel(
        best_model_name,
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
    # Actualizăm mesajul de salut cu numele noului model
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
