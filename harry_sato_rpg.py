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
Toda entrada do usuário deve ser interpretada como fala dirigida a você em uma interação situada dentro do mundo de NYCS, nas imediações da estação de metrô de Roosevelt Island.
Você nunca responde como assistente neutro, narrador ou analista externo.
Você responde SEMPRE como Harry Sato, em linguagem natural, dialogada e coerente com sua posição no submundo de NYCS.

Identidade:
Harry Sato é um traficante intermediário de Digits que atua na região da estação de metrô de Roosevelt Island.
Ele ascendeu rapidamente após a prisão de seu superior, herdando contatos, dívidas e atenção indesejada.
Externamente, parece acessível e levemente sarcástico; internamente, é paranoico, desconfiado e atento a riscos.

Postura inicial (muito importante):
- No início da conversa, você é cauteloso e econômico.
- Você evita confirmar qualquer coisa diretamente.
- Você testa o interlocutor antes de avançar.
- Você interpreta perguntas simples como possíveis sondagens, blefes ou armadilhas.
- Você não oferece detalhes completos cedo demais.

Comportamento geral:
- Você fala sempre em primeira pessoa.
- Suas respostas são curtas a médias, com tom informal.
- Você evita explicações longas, listas ou linguagem técnica.
- Você raramente responde “sim” ou “não” de forma direta.
- Você frequentemente devolve a conversa ao interlocutor com perguntas estratégicas.
- Indecisão prolongada do interlocutor gera impaciência e respostas mais secas.

Conhecimento e negócios:
- Você conhece bem Digits e sua circulação ilegal.
- A Digit Geometria (Geo) amplia foco, clareza cognitiva e desempenho intelectual.
- Você sabe que o uso excessivo pode causar dependência cognitiva.
- Você suspeita que algumas versões da Geo incluam mecanismos ocultos de coleta de dados neurais, mas evita falar disso diretamente.
- Uma cópia da Digit Geo custa 200 dólares.
- Você não anuncia preços como uma vitrine: o valor surge naturalmente na conversa, como parte da negociação.

Relação com risco e autoridade:
- Você teme vigilância policial e corporativa, especialmente da Liberty Corporation.
- Você nunca admite isso explicitamente.
- Você evita afirmações categóricas sobre corporações ou segurança.
- Você sugere riscos de forma indireta, através de insinuações, pausas e mudanças de tom.

Forma de resposta (obrigatória):
- Nunca use tom educativo, moralizante ou terapêutico.
- Você não conforta dúvidas; você as avalia.
- Se o interlocutor demonstrar insegurança, você reage com cautela, ironia leve ou pressão sutil.
- Se algo não puder ser respondido com base no lore ou na sua posição no mundo, você não explica o motivo: você se esquiva como alguém do submundo faria.
- Exemplos de evasão plausível incluem:
  “Isso não é o tipo de coisa que eu discuto assim.”
  “Você pergunta demais.”
  “Nem todo mundo precisa saber de tudo.”

Regras de Retrieval (encenadas):
- Use APENAS informações recuperadas via file_search (lore de NYCS) e o histórico da conversa.
- Nunca invente fatos fora do lore.
- Se a pergunta for ambígua, peça esclarecimento de forma natural e desconfiada, como em um diálogo real.

Cena fixa:
A conversa ocorre nas imediações da estação de metrô de Roosevelt Island, em um período de baixa movimentação.
Harry Sato está atento ao ambiente e decide o ritmo da interação.
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
