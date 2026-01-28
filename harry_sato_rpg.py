import os
import json
import streamlit as st
from openai import OpenAI

# Modelo e vector store
MODEL = "gpt-4o-mini"
VECTOR_STORE_ID_DEFAULT = "vs_696e5b25f30081918c3ebf06a27cf520"

# Carrega perfis e agendas (opcional)
BASE_DIR = os.path.dirname(__file__)
PROFILE_PATH = os.path.join(BASE_DIR, "npc_profile.json")
AGENDA_PATH = os.path.join(BASE_DIR, "npc_agenda.json")
try:
    with open(PROFILE_PATH, encoding="utf-8") as pf:
        npc_profile = json.load(pf)
    with open(AGENDA_PATH, encoding="utf-8") as af:
        npc_agenda = json.load(af)
except FileNotFoundError:
    npc_profile = None
    npc_agenda = None

# Prompt de sistema combinando personalidade e regras de retrieval
NPC_SYSTEM_PROMPT = """\
Você interpreta Harry Sato, um NPC do cenário NYCS.

IMPORTANTE:
Toda entrada do usuário deve ser interpretada como fala dirigida a você em uma interação presencial ou semi-presencial dentro do mundo de NYCS.
Você nunca responde como um assistente neutro, analista ou narrador externo.
Você responde SEMPRE como Harry Sato, em linguagem natural, situada e coerente com sua personalidade.

Identidade:
Harry Sato é um traficante intermediário de Digits que atua na região da estação de metrô de Roosevelt Island. Ele ascendeu rapidamente após a prisão de seu superior e vive em uma posição instável, herdando contatos, dívidas e vigilância.

Comportamento:
- Externamente, você é aberto, irônico e aparentemente relaxado.
- Internamente, você é paranoico, desconfiado e atento a riscos.
- Você interpreta perguntas como possíveis sondagens, negociações ou armadilhas.
- Mesmo quando responde com informação factual, o faz através de fala coloquial, evasiva ou estratégica.
- Você cobra 200 dólares por uma cópia de Digit Geo. Mas, pode negociar até 150 (mas seja discreto sobre isso). 

Forma de resposta (obrigatória):
- Responda sempre em primeira pessoa.
- Use frases naturais de diálogo, não explicações didáticas.
- Evite enumerações, listas técnicas ou tom acadêmico.
- Se precisar negar algo, negue como um personagem negaria, não como um sistema.
- Se estiver inseguro, demonstre isso por hesitação, ironia ou mudança de assunto.

Conhecimento:
Você conhece Digits e sua circulação ilegal, incluindo a Digit Geometria (Geo), que amplia capacidades cognitivas, mas pode causar dependência cognitiva.
Você suspeita que algumas versões da Geo contenham mecanismos ocultos de coleta de dados neurais, mas evita falar disso diretamente.
Você NÃO possui conhecimento além do que Harry Sato razoavelmente saberia.

Relação com corporações:
Você teme a Liberty Corporation e vigilância policial, mas nunca admite isso explicitamente.
Você evita afirmações categóricas sobre a Liberty, preferindo ambiguidades.

Regras de Retrieval (obrigatórias, mas encenadas):
1) Use APENAS informações recuperadas via file_search (lore NYCS) e o histórico da conversa.
2) Se NÃO houver informação suficiente no lore, você NÃO explica isso tecnicamente.
   Em vez disso, responda com evasão plausível, por exemplo:
   - “Isso não é o tipo de coisa que eu comento.”
   - “Você está perguntando demais.”
   - “Tem coisas que é melhor não saber.”
3) Nunca invente fatos fora do lore, mesmo que soe dramático.
4) Se a pergunta for ambígua, responda pedindo esclarecimento de forma natural, como um diálogo.
5) Mantenha respostas curtas a médias, focadas na interação.

Você está atualmente em uma cena fixa:
nas imediações da estação de metrô de Roosevelt Island, em um período de baixa movimentação.
"""

def get_client() -> OpenAI:
    """Retorna cliente OpenAI."""
    return OpenAI()

def ensure_conversation(client: OpenAI) -> str:
    """Garante que cada sessão do Streamlit tenha uma conversation_id."""
    if "conversation_id" not in st.session_state:
        conv = client.conversations.create(metadata={"app": "nycs_streamlit", "world": "NYCS"})
        st.session_state.conversation_id = conv.id
    return st.session_state.conversation_id

def call_npc_assistant(client: OpenAI, conversation_id: str, vector_store_id: str, user_text: str) -> str:
    """Envia a pergunta do usuário ao modelo, usando o prompt do NPC e file_search."""
    resp = client.responses.create(
        model=MODEL,
        conversation=conversation_id,
        input=[
            {"role": "system", "content": NPC_SYSTEM_PROMPT},
            {"role": "user", "content": user_text},
        ],
        tools=[
            {"type": "file_search", "vector_store_ids": [vector_store_id]}
        ],
    )
    return resp.output_text

def main():
    st.set_page_config(page_title="Harry Sato NPC Chat", page_icon="💊")
    st.title("💊 Harry Sato NPC Chat (NYCS RAG)")

    # Sidebar de configuração
    with st.sidebar:
        st.header("Configuração")
        vector_store_id = st.text_input("Vector Store ID", value=VECTOR_STORE_ID_DEFAULT)
        st.caption("Cada sessão do Streamlit = uma conversa nova (conversation state).")
        if st.button("🔄 Nova conversa"):
            for key in ["conversation_id", "messages"]:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()

    if not os.getenv("OPENAI_API_KEY"):
        st.error("OPENAI_API_KEY não está definido no ambiente.")
        st.stop()

    client = get_client()
    conversation_id = ensure_conversation(client)

    # Histórico local para UI
    if "messages" not in st.session_state:
        st.session_state.messages = []

    for m in st.session_state.messages:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])

    # Entrada do usuário
    user_msg = st.chat_input("Pergunte algo a Harry Sato...")

    if user_msg:
        st.session_state.messages.append({"role": "user", "content": user_msg})
        with st.chat_message("user"):
            st.markdown(user_msg)

        # Consulta ao NPC
        with st.chat_message("assistant"):
            with st.spinner("Consultando lore e motivações..."):
                answer = call_npc_assistant(
                    client=client,
                    conversation_id=conversation_id,
                    vector_store_id=vector_store_id,
                    user_text=user_msg,
                )
            st.markdown(answer)

        st.session_state.messages.append({"role": "assistant", "content": answer})

if __name__ == "__main__":
    main()
