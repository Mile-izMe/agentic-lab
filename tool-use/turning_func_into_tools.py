import json
import display_functions
from dotenv import load_dotenv
from datetime import datetime
import aisuite as ai

_ = load_dotenv()
# Create an instance of the AISuite client
client = ai.Client()

# * BUILD TOOLS
## Notice that this tool includes a docstring explanation of the functions purpose.
## This is important for aisuite because it will use this to help define the tool to the LLM
def get_current_time():
    """
    Returns the current time as a string.
    """
    return datetime.now().strftime("%H:%M:%S")

# test -> '08:58:13'
get_current_time()

# * TURN FUNC INTO LLM TOOL

# Message structure includes: prompt user ask + dictionary represents the conversation history + each message having a role & content
# prompt = "What time is it?"
# messages = [
#     {
#         "role": "user",
#         "content": prompt,
#     }
# ]

# Params:
# model: The model that will be used
# messages: The list of messages passed to the LLM
# tools: The list of tools that the LLM has access to
# max_turns: This is the maximum amount of messages the LLM will be allowed to make. 
#            This can help prevent the LLM from getting into infinite loops and 
#            repeatedly calling a tool.
# response = client.chat.completions.create(
#     model="openai:gpt-4o",
#     messages=messages,
#     tools=[get_current_time],
#     max_turns=5
# )

# See the LLM response -> The current time is 09:02:58.
# print(response.choices[0].message.content)

# See the behind the scenes of response
# 🧠 LLM Action: get_current_time
# {}

# 🔧 Tool Response: get_current_time
# "09:02:58"

# ✅ Final Assistant Message:
# The current time is 09:02:58.

# 🧭 Tool Sequence:
# get_current_time
# display_functions.pretty_print_chat_completion(response)


# * DEFINING TOOLS
# Parts:
# name: The name of the corresponding function that you defined locally
# description: A description that explains what the function does and is used by the LLM to help it decide when to use it
# parameters: If your function has parameters, they would also be described with the parameter name and a description of what the parameter should be.
# tools = [{
#     "type": "function",
#     "function": {
#         "name": "get_current_time", # <--- Your functions name
#         "description": "Returns the current time as a string.", # <--- a description for the LLM
#         "parameters": {}
#     }
# }]

# response = client.chat.completions.create(
#     model="openai:gpt-4o",
#     messages=messages,
#     tools=tools, # <-- Your list of tools with get_current_time
#     # max_turns=5 # <-- When defining tools manually, you must handle calls yourself and cannot use max_turns
# )

# print(json.dumps(response.model_dump(), indent=2, default=str))
# {
#   "id": "chatcmpl-EJUogxjsDUhKTKO0gXmJ20EfeXGUh",
#   "choices": [
#     {
#       "finish_reason": "tool_calls",
#       "index": 0,
#       "logprobs": null,
#       "message": {
#         "content": null,
#         "refusal": null,
#         "role": "assistant",
#         "annotations": [],
#         "audio": null,
#         "function_call": null,
#         "tool_calls": [
#           {
#             "id": "call_99FBBbYktaRehOUkdXF08FK9",
#             "function": {
#               "arguments": "{}",
#               "name": "get_current_time"
#             },
#             "type": "function"
#           }
#         ]
#       }
#     }
#   ],
#   "created": 1788315398,
#   "model": "gpt-4o-2024-08-06",
#   "object": "chat.completion",
#   "service_tier": "default",
#   "system_fingerprint": "fp_4899888b17",
#   "usage": {
#     "completion_tokens": 11,
#     "prompt_tokens": 45,
#     "total_tokens": 56,
#     "completion_tokens_details": {
#       "accepted_prediction_tokens": 0,
#       "audio_tokens": 0,
#       "reasoning_tokens": 0,
#       "rejected_prediction_tokens": 0
#     },
#     "prompt_tokens_details": {
#       "audio_tokens": 0,
#       "cached_tokens": 0
#     }
#   }
# }

# Response 2
# response2 = None

# Create a condition in case tool_calls is in response object
# if response.choices[0].message.tool_calls:
    # Pull out the specific tool metadata from the response
    # tool_call = response.choices[0].message.tool_calls[0]
    # args = json.loads(tool_call.function.arguments)

    # Run the tool locally
    # tool_result = get_current_time()

    # Append the result to the messages list
    # messages.append(response.choices[0].message)
    # messages.append({
    #     "role": "tool", "tool_call_id": tool_call.id, "content": str(tool_result)
    # })

    # Send the list of messages with the newly appended results back to the LLM
    # response2 = client.chat.completions.create(
    #     model="openai:gpt-4o",
    #     messages=messages,
    #     tools=tools,
    # )

    # print(response2.choices[0].message.content)
    # The current time is 09:09:21.
