import os
import streamlit as st
from openai import OpenAI

# ----------------------------
# 1. Configuração e Estado
# ----------------------------
MODEL = "gpt-4o-mini"
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

if "blackboard" not in st.session_state:
    st.session_state.blackboard = {
        "suspicion": 0.0,
        "deal_state": "IDLE", # IDLE, NEGOTIATING, CLOSED, BURNED
        "history": []
    }

# ----------------------------
# 2. Sensor de Intenção (Simplificado)
# ----------------------------
def classify_intent(text):
    prompt = f"Classifique em uma palavra: BUY, HOSTILE, TECH, ou CHAT. Texto: '{text}'"
    resp = client.chat.completions.create(model=MODEL, messages=[{"role": "user", "content": prompt}], temperature=0, max_tokens=5)
    return resp.choices[0].message.content.strip().upper()

# ----------------------------
# 3. Motor de Decisão (Behavior Tree)
# ----------------------------
def get_node_instruction():
    bb = st.session_state.blackboard
    intent = bb.get("last_intent")

    # PRIORIDADE 1: SEGURANÇA / BURNED
    if bb["suspicion"] > 0.8:
        bb["deal_state"] = "BURNED"
        return "ESTADO: FUGA. O cara é um otário ou polícia. Ofenda-o e suma. FIM DE PAPO."

    # PRIORIDADE 2: FECHAMENTO
    if bb["deal_state"] == "NEGOTIATING" and intent == "BUY":
        return "ESTADO: FECHAMENTO. O preço é 200. Se ele aceitou, dê as instruções finais e diga 'NEGÓCIO FECHADO'."

    # PRIORIDADE 3: NEGOCIAÇÃO
    if intent == "BUY":
        bb["deal_state"] = "NEGOTIATING"
        return "ESTADO: BARGANHA. Seja direto. 200 dólares. Sem metáforas bobas agora."

    return "ESTADO: SONDAGEM. Seja seco, curto e desconfiado."

# ----------------------------
# 4. Atuador de Voz (Harry Sato)
# ----------------------------
def generate_harry_response(user_input):
    bb = st.session_state.blackboard
    bb["last_intent"] = classify_intent(user_input)
    
    # Penalidade por desrespeito (baseado no seu teste)
    if any(x in user_input.lower() for x in ["chupa", "merda", "otário"]):
        bb["suspicion"] += 0.4

    instruction = get_node_instruction()
    
    # PROMPT REFINADO: Foco em crueza e economia
    system_prompt = f"""Você é Harry Sato, traficante em Roosevelt Island. 
    DIRETRIZ DE ESTILO: Seja SECO e CURTO (máximo 25 palavras). 
    REFERÊNCIAS: Evite mencionar samurais/animes a menos que seja estritamente necessário para uma gíria. 
    OBJETIVO ATUAL: {instruction}"""

    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(bb["history"][-4:])
    messages.append({"role": "user", "content": user_input})
    
    answer = client.chat.completions.create(model=MODEL, messages=messages, temperature=0.6).choices[0].message.content
    
    # Detecta gatilho de encerramento
    if "negócio fechado" in answer.lower() or "sumindo daqui" in answer.lower():
        bb["deal_state"] = "CLOSED" if bb["suspicion"] < 0.8 else "BURNED"
        
    bb["history"].append({"role": "user", "content": user_input})
    bb["history"].append({"role": "assistant", "content": answer})
    return answer

# ----------------------------
# 5. Interface UI
# ----------------------------
def main():
    st.set_page_config(page_title="Harry Sato v2.2")
    
    # Renderização de fim de jogo
    if st.session_state.blackboard["deal_state"] in ["CLOSED", "BURNED"]:
        status = st.session_state.blackboard["deal_state"]
        msg = "✅ MISSÃO CUMPRIDA: Transação finalizada." if status == "CLOSED" else "🚨 CONEXÃO PERDIDA: Harry cortou o contato."
        st.subheader(msg)
        for m in st.session_state.blackboard["history"]:
            st.write(f"**{m['role'].capitalize()}:** {m['content']}")
        if st.button("Reiniciar"):
            del st.session_state.blackboard
            st.rerun()
        st.stop()

    # Fluxo normal de chat
    st.title("🚇 Metrô Roosevelt Island")
    if prompt := st.chat_input("..."):
        with st.spinner("Harry está pensando..."):
            generate_harry_response(prompt)
        st.rerun()

    for m in st.session_state.blackboard["history"]:
        with st.chat_message(m["role"]):
            st.write(m["content"])

if __name__ == "__main__":
    main()
