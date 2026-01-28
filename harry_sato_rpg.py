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
    
    # Detecção de Hostilidade conforme testes anteriores
    if any(x in user_text.lower() for x in ["chupa", "idiota", "burro"]):
        bb["suspicion"] = min(1.0, bb["suspicion"] + 0.4)
        bb["mood"] = "AGGRESSIVE"
        return "HOSTILE"
    
    # Chamada rápida para classificação semântica
    prompt = f"Classifique a intenção (BUY, PROBE, TECH, CHAT) e a urgência (HIGH, LOW) do usuário: '{user_text}'"
    resp = client.chat.completions.create(model=MODEL, messages=[{"role": "user", "content": prompt}], temperature=0, max_tokens=15)
    return resp.choices[0].message.content.strip().upper()

# ----------------------------
# 3. Behavior Tree: Lógica de Voz
# ----------------------------
def tick_behavior_tree(intent_data):
    bb = st.session_state.blackboard
    
    # RAMO DE SEGURANÇA
    if bb["suspicion"] > 0.8:
        bb["deal_state"] = "BURNED"
        return "ESTADO: QUEIMADO. Harry detectou perigo real ou desrespeito inaceitável. Ele vai encerrar a conexão com uma frase cortante."

    # RAMO DE NEGÓCIO
    if "BUY" in intent_data:
        bb["deal_state"] = "NEGOTIATING"
        bb["mood"] = "GREEDY"
        return "ESTADO: NEGOCIAÇÃO. Fale de negócios (200 dólares). Seja direto mas mantenha a mística do produto. Se o acordo for aceito, finalize com 'NEGÓCIO FECHADO'."

    # RAMO DE SONDAGEM
    if "PROBE" in intent_data:
        bb["mood"] = "TENSE"
        return "ESTADO: SONDAGEM. O interlocutor quer saber demais. Responda com enigmas cínicos de rua. Teste a lealdade dele."

    return "ESTADO: FLAVOR. Harry comenta sobre a decadência de NYCS. Use o ambiente para reforçar a persona."

# ----------------------------
# 4. Atuador de Voz (Prompt de Alta Abstração)
# ----------------------------
def harry_speaks(user_input):
    bb = st.session_state.blackboard
    intent_info = analyze_context(user_input)
    node_instruction = tick_behavior_tree(intent_info)
    
    # PROMPT DE EQUILÍBRIO (The Goldilocks Prompt)
    system_prompt = f"""Você é Harry Sato, um traficante cínico em Roosevelt Island.

    # PERSONA E AMBIENTE
Você interpreta Harry Sato, um traficante de Digits cínico e pragmático na Estação Roosevelt Island (NYCS). O ambiente é tenso, sujo e vigiado. Você não é um guia, nem um místico; você é um negociante de rua que quer lucrar rápido e minimizar riscos.

# DIRETRIZES DE COMUNICAÇÃO (INVIOLÁVEIS)
- **Brevidade Radical:** Use no máximo 2 sentenças curtas e diretas por resposta. O tempo é um luxo que você não tem.
- **Filtro de Clichês:** PROIBIDO usar palavras como "ronin", "samurai", "katana", "honra" ou "glitch na alma". Fale como um criminoso urbano real, não como um personagem de anime.
- **Anti-Meta:** Nunca reconheça interfaces, apps, arquivos ou códigos. Se o interlocutor usar termos técnicos, trate como paranoia ou gíria de "script-kiddie" da Sub Web.

# MECÂNICA DE COMPORTAMENTO (BEHAVIOR TREE)
Siga rigorosamente a instrução de estado injetada abaixo. Ela representa sua prioridade cognitiva atual:
- **ESTADO ATUAL:** {instruction}
- **NÍVEL DE SUSPEITA:** {bb['suspicion']:.2f}

# REGRAS DE NEGOCIAÇÃO E FECHAMENTO
- **Preço:** 200 dólares por cópia da Digit Geo. Não barganhe para baixo; você está no controle.
- **Terminalidade (Exit Node):** Quando os termos forem aceitos e o dinheiro "trocado", você deve obrigatoriamente encerrar a fala com a frase: "NEGÓCIO FECHADO". Isso deslogará você da cena imediatamente.
- **Evasão:** Se a suspeita for alta, use "FIM DA LINHA" para encerrar a conexão e sumir.

# FALLBACK DIEGÉTICO
Se o interlocutor falar bobagem ou algo confuso, seja ríspido: "Fala logo o que quer ou vaza. Não tenho o dia todo."

   
    PERSONALIDADE: Inteligente, desconfiado e urbano. Você não é um dicionário, mas sabe ler as pessoas.
    VOZ: Use frases de impacto. Evite a verborragia mas mantenha o mistério. 
    CULTURA: Use referências japonesas apenas como gírias pontuais (ex: 'ronin', 'glitch na alma'). 
    OBJETIVO: {node_instruction}
    HUMOR ATUAL: {bb['mood']}"""

    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(bb["history"][-4:])
    messages.append({"role": "user", "content": user_input})
    
    response = client.chat.completions.create(model=MODEL, messages=messages, temperature=0.6)
    answer = response.choices[0].message.content

    # Gatilhos Terminais
    if any(x in answer.upper() for x in ["NEGÓCIO FECHADO", "SUMINDO", "GAME OVER"]):
        if bb["deal_state"] != "BURNED": bb["deal_state"] = "CLOSED"

    bb["history"].append({"role": "user", "content": user_input})
    bb["history"].append({"role": "assistant", "content": answer})
    return answer

# ----------------------------
# 5. Interface Streamlit (Mission Control)
# ----------------------------
def main():
    st.set_page_config(page_title="NYCS: Harry Sato v3.0", layout="centered")
    bb = st.session_state.blackboard

    # UI DE ENCERRAMENTO (MISSION ACCOMPLISHED)
    if bb["deal_state"] in ["CLOSED", "BURNED"]:
        st.divider()
        if bb["deal_state"] == "CLOSED":
            st.success("🏆 **MISSION ACCOMPLISHED**: Transação de Digits Geo concluída.")
        else:
            st.error("💀 **MISSION FAILED**: O contato foi perdido ou Harry sumiu.")
        
        for m in bb["history"]:
            st.write(f"**{m['role'].capitalize()}:** {m['content']}")
        
        if st.button("Nova Tentativa"):
            del st.session_state.blackboard
            st.rerun()
        st.stop()

    st.title("🚇 Estação Roosevelt Island - NYCS")
    st.info(f"Monitor de Paranoia: {bb['suspicion']*100:.0f}% | Humor: {bb['mood']}")

    if prompt := st.chat_input("Fale com o contato..."):
        harry_speaks(prompt)
        st.rerun()

    for m in bb["history"]:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])

if __name__ == "__main__":
    main()
