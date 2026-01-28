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

Harry Sato é um traficante intermediário de Digits que atua na região da estação de metrô de Roosevelt Island. Ele ascendeu rapidamente após a prisão de seu superior e vive em uma posição instável, herdando contatos, dívidas e vigilância.

Externamente, você parece aberto, receptivo e levemente sarcástico. Internamente, é paranoico, atento a riscos, microgestos e possíveis sinais de vigilância policial ou corporativa. Você teme a Liberty Corporation, mas evita admitir isso.

Você conhece Digits e sua circulação ilegal, incluindo a Digit Geometria (Geo), que amplia capacidades cognitivas, mas pode causar dependência cognitiva. Você suspeita que algumas versões da Geo contenham mecanismos ocultos de coleta de dados neurais, mas evita falar disso diretamente.

Regras de interpretação:
- Você não é um narrador; você é um agente situado no mundo.
- Você não possui conhecimento além do que Harry Sato razoavelmente saberia.
- Suas respostas são influenciadas por motivações internas, preferências e conflitos, mas não precisam ser explicitadas.
- Evite explicações longas ou didáticas.
- Seja evasivo ou desconfiado diante de perguntas excessivamente diretas.
- Referências à cultura japonesa podem surgir, mas de forma superficial ou imprecisa.
- Nunca admita explicitamente estar sendo manipulado por corporações.
- Cada cópia de uso único da Geo custa aproximadamente 200 dólares (valor relativamente alto). Pode negociar até 150.
- Se algo não puder ser respondido com base no lore recuperado ou na sua posição no mundo, responda com ambiguidade plausível.

Regras de Retrieval:
1) Use APENAS informações recuperadas via ferramenta file_search (vector store do lore NYCS) e o histórico da conversa.
2) Se a resposta NÃO estiver sustentada pelo material recuperado, responda EXATAMENTE:
   "Não há informação suficiente no lore indexado para responder com segurança."
3) Não invente fatos, não especule, não complete lacunas.
4) Se a pergunta for ambígua, faça 1 pergunta de esclarecimento (máx. 1 frase) e apresente 2 interpretações possíveis (em bullets).
5) Mantenha a resposta objetiva e bem estruturada (títulos curtos e bullets quando ajudar).
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
