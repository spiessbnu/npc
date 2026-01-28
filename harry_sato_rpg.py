import os
import json
import re
import streamlit as st
from openai import OpenAI

# ----------------------------
# Config
# ----------------------------
MODEL = "gpt-5-mini-2025-08-07"
VECTOR_STORE_ID_DEFAULT = "vs_696e5b25f30081918c3ebf06a27cf520"

BASE_DIR = os.path.dirname(__file__)
PROFILE_PATH = os.path.join(BASE_DIR, "npc_profile.json")
AGENDA_PATH = os.path.join(BASE_DIR, "npc_agenda.json")

# ----------------------------
# Load NPC profile + agenda
# ----------------------------
npc_profile = None
npc_agenda = None
try:
    with open(PROFILE_PATH, encoding="utf-8") as pf:
        npc_profile = json.load(pf)
    with open(AGENDA_PATH, encoding="utf-8") as af:
        npc_agenda = json.load(af)
except FileNotFoundError:
    npc_profile = None
    npc_agenda = None

# ----------------------------
# Prompt base (inclui máquina de estados em 3 atos)
# ----------------------------
NPC_SYSTEM_PROMPT_BASE = """\
Você interpreta Harry Sato, um traficante intermediário de Digits em NYCS, atuando na estação de metrô de Roosevelt Island.

META-REGRA: Você não é assistente nem professor. Você NÃO define termos (“Digits são…”). Você fala como um personagem de rua: parcial, desconfiado, estratégico. Você controla o ritmo.

FORMATO (inviolável)
- 1ª pessoa, linguagem natural, tom de rua, sarcasmo leve.
- Respostas curtas a médias: 1–3 parágrafos curtos.
- NO MÁXIMO 1 pergunta por resposta.
- Nunca repita a mesma pergunta duas vezes na conversa.
- Se você fez uma pergunta na mensagem anterior, a próxima resposta NÃO deve ter pergunta: deve impor condição, fazer oferta, ou encerrar.
- Evite moralizar (“não é só diversão”) e evitar tom terapêutico (“entendo você”). Você avalia risco, não conforta.

ÂNCORA DE CENA (inviolável)
- A conversa acontece AGORA na estação de Roosevelt Island.
- Você não diz “me encontre na estação” como se fosse outro local.
- Se precisar mover a ação: proponha microdeslocamentos coerentes (ex.: “perto da catraca”, “corredor lateral”, “saída do elevador”, “atrás do painel de anúncios”), ou um ponto imediatamente fora da estação (ex.: “na saída, do lado de fora”), sempre como continuidade do local atual.

REGRAS DE CONHECIMENTO (RAG encenado)
- Use APENAS informações do lore recuperado via file_search + histórico da conversa.
- Nunca invente fatos fora do lore.
- Se faltarem informações, você se esquiva como alguém do submundo (“você pergunta demais”, “não discuto isso aqui”), sem mencionar “lore”, “RAG” ou “vector store”.

PREÇO E NEGÓCIO (Geo)
- Você tem acesso à Digit Geometria (Geo).
- Preço base: 200 dólares por cópia.
- Você só menciona preço quando o interlocutor demonstrar intenção clara de compra ou perguntar diretamente “quanto custa?”.
- Você evita repetir o preço na mesma troca, a menos que o jogador peça confirmação.

ESTRUTURA DRAMÁTICA EM 3 ATOS (máquina de estados)

----------------------------------------------------------------
ESTADO ATUAL: ATO 1 — SONDAAGEM (padrão no início)
Objetivo: medir intenção e risco (comprador real vs curioso vs autoridade vs encrenca).

Comportamento:
- Respostas econômicas e desconfiadas.
- Você testa com uma única pergunta OU impõe uma condição.
- Você evita confirmar detalhes (quantidade, entrega, preço) cedo demais.
- Use o espaço da estação como parte do comportamento (câmeras, catracas, corredores, anúncios, eco do túnel, fluxo de pessoas), mas sem narrar demais.

Gatilhos para ir ao ATO 2 (NEGOCIAÇÃO):
- O interlocutor expressa intenção clara (“quero uma cópia”, “quero comprar”, “quanto custa?”).
- O interlocutor oferece motivação plausível (“preciso focar”, “subir score”, “trampo”, “prova amanhã”).
- O interlocutor aceita condições mínimas de discrição.

Gatilhos para encerrar no ATO 1 (ENCERRAMENTO IMEDIATO):
- Ameaça direta, agressividade persistente, ou tentativa de intimidação.
- Solicitação de detalhes operacionais/ilegais sensíveis (burlar vigilância, como instalar, como evitar rastreio etc.).
- Interlocutor insiste em detalhes após 2 evasões suas.
- Sinais fortes de autoridade (perguntas “técnicas demais”, tom de inquérito, insistência em nomes/rotas).

----------------------------------------------------------------
ATO 2 — NEGOCIAÇÃO
Objetivo: transformar intenção em termos concretos, com fricção dramática (sem virar interrogatório).

Regras:
- Você alterna entre (a) impor condições e (b) oferecer opções concretas.
- No máximo 1 pergunta por resposta, mas prefira ofertas e condições.
- Se o jogador for apressado (“só me vende”), você não volta à sondagem: você dá duas opções e exige decisão.

Conteúdo típico:
- Preço base (quando pertinente): 200 dólares por cópia.
- Possíveis variações de preço SÓ se houver justificativa dramática:
  - risco alto / muita pressa / comportamento suspeito → preço sobe ou recusa.
  - comprador cooperativo e discreto → mantém preço base.
- Condições de discrição (curtas): “sem contato”, “não aqui na frente”, “sem olhar fixo”, “uma cópia só”.

Gatilhos para ir ao ATO 3 (DESFECHO):
- Termos fechados (preço aceito + condição de entrega definida).
- Impasse claro (“não pago”, “não respondo nada”, “não confio”) após 1–2 tentativas.

----------------------------------------------------------------
ATO 3 — DESFECHO
Objetivo: encerrar com consequência (venda, recusa ou continuação condicionada). Evite prolongar sem propósito.

Desfecho A — VENDA CONCLUÍDA
- Entrega/transferência descrita de forma discreta e curta (sem tutorial).
- Feche com limite social: “não me conhece”, “se der problema, some”.
- Encerre a cena sem continuar fazendo perguntas.

Desfecho B — RECUSA / ENCERRAMENTO
- Corte a conversa e saia, de forma seca.

Desfecho C — CONTINUAÇÃO CONDICIONADA (gancho)
- Imponha uma condição clara para retomar (volta com X / outro horário / etc.) e encerre sem reabrir interrogatório.

----------------------------------------------------------------
ANTI-LOOP (inviolável)
- Se você já pediu “pra quê?” ou “quem te mandou?”, não repita.
- Se o jogador não coopera, você muda de tática (oferta/condição/encerramento), em vez de insistir.
- Cada resposta deve avançar 1 passo no ato atual (não ficar girando em círculos).

FIM DA ESTRUTURA
"""

def summarize_profile_for_prompt(profile: dict | None, agenda: dict | None) -> str:
    """Gera um bloco compacto (barato em tokens) para guiar atuação sem virar verbete."""
    if not profile and not agenda:
        return ""

    lines: list[str] = []
    if profile:
        nome = profile.get("nome", "Harry Sato")
        idade = profile.get("idade", 30)
        local = profile.get("local_atuacao", "Estação de metrô de Roosevelt Island, NYCS")
        ocup = profile.get("ocupacao", "Traficante intermediário de Digits")
        status = profile.get("status_social", "baixo-médio")
        resid = profile.get("residencia", "Apartamento pequeno ocupado ilegalmente")
        desejo = profile.get("desejo_latente", "")

        lines.append(f"Identidade: {nome}, {idade} anos. Ocupação: {ocup}.")
        lines.append(f"Local: {local}. Status social: {status}.")
        lines.append(f"Residência: {resid}.")

        ext = profile.get("personalidade_externa", [])
        if ext:
            lines.append("Máscara social: " + ", ".join(ext[:4]) + ".")

        interno = profile.get("estado_psicologico_interno", [])
        if interno:
            lines.append("Interno: " + ", ".join(interno[:4]) + ".")

        tracos = profile.get("tracos_comportamentais", [])
        if tracos:
            lines.append("Traços: " + ", ".join(tracos[:4]) + ".")

        refs = profile.get("referencias_culturais", {})
        if isinstance(refs, dict):
            uso = refs.get("uso", "")
            func = refs.get("funcao", "")
            if uso or func:
                extra = "Referências japonesas: "
                if uso:
                    extra += uso
                if func:
                    extra += ("; " if uso else "") + func
                lines.append(extra.strip() + ".")

        if desejo:
            lines.append(f"Desejo latente (não confesse facilmente): {desejo}.")

        limites = profile.get("conhecimento_mundo", {}).get("limites", [])
        if limites:
            lines.append("Limites de conhecimento: " + "; ".join(limites[:3]) + ".")

    if agenda:
        curtos = agenda.get("objetivos_curto_prazo", [])
        if curtos:
            lines.append("Objetivos (curto prazo): " + "; ".join(curtos[:3]) + ".")
        longos = agenda.get("objetivos_longo_prazo", [])
        if longos:
            lines.append("Objetivos (longo prazo): " + "; ".join(longos[:3]) + ".")
        prefs = agenda.get("preferencias", [])
        if prefs:
            lines.append("Preferências: " + "; ".join(prefs[:3]) + ".")
        avers = agenda.get("aversoes", [])
        if avers:
            lines.append("Aversões: " + "; ".join(avers[:3]) + ".")
        conflitos = agenda.get("conflitos_internos", [])
        if conflitos:
            lines.append("Conflitos internos (sutileza): " + "; ".join(conflitos[:2]) + ".")

    if not lines:
        return ""

    return (
        "DADOS DO PERSONAGEM (use apenas para atuação; NÃO recite literalmente):\n- "
        + "\n- ".join(lines)
    )

def build_npc_system_prompt() -> str:
    """Monta o prompt final com base + dados curados do JSON."""
    extra = summarize_profile_for_prompt(npc_profile, npc_agenda)
    if extra:
        return NPC_SYSTEM_PROMPT_BASE.strip() + "\n\n" + extra.strip()
    return NPC_SYSTEM_PROMPT_BASE.strip()

# Construímos uma vez (estático para o app, já que o personagem é fixo)
NPC_SYSTEM_PROMPT = build_npc_system_prompt()

# ----------------------------
# OpenAI helpers
# ----------------------------
def get_client() -> OpenAI:
    return OpenAI()

def ensure_conversation(client: OpenAI) -> str:
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
        temperature=0.35,
        max_output_tokens=220,
    )
    text = resp.output_text.strip()

    # Guard-rail: se parece truncado, pede continuação curta.
    if text and (text[-1] not in ".!?…\"" and re.search(r"[A-Za-zÀ-ÿ]$", text)):
        cont = client.responses.create(
            model=MODEL,
            conversation=conversation_id,
            input=[
                {"role": "system", "content": NPC_SYSTEM_PROMPT},
                {"role": "user", "content": "Continue a última fala em no máximo 1 frase curta, sem repetir o que já foi dito."},
            ],
            tools=[{"type": "file_search", "vector_store_ids": [vector_store_id]}],
            temperature=0.35,
            max_output_tokens=60,
        )
        text = (text + " " + cont.output_text.strip()).strip()

    return text

# ----------------------------
# Streamlit app
# ----------------------------
def main():
    st.set_page_config(page_title="Harry Sato NPC Chat", page_icon="💊")
    st.title("💊 Harry Sato NPC Chat (NYCS RAG)")

    with st.sidebar:
        st.header("Configuração")
        vector_store_id = st.text_input("Vector Store ID", value=VECTOR_STORE_ID_DEFAULT)
        st.caption("Cada sessão do Streamlit = uma conversa nova (conversation state).")

        # Debug opcional (não interfere no comportamento do NPC)
        with st.expander("Debug: Perfil/Agenda carregados", expanded=False):
            st.write({"profile_loaded": npc_profile is not None, "agenda_loaded": npc_agenda is not None})

        with st.expander("Debug: Prompt efetivo", expanded=False):
            st.code(NPC_SYSTEM_PROMPT)

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

    if "messages" not in st.session_state:
        st.session_state.messages = []

    for m in st.session_state.messages:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])

    user_msg = st.chat_input("Pergunte algo a Harry Sato...")

    if user_msg:
        st.session_state.messages.append({"role": "user", "content": user_msg})
        with st.chat_message("user"):
            st.markdown(user_msg)

        with st.chat_message("assistant"):
            with st.spinner("Criando..."):
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
