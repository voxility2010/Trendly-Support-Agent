"""
Trendly Support Agent -- orchestration core.

Uses Groq's native function-calling (OpenAI-compatible tool_calls) to run
a ReAct-style loop: the model reads the conversation + tool results,
decides whether to call another tool or respond, and we keep looping
until it produces a final text answer or we hit MAX_STEPS (failure
recovery: if the model gets stuck calling tools, we force an escalation
instead of looping forever or hallucinating).

State: the caller (app.py) owns the message list per session and passes
it in/out, so this module is stateless and easy to test.
"""
import os
import json
import groq
from tools.tools import get_order_status, check_return_eligibility, check_delay_compensation, search_policy, escalate_to_human

MODEL_CANDIDATES = [
    "openai/gpt-oss-120b",   # Groq's current recommended general-purpose model (free tier)
    "openai/gpt-oss-20b",    # smaller/faster fallback, same family
    "llama-3.3-70b-versatile",  # legacy fallback in case org still has access
]
MAX_STEPS = 6

client = groq.Groq(api_key=os.environ.get("GROQ_API_KEY"))
_working_model = {"name": None}  # resolved once, cached for the process lifetime

TOOL_IMPL = {
    "get_order_status": get_order_status,
    "check_return_eligibility": check_return_eligibility,
    "check_delay_compensation": check_delay_compensation,
    "search_policy": search_policy,
    "escalate_to_human": escalate_to_human,
}

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "get_order_status",
            "description": "Look up a Trendly order by its order ID and return its live status, items, dates, tracking, shipping/payment method, and whether it's past the delay grace period or is a lost-parcel claim. Call this whenever the customer mentions an order or asks 'where is my order'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {"type": "string", "description": "The order ID, e.g. TR-4521"},
                    "verify_email": {"type": "string", "description": "Customer's email, if they provided one, used to verify order ownership"},
                    "verify_phone": {"type": "string", "description": "Customer's phone, if they provided one, used to verify order ownership"},
                },
                "required": ["order_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_return_eligibility",
            "description": "Deterministically check whether an order (or a specific item on it) is eligible for return/exchange right now, based on delivery date, the 30-day window, non-returnable categories (innerwear, jewellery, beauty/fragrance, face masks, gift cards), and final-sale status (exchange-only, not refund). Also flags footwear box requirements, and correctly refuses cancelled or lost-parcel orders. ALWAYS call this before telling a customer whether they can return or exchange something -- never decide eligibility yourself.",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {"type": "string"},
                    "sku": {"type": "string", "description": "Optional: specific item SKU or name to check, if the order has multiple items"},
                },
                "required": ["order_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_delay_compensation",
            "description": "Deterministically check whether an in-transit/partially-shipped/delayed order qualifies for the ₹250 delayed-order store credit (more than 3 business days past its expected delivery date). ALWAYS call this before offering or denying delay compensation -- never estimate business days yourself, and never offer this for a delivered order or a lost-parcel claim.",
            "parameters": {
                "type": "object",
                "properties": {"order_id": {"type": "string"}},
                "required": ["order_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_policy",
            "description": "Search Trendly's official shipping & returns policy document for the section relevant to a question (shipping times, return window, refund timing, cancellations, damaged items, discounts, etc). ALWAYS call this before answering any policy question -- never answer policy questions from general knowledge.",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string", "description": "The policy topic or the customer's question, in a few keywords"}},
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "escalate_to_human",
            "description": "Hand the conversation off to a human support agent. Use for: fraud/payment disputes, abusive/legal-threat language, anything not covered by policy, a customer explicitly asking for a human, requests for discounts/compensation outside policy, or when you are not confident enough to resolve it yourself after trying the other tools.",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {"type": "string", "description": "The order ID if one was discussed, otherwise omit this field"},
                    "reason": {"type": "string", "description": "Short internal reason category, e.g. 'damaged item beyond policy scope'"},
                    "conversation_summary": {"type": "string", "description": "2-4 sentence summary a human agent can act on immediately without re-reading the whole chat"},
                    "urgency": {"type": "string", "enum": ["low", "normal", "high"]},
                },
                "required": ["reason", "conversation_summary"],
            },
        },
    },
]

SYSTEM_PROMPT = """You are Trendly's customer support assistant. Trendly is a D2C fashion retailer.

HOW YOU WORK
- You have five tools: get_order_status, check_return_eligibility, check_delay_compensation, search_policy, escalate_to_human.
- Ground every policy claim ONLY in what search_policy returns. If it returns found=false or nothing relevant, say you don't have that information and offer to escalate -- never invent a policy.
- Whenever a customer asks to return or exchange an item, or asks whether they CAN return/exchange an item, you MUST call check_return_eligibility -- every time, even if you already called search_policy and think you know the category rule (jewellery, final sale, etc). search_policy tells you what the rule IS; check_return_eligibility tells you whether THIS item on THIS order, right now, qualifies. Never answer an eligibility question from search_policy text alone.
- Ground every delay-compensation claim ONLY in what check_delay_compensation returns. Never eyeball dates yourself or guess whether something is "probably fine" or "probably late enough."
- Never state an order's status, items, or dates without having called get_order_status first in this conversation (or reusing a result already in this conversation).
- If the customer gives an order ID that doesn't match records, or an order ID plus email/phone that don't match, say so plainly and do not reveal any order details.

KEY POLICY RULES TO REMEMBER WHEN ROUTING (still verify specifics via tools/search_policy, don't quote numbers from here)
- Return window is 30 calendar days from delivery, not order date.
- Final-sale items get a size EXCHANGE only, never a refund -- don't tell a customer a final-sale item simply "can't be returned," it CAN be exchanged for size.
- Innerwear/socks, jewellery, beauty/fragrance, face masks, and gift cards can never be returned or exchanged, regardless of the 30-day window.
- A "lost_in_transit" order is a lost-parcel claim, NOT a return -- always escalate it to a human, never run return eligibility on it or try to resolve it yourself.
- A cancelled order cannot have a return raised against it.
- Delayed orders (more than 3 business days past expected delivery, and not yet delivered) can get a ₹250 store credit on request -- check via check_delay_compensation, don't offer it for delivered orders or lost parcels.
- Never collect bank account numbers, card numbers, or CVV in chat, even for a COD refund -- that's handled by a human agent over a secure link. If a customer offers this info, tell them not to share it here and escalate instead.

WHAT YOU MUST NEVER DO
- Never invent, extend, or guess at policy terms not present in search_policy results.
- Never offer, promise, or apply a discount, refund amount, or compensation beyond what policy explicitly allows (delay store credit and damaged-item resolutions are the only compensations defined -- both are tool-verified, not discretionary).
- Never reveal one customer's order details in response to another customer's session, and never guess an order ID.
- Never fabricate an order, tracking number, or refund timeline.
- Never collect or ask for bank/card details in chat.

WHEN TO ESCALATE
Escalate when: the order is a lost-parcel claim (status lost_in_transit), the customer reports an item arrived damaged/defective/or wrong (do NOT run check_return_eligibility for these -- a damaged/wrong item is not a standard return regardless of category or window, it needs a human to review photos per policy), the situation involves fraud/payment disputes, abuse/legal threats, a COD refund that needs bank details, a request outside what policy covers, the customer explicitly asks for a human, or you've tried the relevant tools and still can't resolve it confidently. When you escalate, write a summary a human can act on immediately (order id, what the customer wants, what you already found/ruled out) -- don't just say "customer needs help."

STYLE
- Plain, warm, concise language. No corporate fluff. Explain status/eligibility in terms a non-technical customer understands.
- If information is genuinely missing (order not found, policy not found), say so directly instead of hedging vaguely.
- Ask for an order ID if the customer references "my order" without giving one.
"""


def _chat_completion(**kwargs):
    """Calls Groq with automatic model fallback. Groq's free-tier model
    lineup changes/deprecates faster than this code does -- if the
    primary model 404s or is decommissioned, we transparently retry with
    the next candidate rather than failing the whole conversation. Once
    a model is confirmed working, it's cached for the rest of the process."""
    candidates = [_working_model["name"]] if _working_model["name"] else MODEL_CANDIDATES
    last_err = None
    for model_name in candidates:
        try:
            resp = client.chat.completions.create(model=model_name, **kwargs)
            _working_model["name"] = model_name
            return resp
        except Exception as e:  # groq raises various APIStatusError subclasses
            last_err = e
            continue
    raise RuntimeError(
        f"All Groq model candidates failed ({MODEL_CANDIDATES}). "
        f"Check console.groq.com/docs/models for current free-tier model names "
        f"and update MODEL_CANDIDATES in agent.py. Last error: {last_err}"
    )


def run_agent_turn(messages: list[dict]) -> tuple[list[dict], str]:
    """Runs the ReAct loop for one user turn. `messages` is the full
    conversation so far (system + history + new user message, OpenAI
    format). Returns (updated_messages, final_assistant_text)."""
    working = list(messages)

    for step in range(MAX_STEPS):
        resp = _chat_completion(
            messages=working,
            tools=TOOL_SCHEMAS,
            tool_choice="auto",
            temperature=0.2,
        )
        msg = resp.choices[0].message
        assistant_msg = {"role": "assistant", "content": msg.content}
        if msg.tool_calls:
            assistant_msg["tool_calls"] = [tc.model_dump() for tc in msg.tool_calls]
        working.append(assistant_msg)

        if not msg.tool_calls:
            return working, msg.content or ""

        for tc in msg.tool_calls:
            name = tc.function.name
            try:
                args = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}
            impl = TOOL_IMPL.get(name)
            if impl is None:
                result = {"error": f"Unknown tool {name}"}
            else:
                try:
                    result = impl(**args)
                except TypeError as e:
                    result = {"error": f"Bad arguments for {name}: {e}"}
            working.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "name": name,
                "content": json.dumps(result, default=str),
            })

    # Failure recovery: model looped past MAX_STEPS without a final
    # answer -- don't hallucinate, force a human handoff instead.
    fallback = escalate_to_human(
        order_id=None,
        reason="agent_loop_limit",
        conversation_summary="Agent could not resolve this within its tool-call budget. Needs manual review of the conversation.",
        urgency="normal",
    )
    text = "I'm having trouble fully resolving this one myself, so I've flagged it for a human agent to take over -- they'll have the context from our chat."
    working.append({"role": "assistant", "content": text})
    return working, text
