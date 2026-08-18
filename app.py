import streamlit as st
from agent import ConfigurationError, run_agent_turn, SYSTEM_PROMPT

st.set_page_config(
    page_title="Trendly Help Center",
    page_icon="🛍️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================
#  Design system — storefront help center
# ============================================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

    :root {
        --bg:          #f6f6f8;
        --surface:     #ffffff;
        --border:      #e7e7ec;
        --text:        #191925;
        --text-dim:    #6d6d7e;
        --brand:       #ff5a3c;
        --brand-dark:  #e8482c;
        --brand-soft:  #fff1ed;
        --green:       #22b573;
    }

    html, body, [data-testid="stAppViewContainer"], .stApp {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
        background: var(--bg) !important;
        color: var(--text);
    }

    header[data-testid="stHeader"] { background: transparent !important; }
    footer, #MainMenu { visibility: hidden; }

    .block-container {
        max-width: 1120px !important;
        padding-top: 0 !important;
        padding-bottom: 8rem !important;
    }

    /* ---------- Storefront navbar (full-bleed) ---------- */
    .navbar {
        width: 100vw;
        margin-left: calc(50% - 50vw);
        background: var(--surface);
        border-bottom: 1px solid var(--border);
        box-shadow: 0 1px 6px rgba(20, 20, 40, 0.04);
    }
    .nav-inner {
        max-width: 1120px;
        margin: 0 auto;
        padding: 0.85rem 1.5rem;
        display: flex;
        align-items: center;
        gap: 2rem;
    }
    .brand {
        font-size: 1.45rem;
        font-weight: 800;
        letter-spacing: -0.03em;
        color: var(--text);
    }
    .brand span { color: var(--brand); }
    .nav-links {
        display: flex;
        gap: 1.4rem;
        font-size: 0.88rem;
        font-weight: 500;
        color: var(--text-dim);
        flex: 1;
    }
    .nav-links .active {
        color: var(--brand);
        font-weight: 700;
        border-bottom: 2px solid var(--brand);
        padding-bottom: 2px;
    }
    .nav-right { display: flex; align-items: center; gap: 1.1rem; font-size: 1.05rem; }
    .cart-wrap { position: relative; }
    .cart-badge {
        position: absolute;
        top: -7px; right: -9px;
        background: var(--brand);
        color: #fff;
        font-size: 0.6rem;
        font-weight: 700;
        border-radius: 999px;
        padding: 1px 5px;
    }

    /* ---------- Online status strip ---------- */
    .status-strip {
        width: 100vw;
        margin-left: calc(50% - 50vw);
        background: linear-gradient(90deg, var(--brand) 0%, #ff7a4d 100%);
        color: #fff;
        font-size: 0.8rem;
        font-weight: 600;
        text-align: center;
        padding: 0.45rem 1rem;
        letter-spacing: 0.01em;
        margin-bottom: 1.8rem;
    }

    /* ---------- Page heading ---------- */
    .page-head { margin-bottom: 1.3rem; }
    .page-head h1 {
        font-size: 1.7rem;
        font-weight: 800;
        letter-spacing: -0.02em;
        margin: 0 0 0.25rem;
        color: var(--text);
    }
    .page-head p { color: var(--text-dim); font-size: 0.92rem; margin: 0; }

    /* ---------- Messenger card ---------- */
    .chat-header {
        background: var(--surface);
        border: 1px solid var(--border);
        border-bottom: none;
        border-radius: 18px 18px 0 0;
        padding: 0.95rem 1.3rem;
        display: flex;
        align-items: center;
        gap: 0.85rem;
        box-shadow: 0 1px 4px rgba(20, 20, 40, 0.03);
    }
    .agent-avatar {
        width: 42px; height: 42px;
        border-radius: 50%;
        background: linear-gradient(135deg, var(--brand), #ff8a5c);
        color: #fff;
        font-weight: 800;
        font-size: 1.05rem;
        display: flex;
        align-items: center;
        justify-content: center;
        flex-shrink: 0;
    }
    .agent-name { font-weight: 700; font-size: 0.95rem; color: var(--text); }
    .agent-status {
        font-size: 0.76rem;
        color: var(--text-dim);
        display: flex;
        align-items: center;
        gap: 0.35rem;
        margin-top: 1px;
    }
    .online-dot {
        width: 8px; height: 8px;
        border-radius: 50%;
        background: var(--green);
        box-shadow: 0 0 0 3px rgba(34, 181, 115, 0.18);
    }
    .chat-header-right {
        margin-left: auto;
        font-size: 0.78rem;
        font-weight: 600;
        color: var(--text-dim);
        background: var(--bg);
        border: 1px solid var(--border);
        border-radius: 999px;
        padding: 0.3rem 0.8rem;
    }
    .chat-body-frame {
        background: var(--surface);
        border: 1px solid var(--border);
        border-top: 1px solid var(--border);
        border-radius: 0 0 18px 18px;
        padding: 1.1rem 1.1rem 0.4rem;
        margin-bottom: 1rem;
        box-shadow: 0 1px 4px rgba(20, 20, 40, 0.03);
    }
    .powered-by {
        text-align: center;
        color: #b3b3c0;
        font-size: 0.7rem;
        padding: 0.5rem 0 0.7rem;
    }

    /* ---------- Welcome card (empty state) ---------- */
    .welcome-card {
        background: var(--brand-soft);
        border: 1px solid #ffd9cf;
        border-radius: 14px;
        padding: 1.3rem 1.5rem;
        margin-bottom: 1rem;
    }
    .welcome-card h3 { margin: 0 0 0.4rem; font-size: 1.05rem; font-weight: 700; color: var(--text); }
    .welcome-card p { margin: 0; color: #7a5348; font-size: 0.88rem; line-height: 1.6; }
    .chips-label {
        color: var(--text-dim);
        font-size: 0.74rem;
        font-weight: 700;
        letter-spacing: 0.09em;
        text-transform: uppercase;
        margin: 0.3rem 0 0.6rem 0.2rem;
    }

    /* ---------- Chat bubbles ---------- */
    [data-testid="stChatMessage"] {
        background: transparent !important;
        border: none !important;
        padding: 0.15rem 0 !important;
        gap: 0.7rem;
    }
    [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]) [data-testid="stChatMessageContent"] {
        background: #f2f2f6;
        border: 1px solid #e9e9ef;
        border-radius: 4px 16px 16px 16px;
        padding: 0.85rem 1.05rem;
    }
    [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) {
        flex-direction: row-reverse;
    }
    [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) [data-testid="stChatMessageContent"] {
        background: linear-gradient(120deg, var(--brand), #ff7a4d);
        border-radius: 16px 4px 16px 16px;
        padding: 0.85rem 1.05rem;
        box-shadow: 0 3px 12px rgba(255, 90, 60, 0.25);
    }
    [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) [data-testid="stChatMessageContent"] p,
    [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) [data-testid="stChatMessageContent"] li {
        color: #fff !important;
    }
    [data-testid="stChatMessageContent"] p { color: var(--text); line-height: 1.6; }
    [data-testid="chatAvatarIcon-assistant"],
    [data-testid="chatAvatarIcon-user"] {
        background: var(--surface) !important;
        border: 1px solid var(--border);
        border-radius: 50% !important;
    }

    /* ---------- Chat input ---------- */
    div[data-testid="stChatInput"] > div {
        background: var(--surface) !important;
        border: 1px solid var(--border) !important;
        border-radius: 999px !important;
        box-shadow: 0 4px 16px rgba(20, 20, 40, 0.07);
        transition: border-color 0.2s ease, box-shadow 0.2s ease;
    }
    div[data-testid="stChatInput"] > div:focus-within {
        border-color: rgba(255, 90, 60, 0.55) !important;
        box-shadow: 0 0 0 3px rgba(255, 90, 60, 0.12), 0 4px 16px rgba(20, 20, 40, 0.07);
    }
    div[data-testid="stChatInput"] textarea {
        color: var(--text) !important;
        font-family: 'Inter', sans-serif !important;
    }
    div[data-testid="stChatInput"] textarea::placeholder { color: #a6a6b5 !important; }

    /* ---------- Buttons ---------- */
    .stButton > button {
        background: var(--surface) !important;
        border: 1px solid var(--border) !important;
        color: var(--text) !important;
        border-radius: 12px !important;
        font-weight: 600 !important;
        font-size: 0.85rem !important;
        padding: 0.55rem 1rem !important;
        text-align: left !important;
        transition: all 0.16s ease !important;
        box-shadow: 0 1px 3px rgba(20, 20, 40, 0.04);
    }
    .stButton > button:hover {
        border-color: var(--brand) !important;
        color: var(--brand) !important;
        background: var(--brand-soft) !important;
        transform: translateY(-1px);
    }
    .stButton > button:active { transform: translateY(0); }

    /* ---------- Right panel: help topics ---------- */
    .panel-card {
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: 16px;
        padding: 1.1rem 1.2rem;
        margin-bottom: 1rem;
        box-shadow: 0 1px 4px rgba(20, 20, 40, 0.03);
    }
    .panel-title {
        font-size: 0.76rem;
        font-weight: 700;
        letter-spacing: 0.09em;
        text-transform: uppercase;
        color: var(--text-dim);
        margin: 0 0 0.8rem;
    }
    .faq-item {
        padding: 0.55rem 0;
        border-bottom: 1px solid #f0f0f4;
        font-size: 0.86rem;
        font-weight: 500;
        color: var(--text);
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .faq-item:last-child { border-bottom: none; }
    .faq-item span.arrow { color: var(--brand); font-weight: 700; }
    .contact-card {
        background: linear-gradient(135deg, #23233a, #34345a);
        border: none;
        color: #fff;
    }
    .contact-card .panel-title { color: #b9b9d0; }
    .contact-card p { margin: 0.2rem 0; font-size: 0.85rem; color: #e6e6f2; }
    .contact-card .big { font-size: 1rem; font-weight: 700; color: #fff; }

    /* ---------- Sidebar ---------- */
    [data-testid="stSidebar"] {
        background: var(--surface) !important;
        border-right: 1px solid var(--border);
    }
    [data-testid="stSidebar"] .block-container { padding-top: 2rem !important; }
    .sidebar-title {
        font-size: 0.76rem;
        font-weight: 700;
        letter-spacing: 0.09em;
        text-transform: uppercase;
        color: var(--text-dim);
        margin: 0.3rem 0 0.8rem;
    }
    .order-card {
        display: flex;
        align-items: flex-start;
        gap: 0.6rem;
        background: var(--bg);
        border: 1px solid var(--border);
        border-radius: 12px;
        padding: 0.6rem 0.8rem;
        margin-bottom: 0.45rem;
        transition: border-color 0.16s ease, transform 0.16s ease;
    }
    .order-card:hover { border-color: var(--brand); transform: translateX(3px); }
    .order-dot {
        width: 8px; height: 8px;
        border-radius: 50%;
        margin-top: 5px;
        flex-shrink: 0;
    }
    .order-id { color: var(--brand); font-weight: 700; font-size: 0.84rem; }
    .order-desc { color: var(--text-dim); font-size: 0.76rem; line-height: 1.4; }
    .sidebar-footer {
        color: #a6a6b5;
        font-size: 0.72rem;
        text-align: center;
        margin-top: 1.2rem;
        line-height: 1.5;
    }

    /* ---------- Misc ---------- */
    [data-testid="stSpinner"] p { color: var(--text-dim) !important; }
    div[data-testid="stAlert"] { border-radius: 12px !important; }

    ::-webkit-scrollbar { width: 8px; height: 8px; }
    ::-webkit-scrollbar-thumb { background: #d4d4de; border-radius: 4px; }
    ::-webkit-scrollbar-track { background: transparent; }

    @media (max-width: 900px) {
        .nav-links { display: none; }
    }
</style>
""", unsafe_allow_html=True)

# ============================================================
#  Storefront navbar + status strip
# ============================================================
st.markdown("""
<div class="navbar">
    <div class="nav-inner">
        <div class="brand">Trendly<span>.</span></div>
        <div class="nav-links">
            <div>New In</div><div>Women</div><div>Men</div><div>Sale</div>
            <div class="active">Help Center</div>
        </div>
        <div class="nav-right">
            <div>🔍</div>
            <div class="cart-wrap">🛍️<span class="cart-badge">2</span></div>
        </div>
    </div>
</div>
<div class="status-strip">🟢 &nbsp;Support is online — average reply time under 2 minutes</div>
""", unsafe_allow_html=True)

st.markdown("""
<div class="page-head">
    <h1>Help Center</h1>
    <p>Track orders, start returns &amp; exchanges, or ask about shipping and refunds.</p>
</div>
""", unsafe_allow_html=True)

# ============================================================
#  Sidebar — order lookup
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
    "green":  "#22b573",
    "amber":  "#f0a020",
    "red":    "#e85454",
    "violet": "#8b6ff0",
}

with st.sidebar:
    st.markdown('<div class="sidebar-title">📦 My orders — sample IDs</div>', unsafe_allow_html=True)
    for oid, desc, tone in SAMPLE_ORDERS:
        st.markdown(
            f"""
            <div class="order-card">
                <span class="order-dot" style="background:{DOT_COLORS[tone]};
                    box-shadow: 0 0 6px {DOT_COLORS[tone]}55;"></span>
                <div>
                    <div class="order-id">{oid}</div>
                    <div class="order-desc">{desc}</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    st.markdown("<div style='height:0.6rem'></div>", unsafe_allow_html=True)
    if st.button("🔄  Start a new conversation", use_container_width=True):
        st.session_state.messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        st.session_state.pop("pending_prompt", None)
        st.rerun()
    st.markdown(
        '<div class="sidebar-footer">Trendly Help Center<br>Mon–Sat · 9am–9pm IST</div>',
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

HELP_TOPICS = [
    ("📦  Track my order", "Where is my order TR-4521?"),
    ("↩️  Start a return", "I want to return order TR-4530"),
    ("🔁  Exchange an item", "I want to exchange an item from order TR-4528"),
    ("💰  Refund status", "What's your refund policy?"),
]

POPULAR_QUESTIONS = [
    "How long does delivery take?",
    "What is the return window?",
    "Can I cancel my order?",
    "Do you offer Cash on Delivery?",
]


def handle_prompt(prompt: str):
    """Append the user turn, run the agent, and persist the result."""
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user", avatar=AVATARS["user"]):
        st.markdown(prompt)

    with st.chat_message("assistant", avatar=AVATARS["assistant"]):
        with st.spinner("Maya is typing…"):
            try:
                updated, reply = run_agent_turn(st.session_state.messages)
            except ConfigurationError as exc:
                st.session_state.messages.pop()
                st.error(str(exc))
                st.stop()
            except RuntimeError:
                st.session_state.messages.pop()
                st.error("The support service is temporarily unavailable. Please try again shortly.")
                st.stop()
        st.markdown(reply)
    st.session_state.messages = updated


# ============================================================
#  Main layout: messenger (left) + help topics (right)
# ============================================================
chat_col, side_col = st.columns([1.75, 1], gap="large")

has_chat = any(
    m["role"] in ("user", "assistant") and m.get("content")
    for m in st.session_state.messages
)

with chat_col:
    # Messenger header
    st.markdown("""
    <div class="chat-header">
        <div class="agent-avatar">M</div>
        <div>
            <div class="agent-name">Maya · Trendly Care</div>
            <div class="agent-status"><span class="online-dot"></span>Online — typically replies instantly</div>
        </div>
        <div class="chat-header-right">🎧 Support chat</div>
    </div>
    """, unsafe_allow_html=True)

    # Messenger body
    st.markdown('<div class="chat-body-frame">', unsafe_allow_html=True)

    if not has_chat:
        st.markdown("""
        <div class="welcome-card">
            <h3>👋 Hi! Maya here from Trendly Care.</h3>
            <p>
                I can track your orders, start a return or exchange, and walk you through
                our shipping and refund policies. Grab a sample order ID from the sidebar,
                or tap a quick start below.
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

    # Render history
    for m in st.session_state.messages:
        if m["role"] in ("user", "assistant") and m.get("content"):
            with st.chat_message(m["role"], avatar=AVATARS[m["role"]]):
                st.markdown(m["content"])

    st.markdown(
        '<div class="powered-by">Trendly Care · AI-assisted support · '
        'Conversation may be reviewed for quality</div>',
        unsafe_allow_html=True,
    )
    st.markdown('</div>', unsafe_allow_html=True)

with side_col:
    st.markdown("""
    <div class="panel-card">
        <div class="panel-title">Help topics</div>
    </div>
    """, unsafe_allow_html=True)
    # Buttons render right under the panel card header, styled as topic rows
    for i, (label, prompt_text) in enumerate(HELP_TOPICS):
        if st.button(label, key=f"topic_{i}", use_container_width=True):
            st.session_state.pending_prompt = prompt_text
            st.rerun()

    st.markdown('<div style="height:0.9rem"></div>', unsafe_allow_html=True)

    faq_html = "".join(
        f'<div class="faq-item">{q}<span class="arrow">›</span></div>'
        for q in POPULAR_QUESTIONS
    )
    st.markdown(f"""
    <div class="panel-card">
        <div class="panel-title">Popular questions</div>
        {faq_html}
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="panel-card contact-card">
        <div class="panel-title">Still stuck?</div>
        <p class="big">Talk to a human 💬</p>
        <p>✉️ care@trendly.in</p>
        <p>🕒 Mon–Sat · 9am–9pm IST</p>
    </div>
    """, unsafe_allow_html=True)

# ============================================================
#  Input: typed message or queued quick-prompt
# ============================================================
prompt = st.chat_input("Type your message — e.g. Where is my order TR-4521?")

if not prompt and st.session_state.get("pending_prompt"):
    prompt = st.session_state.pop("pending_prompt")

if prompt:
    handle_prompt(prompt)
    if st.session_state.get("pending_prompt") is None and not has_chat:
        st.rerun()
