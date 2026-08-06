# Trendly Support Agent

An agentic support assistant for Trendly (D2C fashion retailer) that handles order status,
returns/exchange eligibility, and policy Q&A end-to-end, and escalates cleanly to a human
when it shouldn't handle something itself.

## Stack
- **Orchestration**: Groq's native function-calling (`llama-3.3-70b-versatile`, free tier) in a
  ReAct-style loop — the model decides which tool to call, reads the result, and either calls
  another tool or answers. No keyword matching.
- **Retrieval**: hand-rolled TF-IDF-style keyword scoring over policy markdown sections, pure
  Python (no scikit-learn/embedding API/compiled deps) — avoids build issues on newer Python
  versions and stays fully on the free tier.
- **UI**: Streamlit chat, session-scoped multi-turn state.
- **Deterministic logic**: order lookup, the 30-day return window, final-sale (exchange-only,
  not refund), non-returnable hygiene categories, footwear box deduction, business-day delay
  compensation, and lost-parcel/cancelled-order routing are all plain Python, not LLM judgment
  — see `SOLUTION.md` for why.

## Data
`data/trendly_policy.md` and `data/orders.json` are the real files from Trendly's assignment
Drive folder (10 fixed orders across 4 customers, with `_note_for_designers` fields marking the
intended edge case for each order — see the sidebar in the app for a quick reference). Loaded
as-is, unedited.

## Run locally
```bash
git clone <this-repo>
cd trendly-agent
pip install -r requirements.txt
export GROQ_API_KEY=your_free_groq_key   # from console.groq.com
streamlit run app.py
```
Opens at `http://localhost:8501`.

## Run tests
```bash
export GROQ_API_KEY=your_free_groq_key
pytest tests/test_scenarios.py -v -s
```
These are live scripted conversations (happy path, edge cases, safety/refusals, robustness) run
against the real model — they assert on which tools got called and on required/forbidden
keywords in the reply, not exact wording, since LLM phrasing isn't deterministic.

## Deploy (Hugging Face Spaces)
1. Create a new Space, SDK: Streamlit.
2. Push this repo to it (or connect the GitHub repo).
3. Add `GROQ_API_KEY` as a Space secret.
4. Space builds automatically from `requirements.txt` + `app.py`.

## Repo layout
```
app.py                 Streamlit UI, session state
agent.py                ReAct tool-calling loop + system prompt + tool schemas
tools/tools.py           Order lookup, eligibility/delay-compensation logic, escalation (deterministic)
tools/policy_store.py    TF-IDF policy retrieval
data/trendly_policy.md   Policy doc (PLACEHOLDER — replace, see above)
data/orders.json         Order data (PLACEHOLDER — replace, see above)
tests/test_scenarios.py  Scripted multi-turn test conversations
PROMPTS.md               Prompt iteration log
SOLUTION.md              Architecture, trade-offs, limitations, discovery questions
```

## AI usage note
Built with Claude (Anthropic) as a pair-programmer: I described the architecture and
guardrail requirements, Claude generated the initial scaffolding for `tools.py`,
`policy_store.py`, `agent.py`, and the test scenarios; I supplied the real policy doc and order
data, verified tool outputs against every order's intended edge case, wrote/edited the system
prompt iterations (see `PROMPTS.md`), picked the deterministic-vs-LLM split for eligibility
logic, and caught/fixed a live model deprecation on Groq's free tier before submitting.
