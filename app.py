import streamlit as st
import base64
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage

# 1. Configurare Pagină
st.set_page_config(page_title="Profesorul de Mate AI (Vision)", page_icon="📸")
st.title("📸 Proful de Mate - Rezolvă din Poze")

# 2. Configurare API Key
if "GROQ_API_KEY" in st.secrets:
    api_key = st.secrets["GROQ_API_KEY"]
else:
    api_key = st.sidebar.text_input("Introdu cheia Groq API:", type="password")

if not api_key:
    st.warning("Te rog introdu cheia API sau configurează Secrets.")
    st.stop()

# 3. Inițializarea Modelului VISION
# IMPORTANT: Folosim modelul Llama 3.2 Vision Preview care "vede" imagini
try:
    llm = ChatGroq(
        temperature=0.3, 
        groq_api_key=api_key, 
        model_name="llama-3.2-11b-vision-preview" 
    )
except Exception as e:
    st.error(f"Eroare la conectare: {e}")
    st.stop()

# Funcție pentru transformarea imaginii în format text (Base64)
def encode_image(uploaded_file):
    return base64.b64encode(uploaded_file.getvalue()).decode('utf-8')

# 4. Bara Laterală pentru Upload
st.sidebar.header("Încarcă o problemă")
uploaded_file = st.sidebar.file_uploader("Pune o poză cu exercițiul (JPG/PNG)", type=["jpg", "jpeg", "png"])

# Afișarea imaginii în sidebar dacă există
image_data = None
if uploaded_file:
    st.sidebar.image(uploaded_file, caption="Imagine încărcată", use_container_width=True)
    image_data = encode_image(uploaded_file)

# 5. Istoricul chat-ului
if "messages" not in st.session_state:
    st.session_state["messages"] = [
        {"role": "assistant", "content": "Salut! Poți să îmi scrii problema sau să încarci o poză cu ea în meniul din stânga."}
    ]

for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])

# 6. Procesarea Inputului
user_input = st.chat_input("Întreabă ceva despre problemă...")

if user_input:
    # Afișăm mesajul utilizatorului
    st.session_state.messages.append({"role": "user", "content": user_input})
    st.chat_message("user").write(user_input)

    # Construim mesajul pentru AI
    messages_payload = []
    
    # Adăugăm instrucțiunile de profesor (System Prompt)
    system_prompt = """Ești un profesor de matematică expert. 
    1. Analizează cu atenție textul sau imaginea primită.
    2. Dacă e o imagine, extrage textul matematic din ea și rezolvă pas cu pas.
    3. Explică pedagogic, în limba română.
    4. Folosește LaTeX pentru formule matematice clare."""
    
    messages_payload.append(SystemMessage(content=system_prompt))

    # Construim mesajul utilizatorului (Text + Imagine dacă există)
    content_blocks = [{"type": "text", "text": user_input}]
    
    if image_data:
        # Adăugăm imaginea la mesaj doar dacă utilizatorul a încărcat una
        content_blocks.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{image_data}"}
        })
        st.info("Analizez imaginea încărcată... 🧠")
    
    messages_payload.append(HumanMessage(content=content_blocks))

    # Generăm răspunsul
    with st.chat_message("assistant"):
        try:
            response = llm.invoke(messages_payload)
            st.write(response.content)
            st.session_state.messages.append({"role": "assistant", "content": response.content})
        except Exception as e:
            st.error(f"A apărut o eroare: {e}")

    # Resetăm imaginea după ce a fost analizată (opțional, ca să nu o trimită la nesfârșit)
    # Dacă vrei să păstrezi imaginea pentru conversație continuă, șterge liniile de mai jos.
    # if image_data:
    #     st.sidebar.success("Imagine analizată!")
