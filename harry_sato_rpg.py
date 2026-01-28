import os
import streamlit as st
from openai import OpenAI
import re

# ----------------------------
# 1. Configurações de Motor
# ----------------------------
MODEL = "gpt-4o-mini"
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

if "blackboard" not in st.session_state:
    st.session_state.blackboard = {
        "suspicion": 0.1,
        "mood": "NEUTRAL",      
        "deal_state": "IDLE",   
        "history": []
    }

# ----------------------------
# 2. Sensor de Intenção Contextual
# ----------------------------
def analyze_context(user_text):
    bb = st.session_state.blackboard
    text = user_text.lower()

    # Detecção de Hostilidade e Ameaça de Autoridade (Ajuste v3.1)
    perigo = ["chupa", "idiota", "burro", "polícia", "prender", "id", "identidade", "cop", "denunciar"]
    if any(x in text for x in perigo):
        bb["suspicion"] = min(1.0, bb["suspicion"] + 0.5)
        bb["mood"] = "AGGRESSIVE"
        return "HOSTILE"

    prompt = (
        "Classifique a intenção (BUY, PROBE, TECH, CHAT) "
        f"e a urgência (HIGH, LOW) do usuário: '{user_text}'"
    )

    resp = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        max_tokens=15
    )

    return resp.choices[0].message.content.strip().upper()

# ----------------------------
# 3. Behavior Tree (Lógica de Decisão)
# ----------------------------
def tick_behavior_tree(intent_data):
    bb = st.session_state.blackboard

    if bb["suspicion"] > 0.75:
        bb["deal_state"] = "BURNED"
        return "ESTADO: QUEIMADO. Harry detectou perigo real. Encerrar conexão."

    if "BUY" in intent_data:
        bb["deal_state"] = "NEGOTIATING"
        bb["mood"] = "GREEDY"
        return "ESTADO: NEGOCIAÇÃO. Preço: 200 dólares. Finalizar com 'NEGÓCIO FECHADO'."

    if "PROBE" in intent_data:
        bb["mood"] = "TENSE"
        return "ESTADO: SONDAGEM. Rispidez e enigmas."

    return "ESTADO: FLAVOR. Comente a decadência de NYCS."

# ----------------------------
# 4. Atuador de Voz (Persona)
# ----------------------------
def harry_speaks(user_input):
    bb = st.session_state.blackboard
    intent_info = analyze_context(user_input)
    node_instruction = tick_behavior_tree(intent_info)

    system_prompt = f"""
Você é Harry Sato, um traficante cínico em Roosevelt Island.
ESTILO: Máx. 2 frases curtas. Rua, ríspido.
REGRAS: Proibido metáforas poéticas ou samurais.
ESTADO: {node_instruction}
PARANOIA: {bb['suspicion']:.2f} | HUMOR: {bb['mood']}
"""
    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(bb["history"][-4:])
    messages.append({"role": "user", "content": user_input})

    response = client.chat.completions.create(model=MODEL, messages=messages, temperature=0.6)
    answer = response.choices[0].message.content

    if any(x in answer.upper() for x in ["NEGÓCIO FECHADO", "FIM DA LINHA"]):
        if bb["deal_state"] != "BURNED": bb["deal_state"] = "CLOSED"

    bb["history"].append({"role": "user", "content": user_input})
    bb["history"].append({"role": "assistant", "content": answer})
    return answer

# ----------------------------
# 5. Estética Cyberdeck (CSS)
# ----------------------------
def apply_cyberdeck_style():
    st.markdown("""
        <style>
        /* Estilo Geral: Terminal Retro */
        @import url('https://fonts.googleapis.com/css2?family=Source+Code+Pro:wght@400;700&display=swap');
        
        .stApp {
            background-color: #0d0208;
            font-family: 'Source Code Pro', monospace;
            color: #00ff41;
        }
        
        /* Sidebar: Painel de Controle de Hardware */
        [data-testid="stSidebar"] {
            background-color: #001a00;
            border-right: 2px solid #00ff41;
        }
        
        /* Balões de Chat: Blocos de Dados */
        .stChatMessage {
            background-color: #000000;
            border: 1px solid #00ff41;
            border-radius: 0px;
            margin-bottom: 10px;
            box-shadow: 0 0 5px #00ff41;
        }
        
        /* Inputs e Botões */
        .stTextInput input {
            background-color: #000000;
            color: #00ff41;
            border: 1px solid #00ff41;
        }
        
        h1, h2, h3 {
            color: #ff9d00 !important;
            text-transform: uppercase;
            text-shadow: 2px 2px #5a0000;
        }
        
        .stProgress > div > div > div > div {
            background-color: #00ff41;
        }
        </style>
    """, unsafe_allow_html=True)

# ----------------------------
# 6. Interface Principal
# ----------------------------
def main():
    st.set_page_config(page_title="HARRY_SATO_v3.1", layout="centered")
    apply_cyberdeck_style()
    bb = st.session_state.blackboard

    # Cabeçalho: Imagem e Situação
    col1, col2 = st.columns([1, 2])
    with col1:
        if os.path.exists("harry_sato.jpg"):
            st.image("harry_sato.jpg", use_container_width=True)
        else:
            st.warning("IMAGE_NOT_FOUND")
            
    with col2:
        st.subheader("Node: Roosevelt_Island_NYCS")
        st.write("""
        **LOCALIZAÇÃO:** Nível Inferior - Plataforma 04.  
        **STATUS:** Harry Sato aguarda na penumbra. O ar está pesado, saturado por cheiro de ozônio e resíduos industriais.  
        **AVISO:** Mantenha a guarda alta. Vigilância algorítmica ativa na área.
        """)

    # Estados Terminais
    if bb["deal_state"] in ["CLOSED", "BURNED"]:
        st.divider()
        if bb["deal_state"] == "CLOSED":
            st.success("PROTOCOL_COMPLETE: TRANSAÇÃO EFETUADA.")
        else:
            st.error("CONNECTION_LOST: O CONTATO FOI QUEIMADO.")
        
        for m in bb["history"]:
            st.write(f"**{m['role'].upper()}:** {m['content']}")
        if st.button("REBOOT_SYSTEM"):
            del st.session_state.blackboard
            st.rerun()
        st.stop()

    st.sidebar.markdown("### HARDWARE_STATUS")
    st.sidebar.metric("PARANOIA", f"{bb['suspicion'] * 100:.0f}%")
    st.sidebar.write(f"MOOD: {bb['mood']}")
    st.sidebar.progress(bb['suspicion'])

    if prompt := st.chat_input("Insira comando de voz..."):
        harry_speaks(prompt)
        st.rerun()

    for m in bb["history"]:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])

if __name__ == "__main__":
    main()
