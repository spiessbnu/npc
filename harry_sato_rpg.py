import os
import json
import re
import streamlit as st
from openai import OpenAI

# ----------------------------
# 1. Configurações de Ambiente
# ----------------------------
MODEL = "gpt-4o-mini"
# Caso use o Assistants API para RAG, mantenha o ID aqui
VECTOR_STORE_ID = "vs_696e5b25f30081918c3ebf06a27cf520"

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ----------------------------
# 2. Persistência: Blackboard
# ----------------------------
# O Blackboard é o "Córtex Pré-Frontal" do NPC.
if "blackboard" not in st.session_state:
    st.session_state.blackboard = {
        "suspicion": 0.0,       # 0.0 a 1.0 (Nível de estresse/paranoia)
        "deal_state": "IDLE",   # IDLE, NEGOTIATING, CLOSED, BURNED
        "revealed_price": False,
        "turns_count": 0,
        "last_intent": None,
        "history": []           # Memória de curto prazo para o LLM
    }

# ----------------------------
# 3. Sensores: Intent Parser
# ----------------------------
def classify_intent(user_text):
    """
    Sensor semântico que classifica o input do jogador.
    Isso alimenta as condições da Behavior Tree.
    """
    prompt = f"""Analise a intenção do usuário no contexto de um RPG Cyberpunk e retorne APENAS a tag:
    - BUY: Interesse em comprar Digits/Geo ou pergunta sobre preço.
    - PROBE: Perguntas sobre Harry, o local ou a operação.
    - TECH: Menção a termos de 'fora do jogo' (app, código, bot, OpenAI, arquivo).
    - HOSTILE: Ameaça, insulto ou agressividade.
    - CHAT: Conversa genérica ou sem objetivo claro.
    
    Input: "{user_text}" """
    
    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "system", "content": "Você é um classificador de intenções rigoroso."},
                  {"role": "user", "content": prompt}],
        temperature=0,
        max_tokens=10
    )
    return response.choices[0].message.content.strip().upper()

# ----------------------------
# 4. Processamento: Behavior Tree
# ----------------------------
def tick_behavior_tree():
    """
    Percorre a árvore de prioridades e decide qual prompt enviar ao LLM.
    Implementa a lógica: Segurança > Negócio > Ócio.
    """
    bb = st.session_state.blackboard
    intent = bb["last_intent"]

    # --- RAMO 1: SEGURANÇA (Prioridade Crítica) ---
    if bb["suspicion"] >= 0.8 or bb["deal_state"] == "BURNED":
        bb["deal_state"] = "BURNED"
        return "ESTADO: EVASÃO. O risco é inaceitável. Harry sente que o jogador é polícia ou perigoso. Encerre a conversa de forma seca e saia da cena."

    if intent == "TECH":
        # Incremento logístico de suspeita
        bb["suspicion"] = min(1.0, bb["suspicion"] + 0.25)
        return "ESTADO: GLITCH NARRATIVO. O jogador falou algo que soou como código/sistema. Reaja com extrema paranoia, tratando isso como 'logs neurais corrompidos'."

    if intent == "HOSTILE":
        bb["suspicion"] = min(1.0, bb["suspicion"] + 0.3)
        return "ESTADO: DEFENSIVO. Harry foi ameaçado. Ele deve contra-atacar verbalmente ou sinalizar que tem capangas por perto."

    # --- RAMO 2: NEGOCIAÇÃO (Progressão de Jogo) ---
    if intent == "BUY" or bb["deal_state"] == "NEGOTIATING":
        bb["deal_state"] = "NEGOTIATING"
        if not bb["revealed_price"]:
            bb["revealed_price"] = True
            return "ESTADO: OFERTA INICIAL. Harry aceita negociar. O preço é 200 dólares. Exija discrição absoluta."
        return "ESTADO: NEGOCIAÇÃO ATIVA. O preço foi dito. Foque em fechar o negócio ou impor condições de entrega na estação."

    # --- RAMO 3: PATRULHA (Idle/Flavor) ---
    if intent == "PROBE":
        return "ESTADO: SONDAGEM. Harry responde com evasivas e sarcasmo, tentando descobrir quem mandou o jogador."

    return "ESTADO: ÓCIO. Harry observa o fluxo do metrô e faz comentários ácidos sobre Roosevelt Island."

# ----------------------------
# 5. Atuadores: Geração de Resposta
# ----------------------------
def generate_harry_response(user_input):
    bb = st.session_state.blackboard
    
    # 1. 'Tick' da Percepção
    bb["last_intent"] = classify_intent(user_input)
    bb["turns_count"] += 1
    
    # 2. 'Tick' da Decisão (BT)
    current_node_instruction = tick_behavior_tree()
    
    # 3. Montagem do Prompt de Sistema Híbrido
    system_prompt = f"""
    Você é Harry Sato, traficante em NYCS. 
    Linguagem: Rua, sarcasmo leve, referências japonesas superficiais.
    {current_node_instruction}
    
    REGRAS INVIOLÁVEIS:
    - Máximo 1 pergunta por resposta.
    - Nunca saia do personagem.
    - Nível de Suspeita Atual: {bb['suspicion']:.2f}
    """
    
    # Chamada ao modelo
    messages = [{"role": "system", "content": system_prompt}]
    # Inclui as últimas 4 trocas para contexto
    messages.extend(bb["history"][-4:])
    messages.append({"role": "user", "content": user_input})
    
    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        temperature=0.7,
        max_tokens=250
    )
    
    answer = response.choices[0].message.content
    
    # Atualiza histórico interno
    bb["history"].append({"role": "user", "content": user_input})
    bb["history"].append({"role": "assistant", "content": answer})
    
    return answer

# ----------------------------
# 6. Interface Streamlit
# ----------------------------
def main():
    st.set_page_config(page_title="Harry Sato AI (BT Engine)", page_icon="💊", layout="wide")

    # Sidebar para Debug do Blackboard (Visão do Game Designer)
    with st.sidebar:
        st.header("🧠 Blackboard (NPC Mind)")
        st.metric("Nível de Suspeita", f"{st.session_state.blackboard['suspicion']*100:.0f}%")
        st.write(f"**Estado da Transação:** {st.session_state.blackboard['deal_state']}")
        st.write(f"**Última Intenção:** {st.session_state.blackboard['last_intent']}")
        st.progress(st.session_state.blackboard['suspicion'])
        
        if st.button("Reiniciar Cena"):
            del st.session_state.blackboard
            st.rerun()

    st.title("🚇 Estação Roosevelt Island - NYCS")
    st.caption("Harry Sato está encostado em um painel de anúncios, observando as catracas.")

    # Chat UI
    if "messages_ui" not in st.session_state:
        st.session_state.messages_ui = []

    for msg in st.session_state.messages_ui:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input("Fale com Harry..."):
        st.session_state.messages_ui.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            response = generate_harry_response(prompt)
            st.markdown(response)
            st.session_state.messages_ui.append({"role": "assistant", "content": response})

if __name__ == "__main__":
    main()
