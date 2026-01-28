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
            "ESTADO: QUEIMADO. Harry detectou perigo real ou "
            "desrespeito inaceitável. Encerrar conexão."
        )

    if "BUY" in intent_data:
        bb["deal_state"] = "NEGOTIATING"
        bb["mood"] = "GREEDY"
        return (
            "ESTADO: NEGOCIAÇÃO. Preço fixo 200 dólares. "
            "Finalize com 'NEGÓCIO FECHADO' se aceitar."
        )

    if "PROBE" in intent_data:
        bb["mood"] = "TENSE"
        return (
            "ESTADO: SONDAGEM. Interlocutor curioso demais. "
            "Teste lealdade com respostas evasivas."
        )

    return (
        "ESTADO: FLAVOR. Comentários secos sobre NYCS "
        "e o ambiente decadente."
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

# PERSONA
Traficante urbano, pragmático, foco em lucro e autopreservação.

# DIRETRIZES
- Máx. 2 frases curtas.
- Nada de clichês orientais ou meta.
- Termos técnicos = paranoia de sub-rede.

# ESTADO ATUAL
{node_instruction}
SUSPEITA: {bb['suspicion']:.2f}

# NEGOCIAÇÃO
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
        page_title="NYCS: Harry Sato",
        layout="centered"
    )

    # ---------- CSS CIBERDECK LIMPO ----------
    st.markdown(
        """
        <style>
        html, body, [class*="css"] {
            background-color: #0b0e11;
            color: #d7dde5;
            font-family: "Inter", monospace;
        }

        section[data-testid="stSidebar"] {
            background-color: #0d1117;
            border-right: 1px solid #1f2933;
        }

        section[data-testid="stSidebar"] h1,
        section[data-testid="stSidebar"] h2,
        section[data-testid="stSidebar"] h3 {
            color: #3fa46a;
            font-size: 0.85rem;
            letter-spacing: 0.08em;
        }

        section[data-testid="stSidebar"] p {
            color: #8b949e;
            font-size: 0.8rem;
        }

        .status-line {
            font-size: 0.8rem;
            color: #8b949e;
            opacity: 0.7;
            margin-bottom: 1rem;
            letter-spacing: 0.04em;
        }

        div[data-testid="stChatMessage"] {
            background: transparent;
            border: none;
            padding: 0.4rem 0;
        }

        div[data-testid="stChatMessage"][aria-label="assistant"] {
            background-color: #11161c;
            border-left: 3px solid #3fa46a;
            padding: 0.6rem 0.8rem;
            margin-bottom: 0.4rem;
        }

        div[data-testid="stChatMessage"][aria-label="user"] {
            text-align: right;
            opacity: 0.9;
        }

        textarea {
            background-color: #11161c !important;
            color: #d7dde5 !important;
            border: 1px solid #1f2933 !important;
            border-radius: 6px;
        }

        textarea:focus {
            border: 1px solid #c9a227 !important;
            box-shadow: none !important;
        }

        button {
            background-color: #11161c !important;
            color: #d7dde5 !important;
            border: 1px solid #1f2933 !important;
        }

        button:hover {
            border-color: #3fa46a !important;
        }

        .stSuccess {
            background-color: rgba(63, 164, 106, 0.08);
            color: #3fa46a;
        }

        .stError {
            background-color: rgba(201, 79, 79, 0.08);
            color: #c94f4f;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    bb = st.session_state.blackboard

    # ---------- HUD LATERAL ----------
    with st.sidebar:
        st.markdown("### SYSTEM_DIAGNOSTICS")
        st.markdown(f"PARANOIA: {bb['suspicion']*100:.0f}%")
        st.markdown(f"MOOD: {bb['mood']}")
        st.markdown(f"STATE: {bb['deal_state']}")

    # ---------- ENCERRAMENTO ----------
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

    # ---------- CABEÇALHO ----------
    st.title("ROOSEVELT_ISLAND // NODE")

    st.markdown(
        f"""
        <div class="status-line">
        Plataforma 04 · Vigilância algorítmica ativa ·
        Paranoia {bb['suspicion']*100:.0f}% · Humor {bb['mood']}
        </div>
        """,
        unsafe_allow_html=True
    )

    # ---------- INPUT ----------
    if prompt := st.chat_input("Fale com o contato..."):
        harry_speaks(prompt)
        st.rerun()

    # ---------- HISTÓRICO ----------
    for m in bb["history"]:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])

if __name__ == "__main__":
    main()
