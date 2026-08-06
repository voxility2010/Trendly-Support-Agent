# Prompt engineering notes

## Note on data swap
The system prompt and tool descriptions below were first written against placeholder data I
invented (before I had access to the real Drive files), then revised once I had the real
`orders.json` and `trendly_policy.md`. The real policy turned out to have several rules a naive
prompt would get wrong by analogy to "typical" return policies, which drove another prompt/tool
iteration round (documented below): final-sale items are exchange-only rather than fully
blocked, lost-parcel orders are a distinct escalation path rather than a return case, and
delayed (not-yet-delivered) orders get compensation that delivered orders don't.

## System prompt — iteration log

**v1 (naive):** "You are a helpful Trendly support assistant. Use the tools when needed to help
customers with orders, returns, and policy questions."
- Problem: model answered simple policy questions ("do you ship on weekends?") from its own
  general retail knowledge instead of calling `search_policy`, and occasionally said
  approximate things like "returns are usually accepted within 2 weeks" (close to the real 15
  days, but not grounded — a hallucination that happened to be nearly right, which is worse
  because it's harder to catch).

**v2:** Added explicit "ALWAYS call search_policy before answering any policy question, never
answer from general knowledge" and "ALWAYS call check_return_eligibility before telling a
customer whether they can return something."
- Problem: fixed grounding for direct policy questions, but the model would sometimes decide
  eligibility itself when a customer asked something like "can I return my order, it's been like
  10 days" — it did the date math in its head instead of calling the tool, and got it right by
  luck once and wrong once (miscounted business vs calendar days).
- Fix: reframed eligibility as tool-only in both the system prompt and each tool's own
  `description` field ("do this deterministic thing, never eyeball dates yourself") — putting
  the instruction in two places (system prompt + tool description) was more reliable than either
  alone, since the model weighs tool descriptions heavily when deciding whether to call.

**v3:** Added the "WHAT YOU MUST NEVER DO" block (no invented discounts, no cross-customer data,
no fabricated tracking/refund numbers) after testing showed the model would apologize for an
inconvenience by offering "a 10% discount on your next order" unprompted — plausible-sounding
customer service behavior that isn't authorized here. Also added the PII-guardrail instruction
after a test where asking for another field on an order (email/phone) returned it without any
verification check.

**v4:** Added `verify_email` / `verify_phone` as optional tool parameters instead of a system
prompt instruction alone. Prompt instructions to "verify identity before sharing details" were
inconsistently followed; giving the tool itself a verification parameter that returns an error
if it doesn't match made the behavior structural rather than persuasive.

**v5 (escalation quality):** Early escalations produced generic summaries ("customer needs
help with an order"). Rewrote the `escalate_to_human` tool description to explicitly require
"2-4 sentences a human agent can act on immediately without re-reading the whole chat" and
added "what you already found/ruled out" to the system prompt's escalation guidance — this
measurably improved summary usefulness (concrete order IDs, item names, and what the agent
already checked started appearing in the `conversation_summary` argument).

**v6 (loop safety):** Added a hard `MAX_STEPS` cap in `agent.py` with a forced
`escalate_to_human` fallback if the model exceeds it, after a test conversation where a vague
multi-part question ("is my order fine and also what about the one before it and also can I get
a discount") caused the model to call tools repeatedly without ever producing a final answer.
This is orchestration-level recovery, not a prompt fix — some failure modes need code, not
better wording.

## Tool description iteration

Tool `description` fields went through the same iteration as the system prompt — in practice
they carry as much weight as the system prompt for *when* to call a tool, so ambiguous or
generic tool descriptions ("looks up an order") were replaced with descriptions that state the
trigger condition explicitly ("Call this whenever the customer mentions an order or asks
'where is my order'").

**v7 (real-data corrections):** After swapping in the real policy doc, three test conversations
failed against rules I hadn't modeled:
- Asking about a final-sale item ("can I return my final-sale shirt") got a flat "no, it's
  final sale" — technically true-sounding but wrong, since policy 2.4 makes final-sale items
  exchange-eligible. Fixed by changing `check_return_eligibility`'s return shape from a boolean
  to a `mode` field, and adding an explicit "don't just say 'can't be returned' — final sale
  means exchange for size" line to the system prompt.
- A "my order never arrived, tracking says lost" message caused the model to run
  `check_return_eligibility` on a `lost_in_transit` order instead of escalating — the model
  pattern-matched "customer wants their money back" to "return flow." Fixed by making
  `check_return_eligibility` itself refuse lost-parcel and cancelled orders with an explicit
  reason (so even if the model calls the wrong tool first, the tool result steers it back), plus
  adding "lost_in_transit is NOT a return, always escalate" as its own bullet in the system
  prompt rather than folding it into the general escalation paragraph where it got missed.
- A delayed-order question didn't surface the ₹250 store credit until I added
  `check_delay_compensation` as its own named tool with its own trigger condition in the
  description — when delay compensation was just a note inside `get_order_status`'s output, the
  model read the status but didn't reliably act on the compensation eligibility buried in the
  JSON. Splitting it into a dedicated tool call made the behavior show up consistently.

**v8 (model deprecation — caught before submission, not after):** Groq deprecated
`llama-3.3-70b-versatile` (announced June 17, 2026) in favor of `openai/gpt-oss-120b` /
`openai/gpt-oss-20b`. This is a real risk for any free-tier-model project with a multi-week
grading window: a model name that works today can 404 by the time an evaluator runs it. Fixed
by making `agent.py` try a small ordered list of model candidates and cache whichever one
responds successfully, instead of hardcoding one model name and hoping it's still live.

## Things that didn't need iteration

- Temperature: kept at 0.2 throughout — didn't experiment much beyond noting that higher values
  produced more inconsistent tool-call decisions in repeated runs of the same test prompt.
- Didn't need a separate "planner" prompt — a single ReAct loop with well-scoped tool
  descriptions was enough for this tool count (5 tools); would reconsider for a much larger
  toolset.
