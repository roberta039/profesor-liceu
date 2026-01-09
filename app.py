import streamlit as st
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

# 1. Configurare Pagină
st.set_page_config(page_title="Profesorul de Mate AI", page_icon="🧮")
st.title("🧮 Proful de Mate (Llama 3)")

# 2. Bara laterală pentru API Key (ca să fie sigur)
st.sidebar.header("Configurare")
api_key = st.sidebar.text_input("Introdu cheia Groq API:", type="password")
st.sidebar.info("Obține cheia gratuit de la console.groq.com")

if not api_key:
    st.warning("Te rog introdu cheia API în meniul din stânga pentru a începe.")
    st.stop()

# 3. Inițializarea Modelului (Llama 3 prin Groq)
try:
    llm = ChatGroq(temperature=0.3, groq_api_key=api_key, model_name="llama3-8b-8192")
except Exception as e:
    st.error(f"Eroare la conectare: {e}")
    st.stop()

# 4. Definirea Personalității Agentului (Prompt)
# Aici îi spunem să se comporte ca un profesor, nu ca un calculator simplu.
system_prompt = """Ești un profesor de matematică prietenos și răbdător. 
Obiectivul tău este să ajuți elevul să înțeleagă conceptul, nu doar să îi dai rezultatul.
Reguli:
1. Dacă elevul întreabă o problemă, explică pașii logici.
2. Folosește analogii simple.
3. Dacă este o ecuație complexă, descompune-o pas cu pas.
4. Răspunde în limba română.
5. Folosește formatare Markdown (bold, liste) pentru claritate.
"""

prompt = ChatPromptTemplate.from_messages([
    ("system", system_prompt),
    ("user", "{question}")
])

chain = prompt | llm | StrOutputParser()

# 5. Interfața de Chat
if "messages" not in st.session_state:
    st.session_state["messages"] = [{"role": "assistant", "content": "Salut! Sunt gata să rezolvăm probleme la mate. Cu ce te ajut azi?"}]

# Afișarea istoricului
for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])

# Căsuța de input
if user_input := st.chat_input("Scrie problema aici..."):
    # Adaugă mesajul utilizatorului
    st.session_state.messages.append({"role": "user", "content": user_input})
    st.chat_message("user").write(user_input)

    # Generează răspunsul
    with st.chat_message("assistant"):
        response = chain.invoke({"question": user_input})
        st.write(response)
    
    # Salvează răspunsul
    st.session_state.messages.append({"role": "assistant", "content": response})
