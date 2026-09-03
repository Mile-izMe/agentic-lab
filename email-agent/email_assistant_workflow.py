# This agentic workflow can carry out various tasks related to email management, including sending emails, searching for emails from a specific sender, and deleting emails. 
# You’ll give it natural language instructions - like “check unread emails from my boss” or “delete the Happy Hour email” 
# And see how it selects the right tools and completes the task for you.

# * OUTCOME:
# Be able to connect an LLM to tools with AISuite,
# give natural language instructions, 
# observe how the agent selects, executes, 
# validates multi-step tasks such as searching, sending, and deleting emails.

# ================================
# Imports
# ================================

# --- Third-party ---
from dotenv import load_dotenv
import aisuite as ai
import json

# --- Local / project ---
import utils
import display_functions
import email_tools

# ================================
# Environment & Client
# ================================
load_dotenv()          # Load environment variables from .env
client = ai.Client()   # Initialize AISuite client

# * ENDPOINTS
# POST /send → send a new email
# GET /emails → list all emails
# GET /emails/unread → show only unread emails
# GET /emails/{id} → fetch a specific email by ID
# GET /emails/search?q=... → search emails by keyword
# GET /emails/filter → filter by recipient or date range
# PATCH /emails/{id}/read → mark an email as read
# PATCH /emails/{id}/unread → mark an email as unread
# DELETE /emails/{id} → delete an email by ID
# GET /reset_database → reset emails to initial state (for testing)

new_email_id = utils.test_send_email()
_ = utils.test_get_email(new_email_id['id'])
_ = utils.test_list_emails()
_ = utils.test_filter_emails(recipient="test@example.com")
_ = utils.test_search_emails("lunch")
_ = utils.test_unread_emails()
_ = utils.test_mark_read(new_email_id['id'])
_ = utils.test_mark_unread(new_email_id['id'])
_ = utils.test_delete_email(new_email_id['id'])
_ = utils.reset_database()

# * TOOL LAYER
# Now suppose that the endpoints are working, 
# the next step is to expose them to the LLM as Python functions called tools. 
# Each tool wraps a REST route, transforming raw API calls into actions the agent can perform—like list, read, search, send, delete, or toggle read.

# Think of tools as the agent’s actuators: 
# you give a natural language instruction (“check unread emails from my boss and send a polite reply”), 
# and the model chooses which tools to call and in what order to complete the task.

# * AVAILABLE TOOLS
# | Tool Function                      | Action                                                                 |
# |------------------------------------|------------------------------------------------------------------------|
# | `list_all_emails()`                | Fetch all emails, newest first                                         |
# | `list_unread_emails()`             | Retrieve only unread emails                                            |
# | `search_emails(query)`             | Search by keyword in subject, body, or sender                          |
# | `filter_emails(...)`               | Filter by recipient and/or date range                                  |
# | `get_email(email_id)`              | Fetch a specific email by ID                                           |
# | `mark_email_as_read(id)`           | Mark an email as read                                                  |
# | `mark_email_as_unread(id)`         | Mark an email as unread                                                |
# | `send_email(...)`                  | Send a new (simulated) email                                           |
# | `delete_email(id)`                 | Delete an email by ID                                                  |
# | `search_unread_from_sender(addr)`  | Return unread emails from a given sender (e.g., `boss@email.com`)      |

new_email = email_tools.send_email("test@example.com", "Lunch plans", "Shall we meet at noon?")
content_ = email_tools.get_email(new_email['id'])
#content_ = email_tools.list_all_emails()
#content_ = email_tools.list_unread_emails()
#content_ = email_tools.search_emails("lunch")
#content_ = email_tools.filter_emails(recipient="test@example.com")
#content_ = email_tools.mark_email_as_read(new_email['id'])
#content_ = email_tools.mark_email_as_unread(new_email['id'])
#content_ = email_tools.search_unread_from_sender("test@example.com")
#content_ = email_tools.delete_email(new_email['id'])
utils.print_html(content=json.dumps(content_, indent=2), title="Testing the email_tools")

# * AGENT PROMPT:

# Create a small helper function called build_prompt(). This function wraps the natural language request in a system-style preamble so the LLM:
# Recognizes that it’s acting as an email assistant agent
# Understands it has permission to use the available tools
# Executes actions directly, without asking for confirmation (no human-in-the-loop)
def build_prompt(request_: str) -> str:
    return f"""
- You are an AI assistant specialized in managing emails.
- You can perform various actions such as listing, searching, filtering, and manipulating emails.
- Use the provided tools to interact with the email system.
- Never ask the user for confirmation before performing an action.
- If needed, my email address is "demo@email.com" so you can use it to send emails or perform actions related to my account.

{request_.strip()}
"""

# TEST -> HOW FUNCTION WRAPS RAW USER PROMPT
example_prompt = build_prompt("Delete the Happy Hour email")
utils.print_html(content=example_prompt, title="Example example_prompt")
# Example example_prompt

# - You are an AI assistant specialized in managing emails.
# - You can perform various actions such as listing, searching, filtering, and manipulating emails.
# - Use the provided tools to interact with the email system.
# - Never ask the user for confirmation before performing an action.
# - If needed, my email address is "demo@email.com" so you can use it to send emails or perform actions related to my account.

# Delete the Happy Hour email


# * LLM + EMAIL TOOLS
# 1. Scenario: “Check for unread emails from boss@email.com, mark them as read, and send a polite follow-up.”
# 2. What Happen:
#   1. The agent interprets your instruction.
#   2. It selects the right tools (search_unread_from_sender → mark_email_as_read → send_email).
#   3. It executes each action automatically, without asking for confirmation.
# => Focus on what the agent achieves, not how to call the API.
# 3. Run
prompt_ = build_prompt("Check for unread emails from boss@email.com, mark them as read, and send a polite follow-up.")
prompt2 = build_prompt("Search for all emails containing the keyword 'lunch'. Fetch the content of the first result to check what it's about, and then delete that email.")
prompt3 = build_prompt("List all my unread emails. Fetch the full content of the most recent one so I can see what it says, and then mark it as read.")

response = client.chat.completions.create(
    model="openai:gpt-4.1", # LLM
    messages=[{"role": "user", "content": (
        prompt_
    )}],
    tools=[ # list of tools that the LLM can access
        email_tools.search_unread_from_sender,
        email_tools.list_unread_emails,
        email_tools.search_emails,
        email_tools.get_email,
        email_tools.mark_email_as_read,
        email_tools.send_email,
        email_tools.delete_email
    ],
    max_turns=5,
)

display_functions.pretty_print_chat_completion(response)
{
# 🧠 LLM Action: search_unread_from_sender
# {
#   "sender": "boss@email.com"
# }

# 🔧 Tool Response: search_unread_from_sender
# [
#   {
#     "id": 1,
#     "sender": "boss@email.com",
#     "recipient": "you@email.com",
#     "subject": "Quarterly Report",
#     "body": "Please finalize the report ASAP.",
#     "timestamp": "2026-09-03T10:53:36.801850",
#     "read": false
#   }
# ]

# 🧠 LLM Action: mark_email_as_read
# {
#   "email_id": 1
# }

# 🧠 LLM Action: send_email
# {
#   "recipient": "boss@email.com",
#   "subject": "Re: Quarterly Report",
#   "body": "Dear Boss,\n\nThank you for your message regarding the quarterly report. I have received your email and will proceed accordingly. Please let me know if there's anything else you need.\n\nBest regards,\n[Your Name]"
# }

# 🔧 Tool Response: mark_email_as_read
# {
#   "id": 1,
#   "sender": "boss@email.com",
#   "recipient": "you@email.com",
#   "subject": "Quarterly Report",
#   "body": "Please finalize the report ASAP.",
#   "timestamp": "2026-09-03T10:53:36.801850",
#   "read": true
# }

# 🔧 Tool Response: send_email
# {
#   "id": 7,
#   "sender": "you@mail.com",
#   "recipient": "boss@email.com",
#   "subject": "Re: Quarterly Report",
#   "body": "Dear Boss,\n\nThank you for your message regarding the quarterly report. I have received your email and will proceed accordingly. Please let me know if there's anything else you need.\n\nBest regards,\n[Your Name]",
#   "timestamp": "2026-09-03T10:57:47.617631",
#   "read": false
# }

# ✅ Final Assistant Message:
# The unread email from boss@email.com regarding the "Quarterly Report" has been marked as read. 
# A polite follow-up message has also been sent to your boss acknowledging the email and offering further assistance. 
# If you need anything else related to this conversation or other emails, let me know!

# 🧭 Tool Sequence:
# search_unread_from_sender → mark_email_as_read → send_email
}

# Targeted Action: Delete the “Happy Hour” email
prompt4 = build_prompt("Delete the happy hour email")

response = client.chat.completions.create(
    model="openai:o4-mini",
    messages=[{"role": "user", "content": (
        prompt4
    )}],
    tools=[
        email_tools.search_unread_from_sender,
        email_tools.list_unread_emails,
        email_tools.search_emails,
        email_tools.get_email,
        email_tools.mark_email_as_read,
        email_tools.send_email,
        email_tools.delete_email
    ],
    max_turns=5
)

display_functions.pretty_print_chat_completion(response)
{
# 🧠 LLM Action: search_emails
# {
#   "query": "happy hour"
# }

# 🔧 Tool Response: search_emails
# [
#   {
#     "id": 5,
#     "sender": "eric@work.com",
#     "recipient": "you@email.com",
#     "subject": "Happy Hour",
#     "body": "We're planning drinks this Friday!",
#     "timestamp": "2026-09-03T10:53:36.801850",
#     "read": false
#   }
# ]

# 🧠 LLM Action: delete_email
# {
#   "email_id": 5
# }

# 🔧 Tool Response: delete_email
# {
#   "message": "Email deleted"
# }

# ✅ Final Assistant Message:
# The “Happy Hour” email has been deleted. Let me know if there’s anything else I can help with.

# 🧭 Tool Sequence:
# search_emails → delete_email
}