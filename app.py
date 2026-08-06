import streamlit as st
from agent import run_agent_turn, SYSTEM_PROMPT

st.set_page_config(page_title="Trendly Support", page_icon="🛍️", layout="centered")
st.title("🛍️ Trendly Support Assistant")
st.caption("Order status · Returns & exchanges · Shipping & refund policy")

with st.sidebar:
    st.markdown("### Try these order IDs")
    st.markdown(
        "- **TR-4521** — in transit\n"
        "- **TR-4522** — delivered, mixed cart (tee + socks)\n"
        "- **TR-4523** — delivered 61 days ago, window expired\n"
        "- **TR-4524** — partially shipped (item backordered)\n"
        "- **TR-4525** — delayed, qualifies for ₹250 store credit\n"
        "- **TR-4526** — lost in transit, escalates to human\n"
        "- **TR-4527** — jewellery, non-returnable category\n"
        "- **TR-4528** — final sale, exchange only\n"
        "- **TR-4529** — cancelled order\n"
        "- **TR-4530** — clean happy-path return\n"
    )
    if st.button("Reset conversation"):
        st.session_state.messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        st.rerun()

if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "system", "content": SYSTEM_PROMPT}]

for m in st.session_state.messages:
    if m["role"] in ("user", "assistant") and m.get("content"):
        with st.chat_message(m["role"]):
            st.markdown(m["content"])

if prompt := st.chat_input("Ask about an order, a return, or our policies..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Checking..."):
            updated, reply = run_agent_turn(st.session_state.messages)
        st.markdown(reply)
    st.session_state.messages = updated
