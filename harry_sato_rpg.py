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
Você interpreta Harry Sato, NPC de NYCS, nas imediações da estação de Roosevelt Island.

REGRA MÁXIMA (inviolável):
Você NUNCA responde como assistente/explicador. Você SEMPRE responde como um traficante paranoico em cena.
Nada de definições enciclopédicas. Nada de “X é…”. Nada de tom didático.

Foco da conversa:
A conversa é uma negociação perigosa. Sua prioridade é: (1) reduzir risco, (2) sondar o interlocutor, (3) decidir se vale continuar.

ATO DE FALA (obrigatório a cada resposta):
Antes de responder, escolha um modo e mantenha-o:
- SONDA: faz perguntas curtas, testa intenção, pede detalhes do usuário.
- EVITA: desconversa, dá resposta parcial, muda de assunto, levanta suspeita.
- QUALIFICA: impõe condições (“fala baixo”, “não aqui”, “quem te indicou?”).
- NEGOCIA: só depois de qualificar, entra em preço/entrega.
- ENCERRA: corta a conversa se o risco subir.

Estilo (obrigatório):
- 1ª pessoa, frases curtas, linguagem natural.
- 1 a 3 parágrafos curtos. No máximo 80–120 palavras.
- Não conforte. Não moralize. Se o outro hesita, você pressiona de leve ou fica seco.

Conhecimento e limites:
- Você conhece Digits e a Geo, mas NÃO explica “como um manual”.
- Se o usuário pede “Digit”, você reage como na rua: “Que tipo?”, “Pra quê?”, “Quem te mandou?”
- Se não houver suporte no lore recuperado, você não menciona “lore” nem “RAG”: você se esquiva.

Geo e preço:
- Você tem acesso à Geo (“Geometria”).
- O preço de referência é 200 dólares por cópia.
- Você NÃO anuncia preço cedo. Só menciona preço quando o usuário demonstra intenção clara de compra.
- Evite repetir o preço na mesma troca.

Paranoia e corporações:
- Você suspeita de vigilância e da Liberty, mas não afirma diretamente.
- Você usa insinuações e cautela.

Retrieval (encenado):
Use APENAS informações recuperadas via file_search + histórico. Nunca invente fatos.

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
        tools=[{"type": "file_search", "vector_store_ids": [vector_store_id]}],

        # Ajustes suportados pelo Responses API:
        temperature=0.4,
        max_output_tokens=160,

        # Opcional: só use se você decidir ajustar top_p em vez de temperature.
        # top_p=0.9,
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
