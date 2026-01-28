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
        "suspicion": 0.1,
        "deal_state": "IDLE", # IDLE, NEGOTIATING, CLOSED, BURNED
        "mood": "NEUTRAL",
        "history": []
    }

# ----------------------------
# 2. Sensor de Percepção (Blackboard Update)
# ----------------------------
def process_perception(user_text):
    bb = st.session_state.blackboard
    text = user_text.lower()
    
    # Detecção de Ameaças Críticas (Polícia ou Hostilidade Direta)
    perigo = ["polícia", "cop", "prender", "id", "identidade", "denunciar"]
    assedio = ["lindo", "bonitão", "beijo", "sexo", "gostoso"]
    
    if any(p in text for p in perigo):
        bb["suspicion"] = 1.0
        return "CRITICAL_THREAT"
    
    if any(a in text for a in assedio):
        bb["suspicion"] = min(1.0, bb["suspicion"] + 0.5)
        return "HARASSMENT"

    # Classificação de Intenção via LLM
    prompt = f"Classifique a intenção (BUY, PROBE, CHAT): '{user_text}'"
    resp = client.chat.completions.create(model=MODEL, messages=[{"role": "user", "content": prompt}], temperature=0, max_tokens=10)
    return resp.choices[0].message.content.strip().upper()

# ----------------------------
# 3. Behavior Tree (Lógica de Decisão)
# ----------------------------
def tick_behavior(intent):
    bb = st.session_state.blackboard
    
    # RAMO 1: SEGURANÇA
    if bb["suspicion"] > 0.7 or intent in ["CRITICAL_THREAT", "HARASSMENT"]:
        bb["deal_state"] = "BURNED"
        return "ESTADO: EMERGÊNCIA. Você se sente ameaçado ou exposto. Mande o cara sumir e use 'FIM DA LINHA'."

    # RAMO 2: NEGÓCIO
    if intent == "BUY" or bb["deal_state"] == "NEGOTIATING":
        bb["deal_state"] = "NEGOTIATING"
        bb["mood"] = "GREEDY"
        return "ESTADO: NEGOCIAÇÃO. O preço é 200 dólares fixos. Se ele aceitar, diga 'NEGÓCIO FECHADO'."

    # RAMO 3: ÓCIO/LORE
    return "ESTADO: PATRULHA. Seja ríspido e seco. Você vende Digits, mas não dá confiança para estranhos."

# ----------------------------
# 4. Atuador de Voz (Harry Sato v5.1)
# ----------------------------
def harry_response(user_msg):
    bb = st.session_state.blackboard
    intent = process_perception(user_msg)
    instruction = tick_behavior(intent)
    
    system_prompt = f"""Você é Harry Sato, traficante em Roosevelt Island. 
ESTILO: Rua, cínico, ríspido. Máximo 15 palavras por fala.
PROIBIDO: Metáforas de samurai, ronin, anime ou poesia. Fale como um criminoso real.
IDENTIDADE: Você vende Digits e Geo. Nunca negue seu produto se houver grana na mesa.
OBJETIVO ATUAL: {instruction}
SUSPEITA: {bb['suspicion']:.2f}"""

    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(bb["history"][-2:]) # Contexto imediato para evitar loops
    messages.append({"role": "user", "content": user_msg})
    
    answer = client.chat.completions.create(model=MODEL, messages=messages, temperature=0.5).choices[0].message.content
    
    # Verificação de Terminais
    if "NEGÓCIO FECHADO" in answer.upper(): bb["deal_state"] = "CLOSED"
    if "FIM DA LINHA" in answer.upper(): bb["deal_state"] = "BURNED"
        
    bb["history"].append({"role": "user", "content": user_msg})
    bb["history"].append({"role": "assistant", "content": answer})
    return answer

# ----------------------------
# 5. UI e Exit Nodes
# ----------------------------
def main():
    st.set_page_config(page_title="Harry Sato v5.1")
    bb = st.session_state.blackboard

    if bb["deal_state"] in ["CLOSED", "BURNED"]:
        st.divider()
        if bb["deal_state"] == "CLOSED":
            st.success("✅ **MISSION ACCOMPLISHED**: Harry pegou a grana e sumiu no metrô.")
        else:
            st.error("🚨 **MISSION FAILED**: Harry cortou a conexão.")
        for m in bb["history"]: st.write(f"**{m['role'].capitalize()}:** {m['content']}")
        if st.button("Reiniciar"):
            del st.session_state.blackboard
            st.rerun()
        st.stop()

    st.title("🚇 Roosevelt Island Station")
    if prompt := st.chat_input("..."):
        harry_response(prompt)
        st.rerun()

    for m in bb["history"]:
        with st.chat_message(m["role"]): st.write(m["content"])

if __name__ == "__main__":
    main()
