import streamlit as st
import base64
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage

# 1. Configurare Pagină
st.set_page_config(page_title="Profesorul de Mate AI", page_icon="📐")
st.title("📐 Proful de Mate - Rezolvă din Poze")

# 2. Configurare API Key
# Întâi caută în secretele Streamlit, dacă nu, cere în sidebar
if "GROQ_API_KEY" in st.secrets:
    api_key = st.secrets["GROQ_API_KEY"]
else:
    api_key = st.sidebar.text_input("Introdu cheia Groq API:", type="password")

if not api_key:
    st.info("Te rog introdu cheia API în meniul din stânga pentru a începe.")
    st.stop()

# 3. Inițializarea Modelului VISION (ACTUALIZAT)
# Folosim modelul 90b care este activ și foarte bun la logică vizuală
try:
    llm = ChatGroq(
        temperature=0.1,  # Temperatură mică pentru precizie la mate
        groq_api_key=api_key, 
        model_name="llama-3.2-90b-vision-preview" 
    )
except Exception as e:
    st.error(f"Eroare la conectare: {e}")
    st.stop()

# Funcție pentru a transforma imaginea în text (Base64) pentru AI
def encode_image(uploaded_file):
    return base64.b64encode(uploaded_file.getvalue()).decode('utf-8')

# 4. Bara Laterală pentru Upload
st.sidebar.header("Ai o problemă în caiet?")
uploaded_file = st.sidebar.file_uploader("Încarcă o poză (JPG/PNG)", type=["jpg", "jpeg", "png"])

image_data = None
if uploaded_file:
    # Afișăm imaginea mică în stânga
    st.sidebar.image(uploaded_file, caption="Imaginea ta", use_container_width=True)
    # O procesăm pentru AI
    image_data = encode_image(uploaded_file)
    st.sidebar.success("Imagine încărcată cu succes! Acum întreabă ceva.")

# 5. Istoricul chat-ului
if "messages" not in st.session_state:
    st.session_state["messages"] = [
        {"role": "assistant", "content": "Salut! Sunt profesorul tău de matematică. Poți să-mi scrii o problemă sau să încarci o poză cu ea și te ajut să o rezolvi pas cu pas."}
    ]

# Afișăm mesajele anterioare
for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])

# 6. Procesarea Inputului Utilizatorului
user_input = st.chat_input("Scrie aici (ex: 'Rezolvă exercițiul din poză')...")

if user_input:
    # 1. Afișăm ce a scris utilizatorul
    st.session_state.messages.append({"role": "user", "content": user_input})
    st.chat_message("user").write(user_input)

    # 2. Pregătim instrucțiunile pentru Profesor (System Prompt)
    system_prompt = """Ești un profesor de matematică expert, răbdător și pedagogic.
    
    REGULI:
    1. Dacă primești o imagine, transcrie mental problema și rezolv-o.
    2. Nu da doar răspunsul final. Explică logica pas cu pas.
    3. Folosește limba română.
    4. Dacă poza este neclară, spune-i elevului să mai facă una.
    5. Folosește formatare clară (Markdown) și LaTeX pentru formule matematice (încadrate de $).
    """

    # 3. Construim pachetul de mesaje pentru AI
    messages_payload = [SystemMessage(content=system_prompt)]
    
    # Construim mesajul utilizatorului (Text + Imagine Opțională)
    content_blocks = [{"type": "text", "text": user_input}]
    
    if image_data:
        content_blocks.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{image_data}"}
        })
        # Notificare discretă că se uită la poză
        with st.spinner("Mă uit la poză și calculez..."):
            pass
    
    messages_payload.append(HumanMessage(content=content_blocks))

    # 4. Generăm răspunsul
    with st.chat_message("assistant"):
        try:
            response = llm.invoke(messages_payload)
            st.write(response.content)
            # Salvăm răspunsul în istoric
            st.session_state.messages.append({"role": "assistant", "content": response.content})
        except Exception as e:
            st.error(f"Eroare la generare: {e}")
            # Dacă modelul crapă iar, afișăm un mesaj util
            if "model_decommissioned" in str(e):
                st.warning("Modelul AI a fost actualizat de Groq. Verifică app.py pentru noul nume.")
