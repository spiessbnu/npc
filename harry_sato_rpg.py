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
        "suspicion": 0.1,       # 0.0 a 1.0
        "mood": "NEUTRAL",      # NEUTRAL, TENSE, GREEDY, AGGRESSIVE
        "deal_state": "IDLE",   # IDLE, NEGOTIATING, CLOSED (Sucesso), BURNED (Fuga)
        "history": []
    }

# ----------------------------
# 2. Sensor Semântico (Percepção)
# ----------------------------
def analyze_context(user_text):
    bb = st.session_state.blackboard
    text = user_text.lower()

    # Sensor de Ameaça de Autoridade e Hostilidade
    perigo = ["polícia", "cop", "denunciar", "prender", "cana", "id", "identidade"]
    insultos = ["chupa", "idiota", "burro", "merda", "otário"]
    
    if any(p in text for p in perigo):
        bb["suspicion"] = min(1.0, bb["suspicion"] + 0.6)
        bb["mood"] = "TENSE"
        return "THREAT"
    
    if any(i in text for i in insultos):
        bb["suspicion"] = min(1.0, bb["suspicion"] + 0.3)
        bb["mood"] = "AGGRESSIVE"
        return "HOSTILE"

    # Classificação de Intenção via LLM (Rápida)
    prompt = f"Classifique a intenção (BUY, PROBE, CHAT) e a urgência (HIGH, LOW) do usuário: '{user_text}'"
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

    # RAMO 1: SEGURANÇA (Prioridade Máxima)
    if bb["suspicion"] > 0.75 or "THREAT" in intent_data:
        bb["deal_state"] = "BURNED"
        return "ESTADO: FUGA. O interlocutor é perigoso ou autoridade. Encerre com 'FIM DA LINHA' e suma."

    # RAMO 2: NEGÓCIO (Gate de Segurança)
    if "BUY" in intent_data:
        # Só negocia se não estiver sob estresse alto
        if bb["suspicion"] < 0.5:
            bb["deal_state"] = "NEGOTIATING"
            bb["mood"] = "GREEDY"
            return "ESTADO: NEGOCIAÇÃO. 200 dólares fixos. Se ele aceitar, diga 'NEGÓCIO FECHADO'."
        else:
            return "ESTADO: RECUSA TEMPORÁRIA. Você está paranoico demais para vender agora. Desconverse."

    # RAMO 3: SONDAGEM
    if "PROBE" in intent_data:
        bb["mood"] = "TENSE"
        return "ESTADO: SONDAGEM. O cara quer saber demais. Responda com rispidez e sarcasmo."

    return "ESTADO: FLAVOR. Harry comenta sobre o lixo ou a falta de luz na estação de Roosevelt Island."

# ----------------------------
# 4. Atuador de Voz (Persona)
# ----------------------------
def harry_speaks(user_input):
    bb = st.session_state.blackboard
    intent_info = analyze_context(user_input)
    node_instruction = tick_behavior_tree(intent_info)

    system_prompt = f"""
Você é Harry Sato, um traficante cínico e impaciente em NYCS.

# DIRETRIZES DE ESTILO
- Respostas Curtas (máx. 2 frases). Use gírias de rua.
- PROIBIDO metáforas de samurais, ronins ou animes. Seja urbano.
- Se o cara te irritar, mande-o vazar.

# CONTEXTO ATUAL
{node_instruction}
NÍVEL DE PARANOIA: {bb['suspicion']:.2f}
HUMOR: {bb['mood']}

# REGRAS DE FECHAMENTO
- Preço: 200 dólares. Sem descontos.
- Se a venda for concluída, use obrigatoriamente: "NEGÓCIO FECHADO".
- Se for fugir ou cortar o papo, use obrigatoriamente: "FIM DA LINHA".
"""

    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(bb["history"][-4:]) # Mantém o fio da meada curto
    messages.append({"role": "user", "content": user_input})

    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        temperature=0.7
    )

    answer = response.choices[0].message.content

    # Gatilhos de Encerramento (Terminal Nodes)
    if "NEGÓCIO FECHADO" in answer.upper():
        bb["deal_state"] = "CLOSED"
    elif "FIM DA LINHA" in answer.upper():
        bb["deal_state"] = "BURNED"

    bb["history"].append({"role": "user", "content": user_input})
    bb["history"].append({"role": "assistant", "content": answer})

    return answer

# ----------------------------
# 5. Interface Streamlit
# ----------------------------
def main():
    st.set_page_config(page_title="Harry Sato v5.0", layout="centered")
    bb = st.session_state.blackboard

    # UI de Encerramento (Terminalidade)
    if bb["deal_state"] in ["CLOSED", "BURNED"]:
        st.divider()
        if bb["deal_state"] == "CLOSED":
            st.success("🏆 MISSION ACCOMPLISHED: O Digit está na mão. Harry sumiu.")
        else:
            st.error("🚨 MISSION FAILED: Harry te marcou como 'sujo'. Contato perdido.")
        
        for m in bb["history"]:
            role = "Harry" if m["role"] == "assistant" else "Você"
            st.write(f"**{role}:** {m['content']}")
        
        if st.button("Reiniciar Cena"):
            del st.session_state.blackboard
            st.rerun()
        st.stop()

    st.title("🚇 Roosevelt Island Station")
    st.info(f"Risco Detectado: {bb['suspicion'] * 100:.0f}% | Humor: {bb['mood']}")

    if prompt := st.chat_input("Fale com Harry..."):
        harry_speaks(prompt)
        st.rerun()

    for m in bb["history"]:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])

if __name__ == "__main__":
    main()
