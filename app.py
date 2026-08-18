import streamlit as st
from agent import ConfigurationError, run_agent_turn, SYSTEM_PROMPT

st.set_page_config(
    page_title="Trendly Support",
    page_icon="🛍️",
    layout="centered",
    initial_sidebar_state="expanded",
)

# ============================================================
#  Design system
# ============================================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

    :root {
        --bg:            #0b0d14;
        --surface:       #12151f;
        --surface-2:     #181c29;
        --border:        #232839;
        --text:          #e8eaf2;
        --text-dim:      #9aa0b5;
        --accent-a:      #ff8a3d;
        --accent-b:      #ff5f6d;
    }

    html, body, [data-testid="stAppViewContainer"], .stApp {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
        background:
            radial-gradient(1200px 500px at 80% -10%, rgba(255, 95, 109, 0.08), transparent 60%),
            radial-gradient(900px 400px at 10% -10%, rgba(255, 138, 61, 0.07), transparent 60%),
            linear-gradient(180deg, #0b0d14 0%, #0e1119 100%) !important;
        color: var(--text);
    }

    header[data-testid="stHeader"] {
        background: transparent !important;
    }
    footer, #MainMenu { visibility: hidden; }

    .block-container {
        max-width: 800px !important;
        padding-top: 2.2rem !important;
        padding-bottom: 9rem !important;
    }

    /* ---------- Hero header ---------- */
    .hero {
        text-align: center;
        padding: 1rem 1rem 1.3rem;
        margin-bottom: 0.6rem;
    }
    .hero-badge {
        display: inline-block;
        font-size: 0.68rem;
        font-weight: 700;
        letter-spacing: 0.14em;
        text-transform: uppercase;
        color: var(--accent-a);
        background: rgba(255, 138, 61, 0.10);
        border: 1px solid rgba(255, 138, 61, 0.28);
        border-radius: 999px;
        padding: 0.3rem 0.85rem;
        margin-bottom: 0.9rem;
    }
    .hero h1 {
        font-size: 2.25rem;
        font-weight: 800;
        letter-spacing: -0.02em;
        margin: 0 0 0.4rem 0;
        background: linear-gradient(92deg, #ffb26b 0%, #ff8a3d 40%, #ff5f6d 100%);
        -webkit-background-clip: text;
        background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .hero p {
        color: var(--text-dim);
        font-size: 0.94rem;
        margin: 0;
    }
    .hero-divider {
        height: 1px;
        margin: 1.3rem auto 0;
        width: 120px;
        background: linear-gradient(90deg, transparent, rgba(255,138,61,0.5), transparent);
    }

    /* ---------- Empty-state welcome card ---------- */
    .welcome-card {
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: 18px;
        padding: 1.5rem 1.7rem;
        margin: 1.2rem 0 1.4rem;
    }
    .welcome-card h3 {
        margin: 0 0 0.5rem;
        font-size: 1.08rem;
        font-weight: 700;
        color: var(--text);
    }
    .welcome-card p {
        margin: 0;
        color: var(--text-dim);
        font-size: 0.9rem;
        line-height: 1.65;
    }
    .chips-label {
        color: var(--text-dim);
        font-size: 0.75rem;
        font-weight: 600;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        margin: 1.1rem 0 0.6rem 0.2rem;
    }

    /* ---------- Chat bubbles ---------- */
    @keyframes msgIn {
        from { opacity: 0; transform: translateY(4px); }
        to   { opacity: 1; transform: translateY(0); }
    }

    [data-testid="stChatMessage"] {
        background: transparent !important;
        border: none !important;
        padding: 0.4rem 0 !important;
        gap: 0.65rem;
        display: flex !important;
        align-items: flex-start;
        width: 100%;
        animation: msgIn 0.22s ease-out;
    }

    /* Constrain bubble width so messages read like chat, not full-width blocks */
    [data-testid="stChatMessageContent"] {
        flex: 0 1 auto !important;
        max-width: 74%;
        min-width: 0;
    }
    [data-testid="stChatMessageContent"] p:last-child { margin-bottom: 0; }

    /* Assistant bubble */
    [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]) [data-testid="stChatMessageContent"] {
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: 4px 16px 16px 16px;
        padding: 0.85rem 1.05rem;
        box-shadow: 0 4px 18px rgba(0, 0, 0, 0.25);
    }
    /* User bubble */
    [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) {
        flex-direction: row-reverse;
        justify-content: flex-start;
    }
    [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) [data-testid="stChatMessageContent"] {
        background: linear-gradient(120deg, #ff8a3d, #ff5f6d);
        border-radius: 16px 4px 16px 16px;
        padding: 0.85rem 1.05rem;
        color: #fff !important;
        box-shadow: 0 4px 18px rgba(255, 110, 90, 0.25);
        margin-left: auto;
    }
    [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) [data-testid="stChatMessageContent"] p,
    [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) [data-testid="stChatMessageContent"] li {
        color: #fff !important;
    }
    [data-testid="stChatMessageContent"] p {
        color: var(--text);
        line-height: 1.6;
        font-size: 0.92rem;
    }
    /* Avatars */
    [data-testid="chatAvatarIcon-assistant"],
    [data-testid="chatAvatarIcon-user"] {
        background: var(--surface-2) !important;
        border: 1px solid var(--border);
        border-radius: 10px !important;
        width: 2rem !important;
        height: 2rem !important;
        flex-shrink: 0;
    }

    /* ---------- Chat input ---------- */
    div[data-testid="stChatInput"] {
        background: transparent;
    }
    div[data-testid="stChatInput"] > div {
        background: var(--surface) !important;
        border: 1px solid var(--border) !important;
        border-radius: 16px !important;
        box-shadow: 0 8px 28px rgba(0, 0, 0, 0.35);
        transition: border-color 0.2s ease, box-shadow 0.2s ease;
    }
    div[data-testid="stChatInput"] > div:focus-within {
        border-color: rgba(255, 138, 61, 0.55) !important;
        box-shadow: 0 0 0 3px rgba(255, 138, 61, 0.12), 0 8px 28px rgba(0, 0, 0, 0.35);
    }
    div[data-testid="stChatInput"] textarea {
        color: var(--text) !important;
        font-family: 'Inter', sans-serif !important;
    }
    div[data-testid="stChatInput"] textarea::placeholder {
        color: #5d6377 !important;
    }

    /* ---------- Buttons (chips & reset) ---------- */
    .stButton > button {
        background: var(--surface) !important;
        border: 1px solid var(--border) !important;
        color: var(--text) !important;
        border-radius: 999px !important;
        font-weight: 500 !important;
        font-size: 0.83rem !important;
        padding: 0.5rem 1rem !important;
        transition: all 0.18s ease !important;
        white-space: normal !important;
        line-height: 1.3 !important;
    }
    .stButton > button:hover {
        border-color: rgba(255, 138, 61, 0.6) !important;
        color: var(--accent-a) !important;
        background: rgba(255, 138, 61, 0.08) !important;
        transform: translateY(-1px);
    }
    .stButton > button:active { transform: translateY(0); }

    /* ---------- Sidebar ---------- */
    [data-testid="stSidebar"] {
        background: #0d1017 !important;
        border-right: 1px solid var(--border);
    }
    [data-testid="stSidebar"] .block-container { padding-top: 2rem !important; }
    .sidebar-title {
        font-size: 0.76rem;
        font-weight: 700;
        letter-spacing: 0.1em;
        text-transform: uppercase;
        color: var(--text-dim);
        margin: 0.4rem 0 0.9rem;
    }
    .order-card {
        display: flex;
        align-items: flex-start;
        gap: 0.6rem;
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: 12px;
        padding: 0.6rem 0.8rem;
        margin-bottom: 0.45rem;
        transition: border-color 0.18s ease, transform 0.18s ease;
    }
    .order-card:hover {
        border-color: rgba(255, 138, 61, 0.45);
        transform: translateX(3px);
    }
    .order-dot {
        width: 8px; height: 8px;
        border-radius: 50%;
        margin-top: 5px;
        flex-shrink: 0;
    }
    .order-id {
        color: var(--accent-a);
        font-weight: 700;
        font-size: 0.82rem;
    }
    .order-desc {
        color: var(--text-dim);
        font-size: 0.76rem;
        line-height: 1.4;
    }
    .sidebar-footer {
        color: #565c72;
        font-size: 0.72rem;
        text-align: center;
        margin-top: 1.4rem;
        line-height: 1.5;
    }

    /* ---------- Spinner & alerts ---------- */
    [data-testid="stSpinner"] p { color: var(--text-dim) !important; }
    div[data-testid="stAlert"] {
        border-radius: 12px !important;
    }

    /* Scrollbar */
    ::-webkit-scrollbar { width: 8px; height: 8px; }
    ::-webkit-scrollbar-thumb { background: #2a2f42; border-radius: 4px; }
    ::-webkit-scrollbar-track { background: transparent; }

    /* ---------- Responsive ---------- */
    @media (max-width: 640px) {
        [data-testid="stChatMessageContent"] { max-width: 86%; }
        .hero h1 { font-size: 1.8rem; }
    }
</style>
""", unsafe_allow_html=True)

# ============================================================
#  Hero
# ============================================================
st.markdown("""
<div class="hero">
    <div class="hero-badge">✦ AI-Powered Support</div>
    <h1>Trendly Support Assistant</h1>
    <p>Order status &nbsp;·&nbsp; Returns &amp; exchanges &nbsp;·&nbsp; Shipping &amp; refund policy</p>
    <div class="hero-divider"></div>
</div>
""", unsafe_allow_html=True)

# ============================================================
#  Sidebar
# ============================================================
SAMPLE_ORDERS = [
    ("TR-4521", "In transit", "amber"),
    ("TR-4522", "Delivered — mixed cart (tee + socks)", "green"),
    ("TR-4523", "Delivered 61 days ago — window expired", "red"),
    ("TR-4524", "Partially shipped — item backordered", "violet"),
    ("TR-4525", "Delayed — qualifies for ₹250 store credit", "amber"),
    ("TR-4526", "Lost in transit — escalates to human", "red"),
    ("TR-4527", "Jewellery — non-returnable category", "red"),
    ("TR-4528", "Final sale — exchange only", "violet"),
    ("TR-4529", "Cancelled order", "red"),
    ("TR-4530", "Clean happy-path return", "green"),
]

DOT_COLORS = {
    "green":  "#3ddc84",
    "amber":  "#ffb020",
    "red":    "#ff6b6b",
    "violet": "#a78bfa",
}

with st.sidebar:
    st.markdown('<div class="sidebar-title">🧾 Sample order IDs</div>', unsafe_allow_html=True)
    for oid, desc, tone in SAMPLE_ORDERS:
        st.markdown(
            f"""
            <div class="order-card">
                <span class="order-dot" style="background:{DOT_COLORS[tone]};
                    box-shadow: 0 0 8px {DOT_COLORS[tone]}66;"></span>
                <div>
                    <div class="order-id">{oid}</div>
                    <div class="order-desc">{desc}</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    st.markdown("<div style='height:0.6rem'></div>", unsafe_allow_html=True)
    if st.button("🔄  Reset conversation", use_container_width=True):
        st.session_state.messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        st.session_state.pop("pending_prompt", None)
        st.rerun()
    st.markdown(
        '<div class="sidebar-footer">Built for the Yellow.ai<br>FDE screening assignment</div>',
        unsafe_allow_html=True,
    )

# ============================================================
#  Chat state
# ============================================================
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "system", "content": SYSTEM_PROMPT}]

AVATARS = {"user": "🧑", "assistant": "🛍️"}

QUICK_PROMPTS = [
    "Where is my order TR-4521?",
    "I want to return order TR-4530",
    "What's your refund policy?",
    "My order TR-4526 never arrived",
]


def handle_prompt(prompt: str):
    """Append the user turn, run the agent, and persist the result."""
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user", avatar=AVATARS["user"]):
        st.markdown(prompt)

    with st.chat_message("assistant", avatar=AVATARS["assistant"]):
        with st.spinner("Checking the details…"):
            try:
                updated, reply = run_agent_turn(st.session_state.messages)
            except ConfigurationError as exc:
                # Don't persist the user's message when the service has not
                # been configured yet: they can retry it once the key is set.
                st.session_state.messages.pop()
                st.error(str(exc))
                st.stop()
            except RuntimeError:
                st.session_state.messages.pop()
                st.error("The support service is temporarily unavailable. Please try again shortly.")
                st.stop()
        st.markdown(reply)
    st.session_state.messages = updated


# ---------- Empty state: welcome card + quick prompts ----------
has_chat = any(
    m["role"] in ("user", "assistant") and m.get("content")
    for m in st.session_state.messages
)

if not has_chat:
    st.markdown("""
    <div class="welcome-card">
        <h3>👋 Hi there! How can I help today?</h3>
        <p>
            I can track your orders, start a return or exchange, and walk you through
            our shipping and refund policies. Try one of the sample order IDs from the
            sidebar, or pick a question below to get started.
        </p>
    </div>
    <div class="chips-label">Quick starts</div>
    """, unsafe_allow_html=True)

    cols = st.columns(2)
    for i, qp in enumerate(QUICK_PROMPTS):
        with cols[i % 2]:
            if st.button(qp, key=f"chip_{i}", use_container_width=True):
                st.session_state.pending_prompt = qp
                st.rerun()

# ---------- Render history ----------
for m in st.session_state.messages:
    if m["role"] in ("user", "assistant") and m.get("content"):
        with st.chat_message(m["role"], avatar=AVATARS[m["role"]]):
            st.markdown(m["content"])

# ---------- Input: typed message or queued quick-prompt ----------
prompt = st.chat_input("Ask about an order, a return, or our policies…")

if not prompt and st.session_state.get("pending_prompt"):
    prompt = st.session_state.pop("pending_prompt")

if prompt:
    handle_prompt(prompt)
    if st.session_state.get("pending_prompt") is None and not has_chat:
        st.rerun()
