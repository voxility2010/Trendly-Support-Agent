# Solution Note

## Architecture
A single ReAct-style tool-calling loop (Groq `llama-3.3-70b-versatile`, free tier) sits between
the customer and four tools:

- **`get_order_status`** — lookup on `orders.json` (order joined to its customer record), keyed
  by order ID, with optional email/phone verification to prevent cross-customer data leakage.
  Also flags lost-parcel claims and computes business-days-past-expected for delay handling.
- **`check_return_eligibility`** — deterministic Python: delivery-date + 30-day window math,
  final-sale (routes to exchange-only, not a flat refusal), non-returnable category check
  (innerwear/socks, jewellery, beauty/fragrance, face masks, gift cards), footwear box-deduction
  note, and correct refusal for cancelled or lost-parcel orders before even checking dates.
  Returns facts, not a yes/no from the model.
- **`check_delay_compensation`** — deterministic business-day counting against the 3-day grace
  period for the ₹250 delayed-order store credit; explicitly refuses to apply to delivered
  orders or lost-parcel claims (those aren't "delays," they're different problems).
- **`search_policy`** — TF-IDF retrieval over the policy markdown, chunked by `##`/`###` section.
  Only source of policy text the model is allowed to use.
- **`escalate_to_human`** — logs a structured ticket (order ID, reason, human-actionable summary,
  urgency) to a JSONL file, standing in for a real helpdesk API call.

The orchestration loop (`agent.py`) is stateless per call — the caller passes the full message
history in, gets it back updated, and owns persistence. This made it trivial to write scripted
multi-turn tests that just append to a list, and would make swapping Streamlit for a FastAPI
backend + any frontend a non-issue later.

## Key trade-offs
1. **Deterministic logic outside the LLM wherever possible.** Return eligibility, the 30-day
   window, business-day delay counting, and category rules are all arithmetic and flag-checking
   — I don't want the model "deciding" whether 3499 - 2799 crosses a threshold, or eyeballing
   business days, from memory. Same principle I use building Suproc's agents: LLM calls are for
   judgment (how to explain something, what to search for, when to escalate), not for math or
   lookups the code can just do correctly every time. This also caught a genuine subtlety in
   the policy: final-sale items are *exchange-eligible, refund-ineligible* — a model reasoning
   about "return eligibility" in one boolean would naturally collapse that distinction, so the
   tool returns a `mode` field (`refund_or_exchange` / `exchange_only_final_sale` /
   `non_returnable_category` / `expired`) instead of a flat true/false.
2. **Hand-rolled TF-IDF over embeddings (or even scikit-learn) for policy retrieval.** A ~1-page
   policy doc with a handful of sections doesn't need a vector DB, an embedding API call, or a
   compiled ML library — a ~60-line pure-Python TF-IDF scorer is free, deterministic, has zero
   install friction (this also sidesteps scikit-learn's lack of a prebuilt wheel on newer Python
   versions), and is good enough at this scale. Trade-off: it would degrade on a much longer or
   more ambiguously-worded policy doc, where semantic embeddings would do better.
3. **Hard step cap + forced escalation over open-ended looping.** Rather than trusting the model
   to always terminate cleanly, `MAX_STEPS` forces a human handoff if the loop doesn't converge.
   This trades a small chance of cutting off a resolvable-but-slow conversation for a guarantee
   against infinite tool-calling or a stalled response.
4. **Identity verification is opt-in per message, not session-locked.** `verify_email`/
   `verify_phone` are tool parameters the model passes when the customer has volunteered them,
   not a mandatory login step — reasonable for a support-chat context, but not a real auth
   system. A production version would sit behind Trendly's actual customer auth.

## Known limitations
- No persistent session storage across app restarts — Streamlit session state only.
- The 3-business-day delay grace period doesn't account for public holidays (only counts
  Mon–Fri) — the policy doc doesn't specify a holiday calendar, so this is a reasonable but
  unverified assumption I'd confirm with ops.
- Footwear box deduction (₹300) is surfaced as a note in `check_return_eligibility`'s output but
  there's no mechanism to actually confirm at pickup time whether the box was included — that's
  inherently a physical-world fact this system can't observe.
- Escalation is a local log file, not a real ticketing system integration.
- Single-language (English) — no handling for Hindi/Hinglish input, which Trendly's actual
  customer base likely uses.
- No rate limiting / abuse handling on the free Groq tier — a real deployment needs to guard
  against being hammered.
- Identity verification is easily bypassed by a customer just not providing email/phone (the
  model will ask, but nothing stops a customer from providing a made-up one that happens to not
  match — the tool will correctly refuse, but there's no lockout after repeated failed attempts).

## Five discovery questions for Trendly's ops team
1. What does the current human escalation path actually look like — which helpdesk system, and
   what fields does a human agent need pre-filled to act without re-reading the chat?
2. Of the 30% of chats that aren't order/returns/policy, what's the actual next-biggest category
   — is it worth building a second agent skill for it, or is it genuinely long-tail?
3. How is customer identity currently verified in human-agent chats (order ID alone? email
   match? OTP?) — I made an assumption here that should match existing practice, not invent a
   new one.
4. Are there order states or edge cases not represented in these 10 sample orders (partial
   shipments, multi-item orders with mixed eligibility, address changes mid-transit) that show
   up often enough in the real 2,000/day volume to matter for v1?
5. What's the actual cost/tolerance for a wrong answer vs. an unnecessary escalation — i.e.
   should the agent be tuned to escalate more aggressively (safer, more human load) or resolve
   more aggressively (cheaper, more risk) for this account specifically?
