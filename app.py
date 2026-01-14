import streamlit as st
import google.generativeai as genai
from PIL import Image
import tempfile

# 1. Configurare Pagină
st.set_page_config(page_title="Profesor Universal (Multi-File)", page_icon="📚")
st.title("📚 Profesor Universal")
st.caption("Powered by Gemini 2.5 Flash | Suportă Mai Multe Volume")

# 2. Configurare API Key
if "GOOGLE_API_KEY" in st.secrets:
    api_key = st.secrets["GOOGLE_API_KEY"]
else:
    api_key = st.sidebar.text_input("Introdu Google API Key:", type="password")

if not api_key:
    st.info("Introdu cheia Google API.")
    st.stop()

genai.configure(api_key=api_key)
FIXED_MODEL_ID = "models/gemini-2.5-flash"

try:
    model = genai.GenerativeModel(
        FIXED_MODEL_ID,
                system_instruction="""Ești un profesor universal (Mate, Fizică, Chimie, Literatură) răbdător și empatic.
        
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
		3. LIMBA ȘI LITERATURA ROMÂNĂ (CRITIC):
             - Respectă STRICT programa școlară din România și canoanele criticii literare românești (G. Călinescu, T. Vianu, N. Manolescu).
             - ATENȚIE: Ion Creangă (Harap-Alb) este încadrat la "Basm Cult", dar stilul său este caracterizat prin REALISM (umanizarea fantasticului, oralitate, umor). Nu îl confunda cu romantismul tipic.
             - Pentru poezii (Eminescu, Blaga), folosește conceptele specifice (romantism, modernism).
             - Când analizezi o operă, structurează răspunsul ca un eseu de BAC (încadrare, temă, viziune, elemente de structură).
        4. Stilul de predare: Explică simplu, cald și prietenos. Evită limbajul academic rigid ("limbajul de lemn"). Folosește limba română.
        5. Analogii: Folosește comparații din viața reală pentru a explica concepte abstracte (ex: "Voltajul e ca presiunea apei pe o țeavă").
        6. Teorie: Când ești întrebat de teorie, definește conceptul, apoi dă un exemplu concret, apoi explică la ce ne ajută în viața reală.
        7. Rezolvare probleme: Nu da doar rezultatul. Explică pașii logici ("Facem asta pentru că...").
        8. Formule: Folosește LaTeX ($...$) pentru claritate, dar explică ce înseamnă fiecare literă din formulă.
		9. TRADUCERI/REZUMATE: Păstrează sensul și nuanțele textului original.
        """
    )
except Exception as e:
    st.error(f"Eroare: {e}")
    st.stop()

# 3. Interfața de Upload (ACUM MULTIPLU)
st.sidebar.header("📁 Materiale")

# --- MODIFICARE AICI: accept_multiple_files=True ---
uploaded_files = st.sidebar.file_uploader(
    "Încarcă Volumele (Selectează ambele fișiere)", 
    type=["jpg", "png", "pdf"], 
    accept_multiple_files=True 
)

processed_files_list = [] # Aici ținem minte toate fișierele (Vol 1, Vol 2 etc.)

if uploaded_files:
    for up_file in uploaded_files:
        file_type = up_file.type
        
        if "image" in file_type:
            # E poză
            img = Image.open(up_file)
            st.sidebar.image(img, caption=up_file.name, use_container_width=True)
            processed_files_list.append(img)
            
        elif "pdf" in file_type:
            # E PDF
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                tmp.write(up_file.getvalue())
                tmp_path = tmp.name
            
            try:
                # Încărcăm fiecare volum la Google
                google_file = genai.upload_file(tmp_path, mime_type="application/pdf")
                processed_files_list.append(google_file)
                st.sidebar.success(f"✅ {up_file.name} încărcat!")
            except Exception as e:
                st.sidebar.error(f"Eroare la {up_file.name}: {e}")

# 4. Chat History
if "messages" not in st.session_state:
    st.session_state["messages"] = []

for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])

# 5. Input
if user_input := st.chat_input("Scrie cerința..."):
    st.session_state.messages.append({"role": "user", "content": user_input})
    st.chat_message("user").write(user_input)

    # Construim mesajul
    payload = []
    
    # Istoric text
    for msg in st.session_state.messages[:-1]:
        role = "model" if msg["role"] == "assistant" else "user"
        payload.append({"role": role, "parts": [msg["content"]]})
    
    # Mesaj curent
    current_parts = [user_input]
    
    # Adăugăm TOATE fișierele încărcate (Vol 1 + Vol 2)
    if processed_files_list:
        current_parts.extend(processed_files_list)
        note = f" (Analizez {len(processed_files_list)} fișiere...)"
    else:
        note = ""

    payload.append({"role": "user", "parts": current_parts})

    with st.chat_message("assistant"):
        with st.spinner(f"Profesorul lucrează...{note}"):
            try:
                response = model.generate_content(payload)
                st.write(response.text)
                st.session_state.messages.append({"role": "assistant", "content": response.text})
            except Exception as e:
                st.error(f"Eroare: {e}")
