import streamlit as st
import google.generativeai as genai
from PIL import Image

# 1. Configurare Pagină
st.set_page_config(page_title="Profesor Universal (Contextual)", page_icon="🧠")
st.title("🧠 Profesor Universal")
st.caption("Powered by Gemini 2.5 Flash | Memorie Text + Focus Vizual")

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

# --- INITIALIZARE MODEL ---
FIXED_MODEL_ID = "models/gemini-2.5-flash"

try:
    model = genai.GenerativeModel(
        FIXED_MODEL_ID,
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
    st.error(f"Eroare critică: {e}")
    st.stop()

# 3. Interfața de Upload
st.sidebar.header("📁 Materiale")
uploaded_file = st.sidebar.file_uploader("Încarcă o poză (Doar pentru întrebarea curentă)", type=["jpg", "jpeg", "png"])

img = None
if uploaded_file:
    img = Image.open(uploaded_file)
    st.sidebar.image(img, caption="Imagine de analizat", use_container_width=True)

# 4. Chat History (UI)
if "messages" not in st.session_state:
    st.session_state["messages"] = []

# Afișăm conversația pe ecran
for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])

# 5. Input și Logica de Construire a Istoricului
if user_input := st.chat_input("Scrie problema..."):
    # A. Afișăm mesajul utilizatorului în UI
    st.session_state.messages.append({"role": "user", "content": user_input})
    st.chat_message("user").write(user_input)

    # B. CONSTRUIM ISTORICUL PENTRU MODEL (The Smart Part)
    # Vom crea o listă 'contents' pe care o trimitem la Google.
    conversation_payload = []

    # 1. Adăugăm mesajele VECHI (Doar text, pentru context)
    # Ignorăm ultimul mesaj adăugat acum, pentru că îl procesăm special cu poza
    for msg in st.session_state.messages[:-1]:
        # Convertim rolurile: "assistant" -> "model", "user" -> "user"
        role = "model" if msg["role"] == "assistant" else "user"
        conversation_payload.append({
            "role": role,
            "parts": [msg["content"]]
        })

    # 2. Adăugăm mesajul CURENT (Text + Imagine dacă există)
    current_parts = [user_input]
    if img:
        current_parts.append(img) # Aici atașăm imaginea DOAR acum
    
    conversation_payload.append({
        "role": "user",
        "parts": current_parts
    })

    # C. Trimitem tot pachetul la Model
    with st.chat_message("assistant"):
        with st.spinner("Gândesc..."):
            try:
                # generate_content acceptă o listă de mesaje pentru chat history
                response = model.generate_content(conversation_payload)
                
                # Afișăm și salvăm răspunsul
                st.write(response.text)
                st.session_state.messages.append({"role": "assistant", "content": response.text})
            except Exception as e:
                st.error(f"Eroare: {e}")
