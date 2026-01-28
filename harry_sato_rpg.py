import os
import streamlit as st
from openai import OpenAI

# ----------------------------
# 1. Configuração de Motor
# ----------------------------
MODEL = "gpt-4o-mini"
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

if "blackboard" not in st.session_state:
    st.session_state.blackboard = {
        "suspicion": 0.1,
        "deal_state": "IDLE", # IDLE, NEGOTIATING, CLOSED, BURNED
        "history": []
    }

# ----------------------------
# 2. Sensor de Intenção (Direto)
# ----------------------------
def analyze_intent(user_text):
    bb = st.session_state.blackboard
    text = user_text.lower()
    
    # Extração de valores numéricos (para aceitar 150-200)
    price_found = re.findall(r'\d+', text)
    val = int(price_found[0]) if price_found else 0
    
    # Sensor de Ameaça/Insulto
    if any(p in text for p in ["polícia", "cop", "chupa", "idiota", "prender"]):
        bb["suspicion"] = 1.0
        return "DANGER"

    if val >= 150: return "OFFER_ACCEPTED"
    if "comprar" in text or "digit" in text or "geo" in text: return "BUY"
    return "CHAT"

# ----------------------------
# 3. Behavior Tree (Racionalidade Pragmática)
# ----------------------------
def get_instruction(intent):
    bb = st.session_state.blackboard
    
    if bb["deal_state"] == "BURNED" or intent == "DANGER":
        bb["deal_state"] = "BURNED"
        return "ESTADO: FUGA. Alerta máximo. Ofenda e encerre com 'FIM DA LINHA'."

    if intent == "OFFER_ACCEPTED":
        return "ESTADO: CONCLUSÃO. O valor é aceitável. Entregue o Digit e encerre com 'NEGÓCIO FECHADO'."

    if intent == "BUY" or bb["deal_state"] == "NEGOTIATING":
        bb["deal_state"] = "NEGOTIATING"
        return "ESTADO: NEGOCIAÇÃO. Pergunte quanto ele tem. O alvo é 200, mas 150 serve se ele for rápido."

    return "ESTADO: IMPACIÊNCIA. Harry quer que o cara fale logo ou vaze."

# ----------------------------
# 4. Atuador (Harry Sato "Seco")
# ----------------------------
def call_harry(user_msg):
    bb = st.session_state.blackboard
    intent = analyze_intent(user_msg)
    instruction = get_instruction(intent)
    
    # PROMPT MINIMALISTA
    system_prompt = f"""Você é Harry Sato, traficante em Roosevelt Island.
    ESTILO: Brutalmente curto. Máximo 12 palavras por fala.
    PROIBIDO: Usar samurais, ronins, metáforas ou poesias.
    PERSONA: Você está com pressa. É 'paga ou vaza'.
    OBJETIVO: {instruction}"""

    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(bb["history"][-2:]) # Contexto mínimo
    messages.append({"role": "user", "content": user_msg})
    
    answer = client.chat.completions.create(model=MODEL, messages=messages, temperature=0.5).choices[0].message.content
    
    # Gatilhos de Saída
    if "NEGÓCIO FECHADO" in answer.upper() or "FIM DA LINHA" in answer.upper():
        if bb["deal_state"] != "BURNED": bb["deal_state"] = "CLOSED"
        
    bb["history"].append({"role": "user", "content": user_msg})
    bb["history"].append({"role": "assistant", "content": answer})
    return answer

# ----------------------------
# 5. Interface UI
# ----------------------------
def main():
    st.set_page_config(page_title="Harry Sato v6.0")
    bb = st.session_state.blackboard

    if bb["deal_state"] in ["CLOSED", "BURNED"]:
        st.divider()
        st.subheader("✅ Transação Concluída" if bb["deal_state"] == "CLOSED" else "🚨 Conexão Cortada")
        for m in bb["history"]: st.write(f"**{m['role'].capitalize()}:** {m['content']}")
        if st.button("Reset"):
            del st.session_state.blackboard
            st.rerun()
        st.stop()

    st.title("🚇 Estação Roosevelt Island")
    if prompt := st.chat_input("Diga algo..."):
        call_harry(prompt)
        st.rerun()

    for m in bb["history"]:
        with st.chat_message(m["role"]): st.write(m["content"])

if __name__ == "__main__":
    main()
