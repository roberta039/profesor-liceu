import streamlit as st
import google.generativeai as genai
from PIL import Image

# 1. Configurare Pagină
st.set_page_config(page_title="Profesorul de Mate AI", page_icon="📐")
st.title("📐 Proful de Mate")

# 2. Configurare API Key
if "GOOGLE_API_KEY" in st.secrets:
    api_key = st.secrets["GOOGLE_API_KEY"]
else:
    api_key = st.sidebar.text_input("Introdu Google API Key:", type="password")

if not api_key:
    st.stop()

genai.configure(api_key=api_key)

# 3. Modelul (Setat direct pe cel care merge)
model = genai.GenerativeModel(
    "gemini-1.5-flash",
    system_instruction="""Ești un profesor de matematică prietenos și expert.
    1. Analizează imaginea sau textul primit.
    2. Dacă e o problemă, rezolv-o pas cu pas.
    3. Explică logica clar, în limba română.
    4. Folosește LaTeX pentru formule ($formula$)."""
)

# 4. Upload Poză (Simplificat)
with st.sidebar:
    st.header("📸 Adaugă Problemă")
    uploaded_file = st.file_uploader("Încarcă o poză", type=["jpg", "jpeg", "png"])
    img = None
    if uploaded_file:
        img = Image.open(uploaded_file)
        st.image(img, caption="Imagine încărcată", use_container_width=True)
        st.success("Imagine gata de trimis!")

# 5. Chat History
if "messages" not in st.session_state:
    st.session_state["messages"] = [{"role": "assistant", "content": "Salut! Arată-mi problema și o rezolvăm împreună."}]

for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])

# 6. Chat Input
if user_input := st.chat_input("Scrie aici..."):
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
