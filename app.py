import streamlit as st
import google.generativeai as genai
from PIL import Image
import tempfile
from gtts import gTTS
from io import BytesIO # <--- NOU: Pentru audio în memorie

# 1. Configurare Pagină
st.set_page_config(page_title="Profesor Universal (Audio)", page_icon="🗣️")
st.title("🗣️ Profesor Universal")

# 2. Configurare API Key
if "GOOGLE_API_KEY" in st.secrets:
    api_key = st.secrets["GOOGLE_API_KEY"]
else:
    api_key = st.sidebar.text_input("Introdu Google API Key:", type="password")

if not api_key:
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
    st.error(f"Eroare model: {e}")
    st.stop()

# 3. Upload Multiplu
st.sidebar.header("📁 Materiale")
uploaded_files = st.sidebar.file_uploader("Încarcă fișiere", type=["jpg", "png", "pdf"], accept_multiple_files=True)
processed_files = []

if uploaded_files:
    for up_file in uploaded_files:
        if "image" in up_file.type:
            processed_files.append(Image.open(up_file))
            st.sidebar.image(up_file, caption=up_file.name)
        elif "pdf" in up_file.type:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                tmp.write(up_file.getvalue())
                path = tmp.name
            try:
                processed_files.append(genai.upload_file(path, mime_type="application/pdf"))
                st.sidebar.success(f"✅ {up_file.name}")
            except:
                st.sidebar.error("Eroare upload PDF")

# 4. Chat History
if "messages" not in st.session_state:
    st.session_state["messages"] = []

for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])

# 5. Input și Generare
if user_input := st.chat_input("Scrie ceva..."):
    st.session_state.messages.append({"role": "user", "content": user_input})
    st.chat_message("user").write(user_input)

    payload = []
    for msg in st.session_state.messages[:-1]:
        role = "model" if msg["role"] == "assistant" else "user"
        payload.append({"role": role, "parts": [msg["content"]]})
    
    current_parts = [user_input]
    if processed_files:
        current_parts.extend(processed_files)
    payload.append({"role": "user", "parts": current_parts})

    with st.chat_message("assistant"):
        with st.spinner("Scriu și pregătesc vocea..."):
            try:
                # Generare Text
                response = model.generate_content(payload)
                text = response.text
                st.write(text)
                st.session_state.messages.append({"role": "assistant", "content": text})

                # Generare Audio (Metoda Sigură cu BytesIO)
                if len(text) > 0:
                    try:
                        # Curățăm textul de simboluri care sună urât
                        clean_text = text.replace("*", "").replace("#", "").replace("$", "")
                        
                        # Creăm fișierul în memorie
                        sound_file = BytesIO()
                        tts = gTTS(text=clean_text, lang='ro')
                        tts.write_to_fp(sound_file)
                        
                        # Afișăm playerul
                        st.audio(sound_file, format='audio/mp3')
                        
                    except Exception as e_audio:
                        st.warning(f"Nu am putut genera vocea: {e_audio}")
            
            except Exception as e:
                st.error(f"Eroare: {e}")
