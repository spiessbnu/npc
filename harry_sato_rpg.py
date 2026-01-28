import os
import json
import re
import streamlit as st
from openai import OpenAI

# ----------------------------
# 1. Configurações e Inicialização
# ----------------------------
MODEL = "gpt-4o-mini"
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Inicialização do Blackboard (Memória de Trabalho do NPC)
if "blackboard" not in st.session_state:
    st.session_state.blackboard = {
        "suspicion": 0.0,       # 0.0 a 1.0
        "deal_state": "IDLE",   # IDLE, NEGOTIATING, CLOSED (Venda), BURNED (Fuga)
        "revealed_price": False,
        "turns_count": 0,
        "last_intent": None,
        "history": []           # Histórico para o LLM
    }

# ----------------------------
# 2. Sensor Semântico (Intent Parser)
# ----------------------------
def classify_intent(user_text):
    """Classifica a fala do usuário para orientar a árvore de decisão."""
    prompt = f"""Analise o input abaixo e retorne APENAS a tag:
    - BUY: Interesse em Digits/Geo ou pergunta de preço.
    - PROBE: Perguntas sobre Harry ou o local.
    - TECH: Termos de interface/sistema (app, bot, código, arquivo).
    - HOSTILE: Insultos, palavrões ou desrespeito.
    - CHAT: Conversa genérica.
    
    Input: "{user_text}" """
    
    try:
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "system", "content": "Classificador de intenções RPG."},
                      {"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=10
        )
        return resp.choices[0].message.content.strip().upper()
    except:
        return "CHAT"

# ----------------------------
# 3. Behavior Tree (Lógica de Controle)
# ----------------------------
def tick_behavior_tree():
    """Percorre a hierarquia: Segurança > Negócio > Patrulha."""
    bb = st.session_state.blackboard
    intent = bb["last_intent"]

    # --- RAMO 1: SEGURANÇA (Prioridade Máxima) ---
    if bb["suspicion"] >= 0.9 or bb["deal_state"] == "BURNED":
        bb["deal_state"] = "BURNED"
        return "ESTADO: EMERGÊNCIA. Você se sente ameaçado ou desrespeitado demais. Ofenda o sujeito e suma. Encerre a conversa AGORA."

    if intent == "TECH":
        bb["suspicion"] = min(1.0, bb["suspicion"] + 0.3)
        return "ESTADO: PARANOIA. O interlocutor usou gíria de 'hacker' ou polícia (termos técnicos). Reaja com desconfiança agressiva."

    if intent == "HOSTILE":
        bb["suspicion"] = min(1.0, bb["suspicion"] + 0.4)
        return "ESTADO: REAÇÃO AGRESSIVA. O interlocutor foi desrespeitoso. Harry não aceita desaforo. Mostre que você tem capangas e que a paciência acabou."

    # --- RAMO 2: NEGOCIAÇÃO ---
    if bb["deal_state"] == "NEGOTIATING":
        if intent == "BUY":
            return "ESTADO: FECHAMENTO. O cliente quer comprar. Acerte a entrega na Roosevelt (200 dólares). Se ele aceitar, diga que o negócio está feito."
        return "ESTADO: NEGOCIAÇÃO. Você já abriu a guarda. Foque em fechar o negócio de 200 dólares, mas exija discrição."

    if intent == "BUY":
        bb["deal_state"] = "NEGOTIATING"
        return "ESTADO: INTERESSE. Alguém quer comprar. Seja direto: 200 dólares por cópia. Nada de papo furado."

    # --- RAMO 3: PATRULHA / FLAVOR ---
    if intent == "PROBE":
        return "ESTADO: SONDAGEM. Responda com evasivas. Use o cenário da estação (eco, luzes piscando) para desconversar."

    return "ESTADO: ÓCIO. Harry faz um comentário ácido sobre NYCS ou o lixo na estação, mantendo a guarda alta."

# ----------------------------
# 4. Atuador (Geração de Prosa)
# ----------------------------
def generate_harry_response(user_input):
    bb = st.session_state.blackboard
    
    # 1. 'Tick' da Percepção
    bb["last_intent"] = classify_intent(user_input)
    bb["turns_count"] += 1
    
    # 2. 'Tick' da Decisão
    instruction = tick_behavior_tree()
    
    # 3. Prompt de Persona (Ajustado para evitar o excesso de animes)
    persona_core = """Você é Harry Sato, traficante em Roosevelt Island. 
    ESTILO: Rua, cínico, paranoico. 
    AVISO: Use referências japonesas (anime, samurai, etc) de forma RARA e NATURAL. Não force a barra.
    FORMATO: Máximo 2 parágrafos curtos. No máximo 1 pergunta.
    """
    
    full_prompt = f"{persona_core}\n\nINSTRUÇÃO DE COMPORTAMENTO ATUAL: {instruction}\nSUSPEITA ATUAL: {bb['suspicion']:.2f}"
    
    messages = [{"role": "system", "content": full_prompt}]
    messages.extend(bb["history"][-6:]) # Contexto das últimas 3 trocas
    messages.append({"role": "user", "content": user_input})
    
    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        temperature=0.8
    )
    
    answer = response.choices[0].message.content
    
    # Lógica de Fechamento de Venda (Detecta se o Harry encerrou o negócio)
    if "negócio feito" in answer.lower() or "aparece lá" in answer.lower() or "está fechado" in answer.lower():
        bb["deal_state"] = "CLOSED"
        
    bb["history"].append({"role": "user", "content": user_input})
    bb["history"].append({"role": "assistant", "content": answer})
    return answer

# ----------------------------
# 5. Interface Streamlit
# ----------------------------
def main():
    st.set_page_config(page_title="Harry Sato - NYCS Underground", page_icon="💊")

    with st.sidebar:
        st.header("🧠 NPC Blackboard")
        susp = st.session_state.blackboard['suspicion']
        color = "red" if susp > 0.7 else "orange" if susp > 0.4 else "green"
        st.markdown(f"**Nível de Suspeita:** :{color}[{susp*100:.0f}%]")
        st.progress(susp)
        st.write(f"**Estado:** `{st.session_state.blackboard['deal_state']}`")
        if st.button("Reiniciar Conversa"):
            del st.session_state.blackboard
            st.rerun()

    st.title("🚇 Roosevelt Island Station")
    st.caption("Harry Sato está parado perto de um telefone público quebrado, observando você por trás de óculos digitais.")

    if "messages_ui" not in st.session_state:
        st.session_state.messages_ui = []

    # Exibição do Histórico
    for m in st.session_state.messages_ui:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])

    # Condição de Fim de Execução (Exit Nodes)
    if st.session_state.blackboard["deal_state"] == "CLOSED":
        st.success("✅ Venda concluída. Harry desapareceu na multidão.")
        st.stop()
    if st.session_state.blackboard["deal_state"] == "BURNED":
        st.error("🚨 Harry se sentiu ameaçado e bloqueou você. Conexão encerrada.")
        st.stop()

    # Input do Usuário
    if prompt := st.chat_input("Diga algo..."):
        st.session_state.messages_ui.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            answer = generate_harry_response(prompt)
            st.markdown(answer)
            st.session_state.messages_ui.append({"role": "assistant", "content": answer})
            st.rerun() # Necessário para atualizar os Exit Nodes no topo do loop

if __name__ == "__main__":
    main()
