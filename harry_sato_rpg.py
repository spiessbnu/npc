import os
import streamlit as st
from openai import OpenAI

# ----------------------------
# 1. Motor e Configuração
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
# 2. Sensor de Perigo (Intent Parser Hardened)
# ----------------------------
def analyze_danger(user_text):
    bb = st.session_state.blackboard
    text = user_text.lower()
    
    # Gatilhos de interrupção imediata (Hardcoded para evitar alucinação do LLM)
    perigo_imediato = ["polícia", "cop", "denunciar", "prender", "beijo", "sexo", "oral", "chupa"]
    if any(p in text for p in perigo_imediato):
        bb["suspicion"] = 1.0
        bb["deal_state"] = "BURNED"
        return "DANGER"
    
    prompt = f"Classifique a intenção (BUY, PROBE, CHAT): '{user_text}'"
    resp = client.chat.completions.create(model=MODEL, messages=[{"role": "user", "content": prompt}], temperature=0, max_tokens=10)
    return resp.choices[0].message.content.strip().upper()

# ----------------------------
# 3. Atuador de Voz (Foco em Brutalidade)
# ----------------------------
def harry_response(user_input):
    bb = st.session_state.blackboard
    intent = analyze_danger(user_input)
    
    # Lógica de Instrução da Árvore
    if bb["deal_state"] == "BURNED":
        instruction = "ESTADO: FUGA. Você foi insultado ou ameaçado. Ofenda o cara e suma. Não negocie."
    elif intent == "BUY":
        bb["deal_state"] = "NEGOTIATING"
        instruction = "ESTADO: NEGÓCIO. Preço fixo 200. Sem papo furado. Se ele aceitar, diga 'NEGÓCIO FECHADO'."
    else:
        instruction = "ESTADO: DESCONFIANÇA. Seja curto. Pergunte o que ele quer ou mande vazar."

    # PROMPT DE RUA (v4.0)
    system_prompt = f"""Você é Harry Sato, traficante em NYCS. 
    ESTILO: Brutalmente curto. Máximo 15 palavras. 
    PROIBIDO: Metáforas, poesias, conselhos morais ou palavras como 'ronin', 'sombra' ou 'labirinto'. 
    Fale como um criminoso impaciente: 'Paga ou vaza'.
    OBJETIVO: {instruction}"""

    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(bb["history"][-2:]) # Contexto curtíssimo para evitar verborragia
    messages.append({"role": "user", "content": user_input})
    
    answer = client.chat.completions.create(model=MODEL, messages=messages, temperature=0.5).choices[0].message.content
    
    if "NEGÓCIO FECHADO" in answer.upper() or "VAZA" in answer.upper() or bb["deal_state"] == "BURNED":
        if bb["deal_state"] != "BURNED": bb["deal_state"] = "CLOSED"
        
    bb["history"].append({"role": "user", "content": user_input})
    bb["history"].append({"role": "assistant", "content": answer})
    return answer

# ----------------------------
# 4. Interface com Travamento de Chat
# ----------------------------
def main():
    st.set_page_config(page_title="Harry Sato v4.0")
    bb = st.session_state.blackboard

    if bb["deal_state"] in ["CLOSED", "BURNED"]:
        st.divider()
        if bb["deal_state"] == "CLOSED":
            st.success("✅ **MISSÃO CUMPRIDA**: Harry pegou o dinheiro e sumiu no túnel.")
        else:
            st.error("🚨 **MISSÃO FALHOU**: Conexão cortada. Harry te marcou como 'problema'.")
        
        for m in bb["history"]: st.write(f"**{m['role'].capitalize()}:** {m['content']}")
        if st.button("Tentar denovo"):
            del st.session_state.blackboard
            st.rerun()
        st.stop()

    st.title("🚇 Roosevelt Island")
    if prompt := st.chat_input("..."):
        harry_response(prompt)
        st.rerun()

    for m in bb["history"]:
        with st.chat_message(m["role"]): st.write(m["content"])

if __name__ == "__main__":
    main()
