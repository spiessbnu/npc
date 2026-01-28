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
    text = user_text.lower()

    # Detecção de Hostilidade e Ameaça de Autoridade (Ajuste de Segurança v3.1)
    # Adicionamos gatilhos para identificar a polícia ou tentativas de prisão
    perigo = ["chupa", "idiota", "burro", "polícia", "prender", "id", "identidade", "cop", "denunciar"]
    if any(x in text for x in perigo):
        bb["suspicion"] = min(1.0, bb["suspicion"] + 0.5) # Incremento drástico de paranoia
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

    # Ramo de Segurança: Se a suspeita for alta, o Harry 'queima' o contato e foge
    if bb["suspicion"] > 0.75:
        bb["deal_state"] = "BURNED"
        return (
            "ESTADO: QUEIMADO. Harry detectou perigo real "
            "ou desrespeito inaceitável. Encerrar a conexão imediatamente."
        )

    # Ramo de Negócio: Foco na transação de Digits
    if "BUY" in intent_data:
        bb["deal_state"] = "NEGOTIATING"
        bb["mood"] = "GREEDY"
        return (
            "ESTADO: NEGOCIAÇÃO. Fale de negócios (200 dólares fixos). "
            "Se o usuário aceitar, finalize com 'NEGÓCIO FECHADO'."
        )

    # Ramo de Sondagem: Quando o usuário faz perguntas pessoais ou sobre o local
    if "PROBE" in intent_data:
        bb["mood"] = "TENSE"
        return (
            "ESTADO: SONDAGEM. O interlocutor quer saber demais. "
            "Responda com enigmas ríspidos e teste a lealdade dele."
        )

    # Ramo de Ócio: Manutenção de Persona
    return (
        "ESTADO: FLAVOR. Harry comenta a decadência de NYCS "
        "ou o lixo na estação para reforçar sua persona."
    )

# ----------------------------
# 4. Atuador de Voz (Prompt de Persona)
# ----------------------------
def harry_speaks(user_input):
    bb = st.session_state.blackboard

    intent_info = analyze_context(user_input)
    node_instruction = tick_behavior_tree(intent_info)

    system_prompt = f"""
Você é Harry Sato, um traficante cínico em Roosevelt Island.

# PERSONA E AMBIENTE
Traficante de Digits em NYCS. Pragmatismo, risco mínimo, lucro rápido.

# DIRETRIZES
- Máx. 2 frases curtas e diretas.
- Proibido clichês orientais excessivos ou metáforas poéticas longas.
- Trate termos técnicos como paranoia de sub-rede.

# ESTADO ATUAL (Instrução da Behavior Tree)
{node_instruction}
NÍVEL DE PARANOIA: {bb['suspicion']:.2f}

# NEGOCIAÇÃO
Preço fixo: 200 dólares. Sem descontos.
Encerrar com "NEGÓCIO FECHADO" ao concluir a venda.
Encerrar com "FIM DA LINHA" se a suspeita subir ou o perigo for detectado.

HUMOR ATUAL: {bb['mood']}
"""

    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(bb["history"][-4:]) # Histórico curto para manter o foco
    messages.append({"role": "user", "content": user_input})

    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        temperature=0.6
    )

    answer = response.choices[0].message.content

    # Lógica de Terminalidade: Identifica se a cena deve ser encerrada
    if any(x in answer.upper() for x in ["NEGÓCIO FECHADO", "FIM DA LINHA"]):
        if bb["deal_state"] != "BURNED":
            bb["deal_state"] = "CLOSED"

    # Atualização da Memória de Trabalho
    bb["history"].append({"role": "user", "content": user_input})
    bb["history"].append({"role": "assistant", "content": answer})

    return answer

# ----------------------------
# 5. Interface Streamlit
# ----------------------------
def main():
    st.set_page_config(
        page_title="NYCS: Harry Sato v3.1",
        layout="centered"
    )

    bb = st.session_state.blackboard

    # Exit Nodes: Trava o chat se a missão terminou (Sucesso ou Falha)
    if bb["deal_state"] in ["CLOSED", "BURNED"]:
        st.divider()

        if bb["deal_state"] == "CLOSED":
            st.success("🏁 MISSION ACCOMPLISHED: A transação foi concluída com sucesso.")
        else:
            st.error("🚨 MISSION FAILED: Harry Sato sumiu. O contato foi 'queimado'.")

        for m in bb["history"]:
            role = "Harry" if m["role"] == "assistant" else "Você"
            st.write(f"**{role}:** {m['content']}")

        if st.button("Tentar Novamente"):
            del st.session_state.blackboard
            st.rerun()

        st.stop()

    st.title("🚇 Estação Roosevelt Island — NYCS")
    st.info(
        f"Monitor de Paranoia: {bb['suspicion'] * 100:.0f}% | "
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
