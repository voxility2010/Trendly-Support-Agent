"""
Tool implementations the agent can call.

Design principle: anything deterministic (date math, category checks,
business-day counting) is plain Python, not an LLM judgment call. The
LLM decides WHEN to call a tool and how to phrase results -- it never
invents order data, eligibility outcomes, or compensation amounts.
"""
import json
from datetime import datetime, date, timedelta
from pathlib import Path
from .policy_store import get_store

DATA_PATH = Path(__file__).parent.parent / "data" / "orders.json"

RETURN_WINDOW_DAYS = 30
DELAY_GRACE_BUSINESS_DAYS = 3
DELAY_STORE_CREDIT = 250
FOOTWEAR_NO_BOX_DEDUCTION = 300
NON_RETURNABLE_CATEGORIES = {"innerwear", "jewellery", "beauty", "fragrance", "gift_card"}

with open(DATA_PATH, encoding="utf-8") as f:
    _RAW = json.load(f)
_CUSTOMERS = {c["customer_id"]: c for c in _RAW["customers"]}
_ORDERS = {o["order_id"].upper(): o for o in _RAW["orders"]}


def _today() -> date:
    return date(2026, 8, 5)  # fixed "current date" for deterministic testing


def _parse(dt_str: str) -> date:
    return datetime.fromisoformat(dt_str.replace("Z", "+00:00")).date()


def _business_days_between(d1: date, d2: date) -> int:
    """Count business days (Mon-Fri) strictly between d1 and d2, d2 > d1."""
    if d2 <= d1:
        return 0
    days = 0
    cur = d1 + timedelta(days=1)
    while cur <= d2:
        if cur.weekday() < 5:
            days += 1
        cur += timedelta(days=1)
    return days


def _customer_for(order: dict) -> dict:
    return _CUSTOMERS.get(order["customer_id"], {})


def get_order_status(order_id: str, verify_email: str | None = None, verify_phone: str | None = None) -> dict:
    """Look up an order. If verify_email/verify_phone is supplied it must
    match the order's customer -- guardrail against pulling up another
    customer's order by guessing an ID."""
    order = _ORDERS.get(order_id.strip().upper())
    if not order:
        return {"found": False, "error": f"No order found with ID '{order_id}'."}

    customer = _customer_for(order)
    if verify_email and verify_email.strip().lower() != customer.get("email", "").lower():
        return {"found": False, "error": "Order ID does not match the provided email. Cannot share order details."}
    if verify_phone and verify_phone.strip() != customer.get("phone", ""):
        return {"found": False, "error": "Order ID does not match the provided phone number. Cannot share order details."}

    today = _today()
    is_delayed = False
    business_days_late = 0
    if order["status"] in ("in_transit", "partially_shipped", "delayed") and order.get("expected_delivery"):
        expected = _parse(order["expected_delivery"])
        business_days_late = _business_days_between(expected, today)
        is_delayed = business_days_late > DELAY_GRACE_BUSINESS_DAYS

    days_since_delivery = None
    if order.get("delivered_at"):
        days_since_delivery = (today - _parse(order["delivered_at"])).days

    return {
        "found": True,
        "order_id": order["order_id"],
        "status": order["status"],
        "placed_at": order["placed_at"],
        "delivered_at": order.get("delivered_at"),
        "expected_delivery": order.get("expected_delivery"),
        "days_since_delivery": days_since_delivery,
        "is_delayed_past_grace_period": is_delayed,
        "business_days_past_expected": business_days_late,
        "carrier": order.get("carrier"),
        "tracking_number": order.get("tracking_number"),
        "payment_method": order["payment_method"],
        "shipping_city": order.get("shipping_city"),
        "items": order["items"],
        "total": order["total"],
        "cancelled_at": order.get("cancelled_at"),
        "refund_status": order.get("refund_status"),
        "note_is_lost_parcel_claim": order["status"] == "lost_in_transit",
    }


def check_delay_compensation(order_id: str) -> dict:
    """Deterministically check whether an order qualifies for the ₹250
    delayed-order store credit (policy 1.5: >3 business days past
    expected delivery). Never estimate this from memory -- always call."""
    order = _ORDERS.get(order_id.strip().upper())
    if not order:
        return {"eligible": None, "error": f"No order found with ID '{order_id}'."}
    if order["status"] == "delivered":
        return {"eligible": False, "reason": "Order has already been delivered; delay compensation does not apply."}
    if order["status"] == "lost_in_transit":
        return {"eligible": False, "reason": "This is a lost-parcel claim, not a delay -- escalate to a human instead of offering store credit."}
    if not order.get("expected_delivery"):
        return {"eligible": False, "reason": "Order has no expected delivery date on file."}

    expected = _parse(order["expected_delivery"])
    business_days_late = _business_days_between(expected, _today())
    eligible = business_days_late > DELAY_GRACE_BUSINESS_DAYS
    return {
        "eligible": eligible,
        "business_days_past_expected": business_days_late,
        "store_credit_amount": DELAY_STORE_CREDIT if eligible else 0,
    }


def check_return_eligibility(order_id: str, sku: str | None = None) -> dict:
    """Deterministic eligibility per policy: 30-day window from delivery,
    non-returnable categories, final-sale (exchange-only, not refund),
    footwear box requirement, cancelled/undelivered/lost orders blocked.
    Returns facts per item; the LLM must not decide this itself."""
    order = _ORDERS.get(order_id.strip().upper())
    if not order:
        return {"eligible": None, "error": f"No order found with ID '{order_id}'."}

    if order["status"] == "cancelled":
        return {"eligible": False, "reason": "Order is already cancelled and refunded; a return cannot be raised against it.", "order_status": "cancelled"}
    if order["status"] == "lost_in_transit":
        return {"eligible": False, "reason": "This order is a lost-parcel claim, not a return -- must be escalated to a human agent.", "order_status": "lost_in_transit"}
    if order["status"] != "delivered":
        return {"eligible": False, "reason": f"Order status is '{order['status']}', not 'delivered'. Returns can only be raised after delivery.", "order_status": order["status"]}

    delivered = _parse(order["delivered_at"])
    days_since = (_today() - delivered).days
    within_window = days_since <= RETURN_WINDOW_DAYS

    items = order["items"]
    if sku:
        items = [i for i in items if i["sku"].upper() == sku.upper() or i["name"].lower() == sku.lower()]
        if not items:
            return {"eligible": None, "error": f"No item matching '{sku}' found on order {order_id}."}

    item_flags = []
    for item in items:
        category = item.get("category", "").lower()
        is_non_returnable = category in NON_RETURNABLE_CATEGORIES
        is_final_sale = item.get("final_sale", False)
        is_footwear = category == "footwear"

        if not within_window:
            outcome, mode = False, "expired"
        elif is_non_returnable:
            outcome, mode = False, "non_returnable_category"
        elif is_final_sale:
            outcome, mode = True, "exchange_only_final_sale"
        else:
            outcome, mode = True, "refund_or_exchange"

        item_flags.append({
            "sku": item["sku"], "name": item["name"], "category": category,
            "eligible": outcome, "mode": mode,
            "final_sale": is_final_sale,
            "non_returnable_category": is_non_returnable,
            "footwear_box_note": "Original shoe box required, ₹300 deduction if missing" if (is_footwear and outcome) else None,
        })

    return {
        "eligible": any(f["eligible"] for f in item_flags),
        "days_since_delivery": days_since,
        "within_30_day_window": within_window,
        "items": item_flags,
        "order_status": order["status"],
        "payment_method": order["payment_method"],
    }


def search_policy(query: str) -> dict:
    """Retrieve the most relevant policy section(s) for a query. The ONLY
    source of policy text the agent may use -- if empty, say so, don't guess."""
    results = get_store().search(query)
    if not results:
        return {"found": False, "sections": []}
    return {"found": True, "sections": [{"heading": r["heading"], "text": r["text"]} for r in results]}


def escalate_to_human(reason: str, conversation_summary: str, order_id: str | None = None, urgency: str = "normal") -> dict:
    """Hand off to a human agent with a usable summary. Logs a structured
    ticket; in production this would hit a real helpdesk API."""
    ticket = {
        "ticket_created": True, "order_id": order_id, "reason": reason,
        "summary": conversation_summary, "urgency": urgency, "created_at": _today().isoformat(),
    }
    log_path = Path(__file__).parent.parent / "data" / "escalations.log.jsonl"
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(ticket) + "\n")
    return ticket
