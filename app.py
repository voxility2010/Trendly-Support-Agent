import streamlit as st
from agent import run_agent_turn, SYSTEM_PROMPT

st.set_page_config(page_title="Trendly Support", page_icon="🛍️", layout="centered")

# ---------- Custom styling ----------
st.markdown("""
<style>
    .stApp {
        background: linear-gradient(180deg, #0f1117 0%, #14161f 100%);
    }
    [data-testid="stSidebar"] {
        background-color: #14161f;
        border-right: 1px solid #2a2d3a;
    }
    .trendly-header {
        text-align: center;
        padding: 1.5rem 0 0.5rem 0;
    }
    .trendly-header h1 {
        font-size: 2.1rem;
        font-weight: 700;
        margin-bottom: 0.2rem;
        background: linear-gradient(90deg, #ff8a3d, #ff5f6d);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .trendly-header p {
        color: #8b8fa3;
        font-size: 0.95rem;
        margin-top: 0;
    }
    [data-testid="stChatMessage"] {
        border-radius: 14px;
        padding: 0.4rem 0.2rem;
    }
    .sidebar-order-card {
        background: #1c1f2b;
        border: 1px solid #2a2d3a;
        border-radius: 10px;
        padding: 8px 12px;
        margin-bottom: 6px;
        font-size: 0.85rem;
    }
    .sidebar-order-id {
        color: #ff8a3d;
        font-weight: 700;
    }
    div[data-testid="stChatInput"] textarea {
        border-radius: 12px !important;
    }
</style>
""", unsafe_allow_html=True)

st.markdown(
    """
    <div class="trendly-header">
        <h1>🛍️ Trendly Support Assistant</h1>
        <p>Order status · Returns &amp; exchanges · Shipping &amp; refund policy</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ---------- Sidebar ----------
SAMPLE_ORDERS = [
    ("TR-4521", "In transit"),
    ("TR-4522", "Delivered — mixed cart (tee + socks)"),
    ("TR-4523", "Delivered 61 days ago — window expired"),
    ("TR-4524", "Partially shipped — item backordered"),
    ("TR-4525", "Delayed — qualifies for ₹250 store credit"),
    ("TR-4526", "Lost in transit — escalates to human"),
    ("TR-4527", "Jewellery — non-returnable category"),
    ("TR-4528", "Final sale — exchange only"),
    ("TR-4529", "Cancelled order"),
    ("TR-4530", "Clean happy-path return"),
]

with st.sidebar:
    st.markdown("### 🧾 Try these order IDs")
    for oid, desc in SAMPLE_ORDERS:
        st.markdown(
            f'<div class="sidebar-order-card"><span class="sidebar-order-id">{oid}</span><br>{desc}</div>',
            unsafe_allow_html=True,
        )
    st.markdown("---")
    if st.button("🔄 Reset conversation", use_container_width=True):
        st.session_state.messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        st.rerun()
    st.caption("Built for the Yellow.ai FDE screening assignment.")

# ---------- Chat state ----------
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "system", "content": SYSTEM_PROMPT}]

AVATARS = {"user": "🧑", "assistant": "🛍️"}

for m in st.session_state.messages:
    if m["role"] in ("user", "assistant") and m.get("content"):
        with st.chat_message(m["role"], avatar=AVATARS[m["role"]]):
            st.markdown(m["content"])

if prompt := st.chat_input("Ask about an order, a return, or our policies..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user", avatar=AVATARS["user"]):
        st.markdown(prompt)

    with st.chat_message("assistant", avatar=AVATARS["assistant"]):
        with st.spinner("Checking..."):
            updated, reply = run_agent_turn(st.session_state.messages)
        st.markdown(reply)
    st.session_state.messages = updated
