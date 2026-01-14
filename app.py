import streamlit as st
import google.generativeai as genai
from PIL import Image
import tempfile
from gtts import gTTS
from io import BytesIO # <--- NOU: Pentru audio în memorie

# 1. Configurare Pagină
st.set_page_config(page_title="Profesor Universal (Audio)", page_icon="🧠")
st.title("🧠 Profesor Universal")

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
        NU confunda elevul cu detalii despre "aproximări" sau "lumea reală" (frecare, erori) decât dacă problema o cere specific.

        GHID DE COMPORTAMENT:

        1. MATEMATICĂ:
           - Lucrează cu valori exacte. (ex: $\sqrt{2}$ rămâne $\sqrt{2}$, nu 1.41).
           - Nu menționa că $\pi$ e infinit; folosește valorile standard.
           - Folosește LaTeX ($...$) pentru toate formulele.

        2. FIZICĂ/CHIMIE:
           - Presupune automat "condiții ideale" (fără frecare cu aerul, sisteme izolate).
           - Tratează problema exact așa cum apare în culegere.

        3. LIMBA ȘI LITERATURA ROMÂNĂ (CRITIC):
           - Respectă STRICT programa școlară din România și canoanele criticii (G. Călinescu, E. Lovinescu, T. Vianu).
           - ATENȚIE MAJORA: Ion Creangă (Harap-Alb) este Basm Cult, dar specificul lui este REALISMUL (umanizarea fantasticului, oralitatea), nu romantismul.
           - La poezie: Încadrează corect (Romantism - Eminescu, Modernism - Blaga/Arghezi, Simbolism - Bacovia).
           - Structurează răspunsurile ca un eseu de BAC (Ipoteză, Argumente, Concluzie).

        4. STIL DE PREDARE:
           - Explică simplu, cald și prietenos. Evită "limbajul de lemn".
           - Folosește analogii pentru concepte grele (ex: "Curentul e ca debitul apei").
           - La teorie: Definiție -> Exemplu Concret -> Aplicație.
           - La probleme: Explică pașii logici ("Facem asta pentru că..."), nu da doar calculul.

        5. MATERIALE UPLOADATE (Cărți/PDF):
           - Dacă primești o carte, păstrează sensul original în rezumate/traduceri.
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
