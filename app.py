import streamlit as st
import google.generativeai as genai
from PIL import Image
import tempfile # Avem nevoie de asta pentru a manipula PDF-urile temporar

# 1. Configurare Pagină
st.set_page_config(page_title="Profesor Universal (PDF & Vision)", page_icon="📚")
st.title("📚 Profesor Universal")
st.caption("Powered by Gemini 2.5 Flash | Analiză Cărți (PDF) & Probleme (Foto)")

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
    st.error(f"Eroare critică: {e}")
    st.stop()

# 3. Interfața de Upload (Modificată pentru PDF)
st.sidebar.header("📁 Materiale")
# Acum acceptăm și PDF
uploaded_file = st.sidebar.file_uploader("Încarcă Poză sau PDF", type=["jpg", "jpeg", "png", "pdf"])

media_content = None # Aici vom stoca fișierul procesat (Poză sau PDF)
file_type = ""

if uploaded_file:
    file_type = uploaded_file.type
    
    if "image" in file_type:
        # Procesare Imagine
        media_content = Image.open(uploaded_file)
        st.sidebar.image(media_content, caption="Imagine încărcată", use_container_width=True)
        
    elif "pdf" in file_type:
        # Procesare PDF (Mai complex)
        st.sidebar.info("📄 PDF Detectat. Se procesează...")
        
        # 1. Salvăm PDF-ul într-un fișier temporar pe disc
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(uploaded_file.getvalue())
            tmp_path = tmp.name
        
        # 2. Încărcăm fișierul pe serverele Google (File API)
        try:
            with st.spinner("Urc cartea în biblioteca digitală Google..."):
                uploaded_pdf = genai.upload_file(tmp_path, mime_type="application/pdf")
                media_content = uploaded_pdf # Acesta este obiectul pe care îl trimitem la AI
                st.sidebar.success(f"✅ Carte încărcată! ({uploaded_file.name})")
        except Exception as e:
            st.sidebar.error(f"Eroare la upload PDF: {e}")

# 4. Chat History
if "messages" not in st.session_state:
    st.session_state["messages"] = []

for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])

# 5. Input și Logică
if user_input := st.chat_input("Scrie cerința (ex: 'Fă rezumatul cărții')..."):
    st.session_state.messages.append({"role": "user", "content": user_input})
    st.chat_message("user").write(user_input)

    # --- CONSTRUIREA MESAJULUI ---
    conversation_payload = []

    # A. Istoric text (context)
    for msg in st.session_state.messages[:-1]:
        role = "model" if msg["role"] == "assistant" else "user"
        conversation_payload.append({
            "role": role,
            "parts": [msg["content"]]
        })

    # B. Mesajul curent + Fișierul (dacă există)
    current_parts = [user_input]
    
    if media_content:
        # Verificăm dacă e Poză sau PDF (Google File)
        current_parts.append(media_content)
        
        if "pdf" in file_type:
            display_note = " (Analizez PDF-ul...)"
        else:
            display_note = " (Analizez imaginea...)"
    else:
        display_note = ""

    conversation_payload.append({
        "role": "user",
        "parts": current_parts
    })

    # C. Trimitere
    with st.chat_message("assistant"):
        with st.spinner(f"Profesorul lucrează...{display_note}"):
            try:
                response = model.generate_content(conversation_payload)
                st.write(response.text)
                st.session_state.messages.append({"role": "assistant", "content": response.text})
            except Exception as e:
                st.error(f"Eroare: {e}")
