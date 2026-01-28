import os
import streamlit as st
from openai import OpenAI

# ----------------------------
# 1. Configurações de Motor
# ----------------------------
MODEL = "gpt-4o-mini"
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

if "blackboard" not in st.session_state:
    st.session_state.blackboard = {
        "suspicion": 0.2,
        "deal_state": "IDLE", # IDLE, NEGOTIATING, CLOSED, BURNED
        "history": []
    }

# ----------------------------
# 2. Sensor de Reatividade (O "Ouvido" da Rua)
# ----------------------------
def process_vibe(user_text):
    bb = st.session_state.blackboard
    text = user_text.lower()
    
    # Gatilhos de Perigo (Hardcoded para evitar passividade)
    perigo = ["polícia", "cop", "denunciar", "prender", "cana"]
    insultos = ["burro", "idiota", "merda", "chupa", "trouxa"]
    
    if any(p in text for p in perigo):
        bb["suspicion"] = 1.0
        bb["deal_state"] = "BURNED"
        return "POLICE_THREAT"
    
    if any(i in text for i in insultos):
        bb["suspicion"] = min(1.0, bb["suspicion"] + 0.4)
        return "INSULTED"

    return "NORMAL"

# ----------------------------
# 3. Behavior Tree (Prioridades Reais)
# ----------------------------
def get_action_instruction(vibe, user_input):
    bb = st.session_state.blackboard
    
    if bb["deal_state"] == "BURNED":
        return "ESTADO: FUGA. Você foi ameaçado ou insultado. Mande o cara se ferrar e suma. Fim da linha."

    if vibe == "INSULTED":
        return "ESTADO: REAÇÃO AGRESSIVA. O cara foi folgado. Mostre que você não é moleque de recados. Exija respeito ou vaza."

    if "quanto" in user_input.lower() or "preço" in user_input.lower() or "compro" in user_input.lower():
        bb["deal_state"] = "NEGOTIATING"
        return "ESTADO: NEGÓCIO. Preço fixo: 200 dólares. Sem metáforas. Se ele aceitar, diga 'NEGÓCIO FECHADO'."

    return "ESTADO: SONDAGEM. Seja seco, mas mantenha a malandragem. Não entregue nada de graça."

# ----------------------------
# 4. Atuador (Persona v5.0)
# ----------------------------
def call_harry(user_msg):
    bb = st.session_state.blackboard
    vibe = process_vibe(user_msg)
    instruction = get_action_instruction(vibe, user_msg)
    
    # PROMPT EQUILIBRADO: Inteligência sem Poesia.
    system_prompt = f"""Você é Harry Sato, traficante pragmático em NYCS. 
    TOM: Ácido, urbano, impaciente. 
    VOCABULÁRIO: Use gírias de rua de NYCS (ex: 'pratas', 'sujo', 'esquema', 'vaza'). 
    PROIBIDO: Metáforas sobre samurais, peixes, sombras ou sabedoria. Fale como se cada segundo a mais na estação fosse um risco de prisão.
    INSTRUÇÃO: {instruction}
    SUSPEITA: {bb['suspicion']:.2f}"""

    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(bb["history"][-4:])
    messages.append({"role": "user", "content": user_msg})
    
    answer = client.chat.completions.create(model=MODEL, messages=messages, temperature=0.6).choices[0].message.content
    
    if "NEGÓCIO FECHADO" in answer.upper() or bb["deal_state"] == "BURNED":
        if bb["deal_state"] != "BURNED": bb["deal_state"] = "CLOSED"
        
    bb["history"].append({"role": "user", "content": user_msg})
    bb["history"].append({"role": "assistant", "content": answer})
    return answer

# ----------------------------
# 5. Interface UI (Mission Control)
# ----------------------------
def main():
    st.set_page_config(page_title="Harry Sato v5.0")
    bb = st.session_state.blackboard

    if bb["deal_state"] in ["CLOSED", "BURNED"]:
        st.divider()
        if bb["deal_state"] == "CLOSED":
            st.success("✅ **MISSÃO CUMPRIDA**: Harry pegou as 200 pratas e sumiu.")
        else:
            st.error("🚨 **MISSÃO FALHOU**: Harry te bloqueou. A conexão caiu.")
        
        for m in bb["history"]: st.write(f"**{m['role'].capitalize()}:** {m['content']}")
        if st.button("Reset"):
            del st.session_state.blackboard
            st.rerun()
        st.stop()

    st.title("🚇 Estação Roosevelt Island")
    st.caption(f"Status: {bb['deal_state']} | Risco: {bb['suspicion']*100:.0f}%")

    if prompt := st.chat_input("..."):
        call_harry(prompt)
        st.rerun()

    for m in bb["history"]:
        with st.chat_message(m["role"]): st.write(m["content"])

if __name__ == "__main__":
    main()
