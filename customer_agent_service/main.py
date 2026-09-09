
# ==== Imports ====
from __future__ import annotations
import json
from dotenv import load_dotenv
from openai import OpenAI
import re, io, sys, traceback, json
from typing import Any, Dict, Optional
from tinydb import Query, where

# Utility modules
import utils      # helper functions for prompting/printing
import inv_utils  # functions for inventory, transactions, schema building, and TinyDB seeding

load_dotenv()
client = OpenAI()

# * Planning with code execution means letting the LLM write code that becomes the plan itself.

db, inventory_tbl, transactions_tbl = inv_utils.seed_db()
# Inspect Record
utils.print_html(json.dumps(inventory_tbl.all(), indent=2), title="Inventory Table")
utils.print_html(json.dumps(transactions_tbl.all(), indent=2), title="Transactions Table")
{
# Inventory Table
# [
#   {
#     "item_id": "SG001",
#     "name": "Aviator",
#     "description": "Originally designed for pilots, these teardrop-shaped lenses with thin metal frames offer timeless appeal. The large lenses provide excellent coverage while the lightweight construction ensures comfort during long wear.",
#     "quantity_in_stock": 23,
#     "price": 80
#   },
#   {
#     "item_id": "SG002",
#     "name": "Wayfarer",
#     "description": "Featuring thick, angular frames that make a statement, these sunglasses combine retro charm with modern edge. The rectangular lenses and sturdy acetate construction create a confident look.",
#     "quantity_in_stock": 6,
#     "price": 95
#   },
#   {
#     "item_id": "SG003",
#     "name": "Mystique",
#     "description": "Inspired by 1950s glamour, these frames sweep upward at the outer corners to create an elegant, feminine silhouette. The subtle curves and often embellished temples add sophistication to any outfit.",
#     "quantity_in_stock": 3,
#     "price": 70
#   },
#   {
#     "item_id": "SG004",
#     "name": "Sport",
#     "description": "Designed for active lifestyles, these wraparound sunglasses feature a single curved lens that provides maximum coverage and wind protection. The lightweight, flexible frames include rubber grips.",
#     "quantity_in_stock": 11,
#     "price": 110
#   },
#   {
#     "item_id": "SG005",
#     "name": "Classic",
#     "description": "Classic round profile with minimalist metal frames, offering a timeless and versatile style that fits both casual and formal wear.",
#     "quantity_in_stock": 10,
#     "price": 60
#   },
#   {
#     "item_id": "SG006",
#     "name": "Moon",
#     "description": "Oversized round style with bold plastic frames, evoking retro aesthetics with a modern twist.",
#     "quantity_in_stock": 10,
#     "price": 120
#   }
# ]

# Transactions Table
# [
#   {
#     "transaction_id": "TXN001",
#     "customer_name": "OPENING_BALANCE",
#     "transaction_summary": "Daily opening register balance",
#     "transaction_amount": 500.0,
#     "balance_after_transaction": 500.0,
#     "timestamp": "2026-09-09T09:11:25.204434"
#   }
# ]
}

# NOTE
{
# Inventory Table (inventory_tbl)
# item_id (string): Unique product identifier (e.g., SG001).
# name (string): Style of sunglasses (e.g., Aviator, Round).
# description (string): Text description of the product.
# quantity_in_stock (int): Current stock available.
# price (float): Price in USD.

# Transactions Table (transactions_tbl)
# transaction_id (string): Unique identifier (e.g., TXN001).
# customer_name (string): Name of the customer, or OPENING_BALANCE for initial entry.
# transaction_summary (string): Short description of the transaction.
# transaction_amount (float): Amount of money for this transaction.
# balance_after_transaction (float): Running balance after applying the transaction.
# timestamp (string): ISO-8601 formatted date/time of the transaction.
}

# * Planning with Code Execution
# Build the prompt that instructs the model to plan by writing code and then execute that code
# The code is the plan: the model explains each step in comments, then carries it out.
PROMPT = """You are a senior data assistant. PLAN BY WRITING PYTHON CODE USING TINYDB.

Database Schema & Samples (read-only):
{schema_block}

Execution Environment (already imported/provided):
- Variables: db, inventory_tbl, transactions_tbl  # TinyDB Table objects
- Helpers: get_current_balance(tbl) -> float, next_transaction_id(tbl, prefix="TXN") -> str
- Natural language: user_request: str  # the original user message

PLANNING RULES (critical):
- Derive ALL filters/parameters from user_request (shape/keywords, price ranges "under/over/between", stock mentions,
  quantities, buy/return intent). Do NOT hard-code values.
- Build TinyDB queries dynamically with Query(). If a constraint isn't in user_request, don't apply it.
- Be conservative: if intent is ambiguous, do read-only (DRY RUN).

TRANSACTION POLICY (hard):
- Do NOT create aggregated multi-item transactions.
- If the request contains multiple items, create a separate transaction row PER ITEM.
- For each item:
  - compute its own line total (unit_price * qty),
  - insert ONE transaction with that amount,
  - update balance sequentially (balance += line_total),
  - update the item’s stock.
- If any requested item lacks sufficient stock, do NOT mutate anything; reply with STATUS="insufficient_stock".

HUMAN RESPONSE REQUIREMENT (hard):
- You MUST set a variable named `answer_text` (type str) with a short, customer-friendly sentence (1–2 lines).
- This sentence is the only user-facing message. No dataframes/JSON, no boilerplate disclaimers.
- If nothing matches, politely say so and offer a nearby alternative (closest style/price) or a next step.

ACTION POLICY:
- If the request clearly asks to change state (buy/purchase/return/restock/adjust):
    ACTION="mutate"; SHOULD_MUTATE=True; perform the change and write a matching transaction row.
  Otherwise:
    ACTION="read"; SHOULD_MUTATE=False; simulate and explain briefly as a dry run (in logs only).

FAILURE & EDGE-CASE HANDLING (must implement):
- Do not capture outer variables in Query.test. Pass them as explicit args.
- Always set a short `answer_text`. Also set a string `STATUS` to one of:
  "success", "no_match", "insufficient_stock", "invalid_request", "unsupported_intent".
- no_match: No items satisfy the filters → suggest the closest in style/price, or invite a different range.
- insufficient_stock: Item found but stock < requested qty → state available qty and offer the max you can fulfill.
- invalid_request: Unable to parse essential info (e.g., quantity for a purchase/return) → ask for the missing piece succinctly.
- unsupported_intent: The action is outside the store’s capabilities → provide the nearest supported alternative.
- In all cases, keep the tone helpful and concise (1–2 sentences). Put technical details (e.g., ACTION/DRY RUN) only in stdout logs.

OUTPUT CONTRACT:
- Return ONLY executable Python between these tags (no extra text):
  <execute_python>
  # your python
  </execute_python>

CODE CHECKLIST (follow in code):
1) Parse intent & constraints from user_request (regex ok).
2) Build TinyDB condition incrementally; query inventory_tbl.
3) If mutate: validate stock, update inventory, insert a transaction (new id, amount, balance, timestamp).
4) ALWAYS set:
   - `answer_text` (human sentence, required),
   - `STATUS` (see list above).
   Also print a brief log to stdout, e.g., "LOG: ACTION=read DRY_RUN=True STATUS=no_match".
5) Optional: set `answer_rows` or `answer_json` if useful, but `answer_text` is mandatory.

TONE EXAMPLES (for `answer_text`):
- success: "Yes, we have our Classic sunglasses, a round frame, for $60."
- no_match: "We don’t have round frames under $100 in stock right now, but our Moon round frame is available at $120."
- insufficient_stock: "We only have 1 pair of Classic left; I can reserve that for you."
- invalid_request: "I can help with that—how many pairs would you like to purchase?"
- unsupported_intent: "We can’t refurbish frames, but I can suggest similar new models."

Constraints:
- Use TinyDB Query for filtering. Standard library imports only if needed.
- Keep code clear and commented with numbered steps.

User request:
{question}
"""

# * FROM CODE TO PLANNING
# ---------- 1) Code generation ----------
def generate_llm_code(
    prompt: str,
    *,
    inventory_tbl,
    transactions_tbl,
    model: str = "gpt-4.1-mini",
    temperature: float = 0.2,
) -> str:
    """
    Ask the LLM to produce a plan-with-code response.
    Returns the FULL assistant content (including surrounding text and tags).
    The actual code extraction happens later in execute_generated_code.
    """
    schema_block = inv_utils.build_schema_block(inventory_tbl, transactions_tbl)
    prompt = PROMPT.format(schema_block=schema_block, question=prompt)

    resp = client.chat.completions.create(
        model=model,
        temperature=temperature,
        messages=[
            {
                "role": "system",
                "content": "You write safe, well-commented TinyDB code to handle data questions and updates."
            },
            {"role": "user", "content": prompt},
        ],
    )
    content = resp.choices[0].message.content or ""
    
    return content  


# Prompt: “Do you have any round sunglasses in stock that are under $100?”

# * MANUALLY
Item = Query()
# Create a Query object to reference fields (e.g., Item.name, Item.description)
# Search the inventory table for documents where either the description OR the name
# contains the word "round" (case-insensitive). The check is done inline:
# - (v or "") ensures we handle None by converting it to an empty string
# - .lower() normalizes case
# - " round " enforces a crude word boundary (won't match "wraparound")
round_sunglasses = inventory_tbl.search(
    (Item.description.test(lambda v: " round " in ((v or "").lower()))) |
    (Item.name.test(        lambda v: " round " in ((v or "").lower())))
)
# Render the results as formatted JSON in the notebook UI
utils.print_html(json.dumps(round_sunglasses, indent=2), title="Inventory Status: Round Sunglasses")
{
# Inventory Status: Round Sunglasses
# [
#   {
#     "item_id": "SG005",
#     "name": "Classic",
#     "description": "Classic round profile with minimalist metal frames, offering a timeless and versatile style that fits both casual and formal wear.",
#     "quantity_in_stock": 10,
#     "price": 60
#   },
#   {
#     "item_id": "SG006",
#     "name": "Moon",
#     "description": "Oversized round style with bold plastic frames, evoking retro aesthetics with a modern twist.",
#     "quantity_in_stock": 10,
#     "price": 120
#   }
# ]
}

# * GENERATE A PLAN IN CODE
prompt_round = "Do you have any round sunglasses in stock that are under $100?"

# Generate the plan-as-code (FULL content; may include <execute_python> tags)
full_content_round = generate_llm_code(
    prompt_round,
    inventory_tbl=inventory_tbl,
    transactions_tbl=transactions_tbl,
    model="o4-mini",
    temperature=1.0,
)

# Inspect the LLM’s plan + code (no execution here)
utils.print_html(full_content_round, title="Plan with Code (Full Response)")
{
# Plan with Code (Full Response)
# <execute_python>
# # 1) Setup and parse constraints
# from tinydb import Query
# import re

# # Intent determined as read-only query since user asks for stock info
# ACTION = "read"
# SHOULD_MUTATE = False  # dry run

# # Extract price constraint (e.g., "under $100", "over $50", "between $X and $Y")
# price_limit = None
# price_match = re.search(r'under\s*\$?(\d+)', user_request, re.IGNORECASE)
# if price_match:
#     price_limit = int(price_match.group(1))
#     price_op = 'lt'

# # Extract keyword for style (e.g., "round")
# keyword = None
# kw_match = re.search(r'\b(round)\b', user_request, re.IGNORECASE)
# if kw_match:
#     keyword = kw_match.group(1).lower()

# # 2) Build TinyDB query
# q = Query()
# cond = (q.quantity_in_stock > 0)
# if keyword:
#     # search keyword in name or description
#     cond = cond & (q.description.test(lambda d, kw=keyword: kw in d.lower()) |
#                    q.name.test(lambda n, kw=keyword: kw in n.lower()))
# if price_limit is not None and price_op == 'lt':
#     cond = cond & (q.price < price_limit)

# # 3) Query the inventory
# results = inventory_tbl.search(cond)

# # 4) Construct response
# if not results:
#     # no matching items: suggest nearest alternative
#     # find all round frames in stock (any price)
#     alt_cond = (q.quantity_in_stock > 0)
#     if keyword:
#         alt_cond = alt_cond & (q.description.test(lambda d, kw=keyword: kw in d.lower()) |
#                                q.name.test(lambda n, kw=keyword: kw in n.lower()))
#     alt_items = inventory_tbl.search(alt_cond)
#     if alt_items:
#         # pick the one with price closest above the limit, if limit exists; else lowest price
#         if price_limit is not None:
#             # filter above limit
#             above = [item for item in alt_items if item['price'] >= price_limit]
#             candidates = above or alt_items
#         else:
#             candidates = alt_items
#         # choose by minimum price difference or min price
#         def price_diff(item):
#             return abs(item['price'] - (price_limit or item['price']))
#         suggestion = min(candidates, key=price_diff)
#         answer_text = (f"We don’t have round frames under ${price_limit}, "
#                        f"but our {suggestion['name']} round frame is available at ${suggestion['price']}.")
#         STATUS = "no_match"
#     else:
#         # no round frames at all
#         answer_text = "We don’t have any round sunglasses in stock right now. Can I help you find another style?"
#         STATUS = "no_match"
# else:
#     # matches found
#     names = [item['name'] for item in results]
#     # build a simple listing
#     if len(names) == 1:
#         item = results[0]
#         answer_text = f"Yes, we have our {item['name']} round sunglasses for ${item['price']}."
#     else:
#         listing = ", ".join(f"{item} (${next(i for i in results if i['name']==item)['price']})" 
#                             for item in names)
#         answer_text = f"Yes, we have: {listing}."
#     STATUS = "success"

# # 5) Log and finish
# print(f"LOG: ACTION={ACTION} DRY_RUN={not SHOULD_MUTATE} STATUS={STATUS}")
# </execute_python>
}

# --- Helper: extract code between <execute_python>...</execute_python> ---
def _extract_execute_block(text: str) -> str:
    """
    Returns the Python code inside <execute_python>...</execute_python>.
    If no tags are found, assumes 'text' is already raw Python code.
    """
    if not text:
        raise RuntimeError("Empty content passed to code executor.")
    m = re.search(r"<execute_python>(.*?)</execute_python>", text, re.DOTALL | re.IGNORECASE)
    return m.group(1).strip() if m else text.strip()


# ---------- 2) Code execution ----------
def execute_generated_code(
    code_or_content: str,
    *,
    db,
    inventory_tbl,
    transactions_tbl,
    user_request: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Execute code in a controlled namespace.
    Accepts either raw Python code OR full content with <execute_python> tags.
    Returns minimal artifacts: stdout, error, and extracted answer.
    """
    # Extract code here (now centralized)
    code = _extract_execute_block(code_or_content)

    SAFE_GLOBALS = {
        "Query": Query,
        "get_current_balance": inv_utils.get_current_balance,
        "next_transaction_id": inv_utils.next_transaction_id,
        "user_request": user_request or "",
    }
    SAFE_LOCALS = {
        "db": db,
        "inventory_tbl": inventory_tbl,
        "transactions_tbl": transactions_tbl,
    }

    # Capture stdout from the executed code
    _stdout_buf, _old_stdout = io.StringIO(), sys.stdout
    sys.stdout = _stdout_buf
    err_text = None
    try:
        exec(code, SAFE_GLOBALS, SAFE_LOCALS)
    except Exception:
        err_text = traceback.format_exc()
    finally:
        sys.stdout = _old_stdout
    printed = _stdout_buf.getvalue().strip()

    # Extract possible answers set by the generated code
    answer = (
        SAFE_LOCALS.get("answer_text")
        or SAFE_LOCALS.get("answer_rows")
        or SAFE_LOCALS.get("answer_json")
    )


    return {
        "code": code,            # <- ya sin etiquetas
        "stdout": printed,
        "error": err_text,
        "answer": answer,
        "transactions_tbl": transactions_tbl.all(),  # For inspection
        "inventory_tbl": inventory_tbl.all(),  # For inspection
    }

# Execute the generated plan for the round-sunglasses question
result = execute_generated_code(
    full_content_round,          # the full LLM response you generated earlier
    db=db,
    inventory_tbl=inventory_tbl,
    transactions_tbl=transactions_tbl,
    user_request=prompt_round, # e.g., "Do you have any round sunglasses in stock that are under $100?"
)

# Peek at exactly what Python the plan executed
utils.print_html(result["answer"], title="Plan Execution · Extracted Answer")
# Plan Execution · Extracted Answer
# Yes, we have our Classic round sunglasses for $60.

# * Return Two Aviator Sunglasses
prompt_aviator = "Return 2 Aviator sunglasses I bought last week."

# Generate the plan-as-code (FULL content; may include <execute_python> tags)
full_content_aviator = generate_llm_code(
    prompt_aviator,
    inventory_tbl=inventory_tbl,
    transactions_tbl=transactions_tbl,
    model="o4-mini",
    temperature=1,
)

# Inspect the LLM’s plan + code (no execution here)
utils.print_html(full_content_aviator, title="Plan with Code (Full Response)")
{
# Plan with Code (Full Response)
# <execute_python>
# # 1) Imports and setup
# import re
# from tinydb import Query
# from datetime import datetime

# # Ensure helpers and tables are available: db, inventory_tbl, transactions_tbl, get_current_balance, next_transaction_id

# # 2) Initialize default variables
# STATUS = None
# answer_text = ""
# ACTION = None
# SHOULD_MUTATE = False

# # 3) Parse user_request for return intent, quantity, and item style
# #    Example: "Return 2 Aviator sunglasses I bought last week."
# user_text = user_request.strip()
# match = re.search(r"\breturn\s+(\d+)\s+([A-Za-z]+)\s+sunglasses", user_text, re.IGNORECASE)

# if not match:
#     # Missing quantity or item style
#     STATUS = "invalid_request"
#     answer_text = "Sure—how many and which sunglasses would you like to return?"
# else:
#     qty = int(match.group(1))
#     style = match.group(2)

#     # 4) Query inventory for the specified style (case-insensitive)
#     Item = Query()
#     item_row = inventory_tbl.get(Item.name.test(lambda v, s=style: v.lower() == s.lower()))

#     if not item_row:
#         # No matching style found
#         STATUS = "no_match"
#         # Suggest closest by price or style - for brevity, mention we don't have it
#         answer_text = f"Sorry, we don’t have {style} sunglasses in our inventory right now."
#     else:
#         # 5) Process return: update stock, insert transaction
#         unit_price = item_row["price"]
#         # Total refund amount is negative (money out of register)
#         total_refund = - unit_price * qty

#         # 6) Perform mutation
#         ACTION = "mutate"
#         SHOULD_MUTATE = True

#         # 7) Update inventory: increase stock by returned quantity
#         new_stock = item_row["quantity_in_stock"] + qty
#         inventory_tbl.update({"quantity_in_stock": new_stock}, doc_ids=[item_row.doc_id])

#         # 8) Insert transaction record
#         current_balance = get_current_balance(transactions_tbl)
#         new_balance = current_balance + total_refund
#         txn_id = next_transaction_id(transactions_tbl, prefix="TXN")
#         transactions_tbl.insert({
#             "transaction_id": txn_id,
#             "customer_name": item_row["name"],
#             "transaction_summary": f"Return of {qty} {item_row['name']} sunglasses",
#             "transaction_amount": total_refund,
#             "balance_after_transaction": new_balance,
#             "timestamp": datetime.now().isoformat()
#         })

#         # 9) Prepare success response
#         STATUS = "success"
#         answer_text = (f"Sure, I’ve processed your return of {qty} {item_row['name']} sunglasses "
#                        f"and refunded ${abs(total_refund)}.")

# # 10) Log action
# print(f"LOG: ACTION={ACTION or 'read'} SHOULD_MUTATE={SHOULD_MUTATE} STATUS={STATUS}")

# # The user-facing message
# </execute_python>
}

utils.print_html(json.dumps(transactions_tbl.all(), indent=2), title="Transactions Table Before Return")
# Transactions Table Before Return
# [
#   {
#     "transaction_id": "TXN001",
#     "customer_name": "OPENING_BALANCE",
#     "transaction_summary": "Daily opening register balance",
#     "transaction_amount": 500.0,
#     "balance_after_transaction": 500.0,
#     "timestamp": "2026-09-09T09:11:25.204434"
#   }
# ]

# Execute the generated plan for the round-sunglasses question
result = execute_generated_code(
    full_content_aviator,          # the full LLM response you generated earlier
    db=db,
    inventory_tbl=inventory_tbl,
    transactions_tbl=transactions_tbl,
    user_request=prompt_aviator, # e.g., "Return 2 aviator sunglasses I bought last week."
)

# Peek at exactly what Python the plan executed
utils.print_html(result["answer"], title="Plan Execution · Extracted Answer")
# Plan Execution · Extracted Answer
# Sure, I’ve processed your return of 2 Aviator sunglasses and refunded $160.

# After all, there will be a new row in transaction db and quantity +2 in inventory db

# NOTE: PUTTING IT ALL TOGETHER
def customer_service_agent(
    question: str,
    *,
    db,
    inventory_tbl,
    transactions_tbl,
    model: str = "o4-mini",
    temperature: float = 1.0,
    reseed: bool = False,
) -> dict:
    """
    End-to-end helper:
      1) (Optional) reseed inventory & transactions
      2) Generate plan-as-code from `question`
      3) Execute in a controlled namespace
      4) Render before/after snapshots and return artifacts

    Returns:
      {
        "full_content": <raw LLM response (may include <execute_python> tags)>,
        "exec": {
            "code": <extracted python>,
            "stdout": <plan logs>,
            "error": <traceback or None>,
            "answer": <answer_text/rows/json>,
            "inventory_after": [...],
            "transactions_after": [...]
        }
      }
    """
    # 0) Optional reseed
    if reseed:
        inv_utils.create_inventory()
        inv_utils.create_transactions()

    # 1) Show the question
    utils.print_html(question, title="User Question")

    # 2) Generate plan-as-code (FULL content)
    full_content = generate_llm_code(
        question,
        inventory_tbl=inventory_tbl,
        transactions_tbl=transactions_tbl,
        model=model,
        temperature=temperature,
    )
    utils.print_html(full_content, title="Plan with Code (Full Response)")

    # 3) Before snapshots
    utils.print_html(json.dumps(inventory_tbl.all(), indent=2), title="Inventory Table · Before")
    utils.print_html(json.dumps(transactions_tbl.all(), indent=2), title="Transactions Table · Before")

    # 4) Execute
    exec_res = execute_generated_code(
        full_content,
        db=db,
        inventory_tbl=inventory_tbl,
        transactions_tbl=transactions_tbl,
        user_request=question,
    )

    # 5) After snapshots + final answer
    utils.print_html(exec_res["answer"], title="Plan Execution · Extracted Answer")
    utils.print_html(json.dumps(inventory_tbl.all(), indent=2), title="Inventory Table · After")
    utils.print_html(json.dumps(transactions_tbl.all(), indent=2), title="Transactions Table · After")

    # 6) Return artifacts
    return {
        "full_content": full_content,
        "exec": {
            "code": exec_res["code"],
            "stdout": exec_res["stdout"],
            "error": exec_res["error"],
            "answer": exec_res["answer"],
            "inventory_after": inventory_tbl.all(),
            "transactions_after": transactions_tbl.all(),
        },
    }

# TEST:
prompt = "I want to buy 3 pairs of classic sunglasses and 1 pair of aviator sunglasses."

out = customer_service_agent(
    prompt,
    db=db,
    inventory_tbl=inventory_tbl,
    transactions_tbl=transactions_tbl,
    model="o4-mini",
    temperature=1.0,
    reseed=True,   # set False to keep current state of the inventory and the transactions
)
# User Question
# I want to buy 3 pairs of classic sunglasses and 1 pair of aviator sunglasses.

{
# Plan with Code (Full Response)
# <execute_python>
# # 1) Import required modules
# import re, datetime
# from tinydb import Query

# # 2) Initialize response variables
# STATUS = None
# answer_text = ""

# # 3) Parse user_request for purchase quantities and items
# #    Expect patterns like "3 pairs of classic" or "1 pair of aviator"
# pattern = re.compile(r'(\d+)\s+pair[s]?\s+of\s+(\w+)', re.IGNORECASE)
# matches = pattern.findall(user_request)

# # 4) Validate parsing
# if not matches:
#     STATUS = "invalid_request"
#     answer_text = "I can help with that—how many pairs would you like to purchase?"
#     print(f"LOG: ACTION=read DRY_RUN=True STATUS={STATUS}")
# else:
#     # 5) Build order list
#     order = []
#     for qty_str, style in matches:
#         order.append({"style": style.lower(), "quantity": int(qty_str)})
    
#     # 6) Check stock for each item
#     insufficient = []
#     items_to_process = []
#     for item in order:
#         Style = item["style"]
#         Qty = item["quantity"]
#         # Query inventory by name case-insensitive
#         q = Query()
#         result = inventory_tbl.get(q.name.test(lambda n, style=Style: n.lower() == style))
#         if not result:
#             insufficient.append({"style": Style, "reason": "no_match"})
#         elif result["quantity_in_stock"] < Qty:
#             insufficient.append({"style": Style, "reason": "low_stock", "available": result["quantity_in_stock"]})
#         else:
#             items_to_process.append({"record": result, "quantity": Qty})
    
#     # 7) Handle stock issues
#     if insufficient:
#         # If any no_match or low_stock, abort mutation
#         item = insufficient[0]
#         if item.get("reason") == "no_match":
#             STATUS = "no_match"
#             answer_text = (f"Sorry, we don’t have {item['style'].capitalize()} sunglasses right now. "
#                            "Can I suggest another style?")
#         else:
#             STATUS = "insufficient_stock"
#             available = item["available"]
#             answer_text = (f"We only have {available} pair{'s' if available != 1 else ''} of "
#                            f"{item['style'].capitalize()} available; let me know if that works for you.")
#         print(f"LOG: ACTION=read DRY_RUN=True STATUS={STATUS}")
#     else:
#         # 8) Proceed with mutation
#         STATUS = "success"
#         # Get starting balance
#         current_balance = get_current_balance(transactions_tbl)
#         for entry in items_to_process:
#             rec = entry["record"]
#             qty = entry["quantity"]
#             unit_price = rec["price"]
#             line_total = unit_price * qty
#             # Generate new transaction ID
#             txn_id = next_transaction_id(transactions_tbl, prefix="TXN")
#             # Build transaction row
#             txn = {
#                 "transaction_id": txn_id,
#                 "customer_name": "GUEST",
#                 "transaction_summary": f"Purchase of {qty} {rec['name']} sunglasses",
#                 "transaction_amount": float(line_total),
#                 "balance_after_transaction": float(current_balance + line_total),
#                 "timestamp": datetime.datetime.now().isoformat()
#             }
#             # 8a) Insert transaction
#             transactions_tbl.insert(txn)
#             # 8b) Update balance for next iteration
#             current_balance += line_total
#             # 8c) Update inventory stock
#             inventory_tbl.update(
#                 {"quantity_in_stock": rec["quantity_in_stock"] - qty},
#                 Query().item_id == rec["item_id"]
#             )
#         # 9) Prepare confirmation message
#         parts = [f"{e['quantity']} {e['record']['name']}" for e in items_to_process]
#         order_desc = " and ".join(parts)
#         answer_text = f"Your purchase of {order_desc} sunglasses is confirmed—thank you for shopping with us!"
#         print(f"LOG: ACTION=mutate DRY_RUN=False STATUS={STATUS}")

# # End of execution  
# </execute_python>
}

{
# Inventory Table · Before
# [
#   {
#     "item_id": "SG001",
#     "name": "Aviator",
#     "description": "Originally designed for pilots, these teardrop-shaped lenses with thin metal frames offer timeless appeal. The large lenses provide excellent coverage while the lightweight construction ensures comfort during long wear.",
#     "quantity_in_stock": 23,
#     "price": 80
#   },
#   {
#     "item_id": "SG002",
#     "name": "Wayfarer",
#     "description": "Featuring thick, angular frames that make a statement, these sunglasses combine retro charm with modern edge. The rectangular lenses and sturdy acetate construction create a confident look.",
#     "quantity_in_stock": 6,
#     "price": 95
#   },
#   {
#     "item_id": "SG003",
#     "name": "Mystique",
#     "description": "Inspired by 1950s glamour, these frames sweep upward at the outer corners to create an elegant, feminine silhouette. The subtle curves and often embellished temples add sophistication to any outfit.",
#     "quantity_in_stock": 3,
#     "price": 70
#   },
#   {
#     "item_id": "SG004",
#     "name": "Sport",
#     "description": "Designed for active lifestyles, these wraparound sunglasses feature a single curved lens that provides maximum coverage and wind protection. The lightweight, flexible frames include rubber grips.",
#     "quantity_in_stock": 11,
#     "price": 110
#   },
#   {
#     "item_id": "SG005",
#     "name": "Classic",
#     "description": "Classic round profile with minimalist metal frames, offering a timeless and versatile style that fits both casual and formal wear.",
#     "quantity_in_stock": 10,
#     "price": 60
#   },
#   {
#     "item_id": "SG006",
#     "name": "Moon",
#     "description": "Oversized round style with bold plastic frames, evoking retro aesthetics with a modern twist.",
#     "quantity_in_stock": 10,
#     "price": 120
#   }
# ]
# Transactions Table · Before
# [
#   {
#     "transaction_id": "TXN001",
#     "customer_name": "OPENING_BALANCE",
#     "transaction_summary": "Daily opening register balance",
#     "transaction_amount": 500.0,
#     "balance_after_transaction": 500.0,
#     "timestamp": "2026-09-09T09:43:24.441930"
#   }
# ]    
}

# Plan Execution · Extracted Answer
# Your purchase of 3 Classic and 1 Aviator sunglasses is confirmed—thank you for shopping with us!

{
# Inventory Table · After
# [
#   {
#     "item_id": "SG001",
#     "name": "Aviator",
#     "description": "Originally designed for pilots, these teardrop-shaped lenses with thin metal frames offer timeless appeal. The large lenses provide excellent coverage while the lightweight construction ensures comfort during long wear.",
#     "quantity_in_stock": 22,
#     "price": 80
#   },
#   {
#     "item_id": "SG002",
#     "name": "Wayfarer",
#     "description": "Featuring thick, angular frames that make a statement, these sunglasses combine retro charm with modern edge. The rectangular lenses and sturdy acetate construction create a confident look.",
#     "quantity_in_stock": 6,
#     "price": 95
#   },
#   {
#     "item_id": "SG003",
#     "name": "Mystique",
#     "description": "Inspired by 1950s glamour, these frames sweep upward at the outer corners to create an elegant, feminine silhouette. The subtle curves and often embellished temples add sophistication to any outfit.",
#     "quantity_in_stock": 3,
#     "price": 70
#   },
#   {
#     "item_id": "SG004",
#     "name": "Sport",
#     "description": "Designed for active lifestyles, these wraparound sunglasses feature a single curved lens that provides maximum coverage and wind protection. The lightweight, flexible frames include rubber grips.",
#     "quantity_in_stock": 11,
#     "price": 110
#   },
#   {
#     "item_id": "SG005",
#     "name": "Classic",
#     "description": "Classic round profile with minimalist metal frames, offering a timeless and versatile style that fits both casual and formal wear.",
#     "quantity_in_stock": 7,
#     "price": 60
#   },
#   {
#     "item_id": "SG006",
#     "name": "Moon",
#     "description": "Oversized round style with bold plastic frames, evoking retro aesthetics with a modern twist.",
#     "quantity_in_stock": 10,
#     "price": 120
#   }
# ]
# Transactions Table · After
# [
#   {
#     "transaction_id": "TXN001",
#     "customer_name": "OPENING_BALANCE",
#     "transaction_summary": "Daily opening register balance",
#     "transaction_amount": 500.0,
#     "balance_after_transaction": 500.0,
#     "timestamp": "2026-09-09T09:43:24.441930"
#   },
#   {
#     "transaction_id": "TXN002",
#     "customer_name": "GUEST",
#     "transaction_summary": "Purchase of 3 Classic sunglasses",
#     "transaction_amount": 180.0,
#     "balance_after_transaction": 680.0,
#     "timestamp": "2026-09-09T09:43:35.454700"
#   },
#   {
#     "transaction_id": "TXN003",
#     "customer_name": "GUEST",
#     "transaction_summary": "Purchase of 1 Aviator sunglasses",
#     "transaction_amount": 80.0,
#     "balance_after_transaction": 760.0,
#     "timestamp": "2026-09-09T09:43:35.482013"
#   }
# ]
}