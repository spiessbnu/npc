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
        "mood": "NEUTRAL",      # NEUTRAL, TENSE, GREEDY, AGGRESSIVE
        "deal_state": "IDLE",   # IDLE, NEGOTIATING, CLOSED, BURNED
        "history": []
    }

# ----------------------------
# 2. Sensor de Intenção Contextual
# ----------------------------
def analyze_context(user_text):
    bb = st.session_state.blackboard

    # Detecção de Hostilidade
    if any(x in user_text.lower() for x in ["chupa", "idiota", "burro"]):
        bb["suspicion"] = min(1.0, bb["suspicion"] + 0.4)
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
# 3. Behavior Tree
# ----------------------------
def tick_behavior_tree(intent_data):
    bb = st.session_state.blackboard

    if bb["suspicion"] > 0.8:
        bb["deal_state"] = "BURNED"
        return (
            "ESTADO: QUEIMADO. Harry detectou perigo real "
            "ou desrespeito inaceitável. Encerrar a conexão."
        )

    if "BUY" in intent_data:
        bb["deal_state"] = "NEGOTIATING"
        bb["mood"] = "GREEDY"
        return (
            "ESTADO: NEGOCIAÇÃO. Fale de negócios (200 dólares). "
            "Se aceitar, finalize com 'NEGÓCIO FECHADO'."
        )

    if "PROBE" in intent_data:
        bb["mood"] = "TENSE"
        return (
            "ESTADO: SONDAGEM. O interlocutor quer saber demais. "
            "Responda com enigmas e teste lealdade."
        )

    return (
        "ESTADO: FLAVOR. Harry comenta a decadência de NYCS "
        "e reforça sua persona."
    )

# ----------------------------
# 4. Atuador de Voz
# ----------------------------
def harry_speaks(user_input):
    bb = st.session_state.blackboard

    intent_info = analyze_context(user_input)
    node_instruction = tick_behavior_tree(intent_info)

    system_prompt = f"""
Você é Harry Sato, um traficante cínico em Roosevelt Island.

# PERSONA E AMBIENTE
Traficante de Digits em NYCS. Pragmatismo, risco mínimo, lucro rápido.
Não vende drogas convencionais (maconha, cocaína, LSD), apenas Digits.
Digits são programas de computador. Seu principal produto é Geommetry, um Digit para aumentar capacidade intelectual. 
Você vive em NYCS - New York City State - em um mundo cyberpunk, no ano de 2070, onde a cidade foi privatizada. 
A cidade é controlada pela Liberty Corporation. 

# DIRETRIZES
- Máx. 2 frases curtas.
- Proibido clichês ou meta-referências. 
- Refira-se ao seu mundo ciberpunk apenas se for perguntado sobre isso.


# ESTADO ATUAL
{node_instruction}
NÍVEL DE SUSPEITA: {bb['suspicion']:.2f}

# NEGOCIAÇÃO
Você postou anúncio na Sub Net - rede de computadores clandestina. 
Preço fixo: 200 dólares.
Encerrar com "NEGÓCIO FECHADO" ao concluir.
Encerrar com "FIM DA LINHA" se suspeita alta.

# FALLBACK
"Fala logo o que quer ou vaza."

HUMOR: {bb['mood']}
"""

    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(bb["history"][-4:])
    messages.append({"role": "user", "content": user_input})

    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        temperature=0.6
    )

    answer = response.choices[0].message.content

    if any(x in answer.upper() for x in ["NEGÓCIO FECHADO", "FIM DA LINHA"]):
        if bb["deal_state"] != "BURNED":
            bb["deal_state"] = "CLOSED"

    bb["history"].append({"role": "user", "content": user_input})
    bb["history"].append({"role": "assistant", "content": answer})

    return answer

# ----------------------------
# 5. Interface Streamlit
# ----------------------------
def main():
    st.set_page_config(
        page_title="NYCS: Harry Sato v3.0",
        layout="centered"
    )

    bb = st.session_state.blackboard

    if bb["deal_state"] in ["CLOSED", "BURNED"]:
        st.divider()

        if bb["deal_state"] == "CLOSED":
            st.success("MISSION ACCOMPLISHED: Transação concluída.")
        else:
            st.error("MISSION FAILED: Contato perdido.")

        for m in bb["history"]:
            st.write(f"**{m['role'].capitalize()}:** {m['content']}")

        if st.button("Nova Tentativa"):
            del st.session_state.blackboard
            st.rerun()

        st.stop()

    st.title("Estação Roosevelt Island — NYCS")
    st.info(
        f"Paranoia: {bb['suspicion'] * 100:.0f}% | "
        f"Humor: {bb['mood']}"
    )

    if prompt := st.chat_input("Fale com o contato..."):
        harry_speaks(prompt)
        st.rerun()

    for m in bb["history"]:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])

if __name__ == "__main__":
    main()
