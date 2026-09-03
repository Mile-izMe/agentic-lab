import display_functions
from dotenv import load_dotenv
import aisuite as ai
from another_tools import get_weather_from_ip, write_txt_file, generate_qr_code
from turning_func_into_tools import get_current_time

_ = load_dotenv("../.env")
client = ai.Client()

# * NOTICE:
# The LLM automatically chooses which tool to use based on the user request
# Parameters are inferred from the user's message (like file names, content, URLs)
# Each tool returns information that the LLM incorporates into its response
# No-parameter tools like weather and time are perfect for quick information requests
# The conversation feels natural despite complex operations happening behind the scenes

prompt = "Can you help me create a qr code that goes to www.deeplearning.com from the image dl_logo.jpg? Also write me a txt note with the current weather please."

response = client.chat.completions.create(
    model="google:gemini-1.5-flash",
    messages=[{"role": "user", "content": (
        prompt
    )}],
    tools=[
        get_weather_from_ip,
        get_current_time,
        write_txt_file,
        generate_qr_code
    ],
    max_turns=10
)

display_functions.pretty_print_chat_completion(response)
# 🧠 LLM Action: generate_qr_code
# {
#   "data": "www.deeplearning.com",
#   "filename": "dl_qr_code",
#   "image_path": "dl_logo.jpg"
# }

# 🔧 Tool Response: generate_qr_code
# "QR code saved as dl_qr_code.png containing: www.deeplearning.com..."

# 🧠 LLM Action: get_weather_from_ip
# {}

# 🔧 Tool Response: get_weather_from_ip
# "Current: 59.9\u00b0F, High: 76.7\u00b0F, Low: 57.6\u00b0F"

# 🧠 LLM Action: write_txt_file
# {
#   "file_path": "weather_note.txt",
#   "content": "Current weather: 59.9\u00b0F\nHigh: 76.7\u00b0F\nLow: 57.6\u00b0F"
# }

# 🔧 Tool Response: write_txt_file
# "weather_note.txt"

# ✅ Final Assistant Message:
# Your QR code has been generated and saved as “dl_qr_code.png” embedding www.deeplearning.com with the dl_logo.jpg image. 
# I also created a text file “weather_note.txt” containing the current weather: Current weather: 59.9°F High: 76.7°F Low: 57.6°F Let me know if you need anything else!

# 🧭 Tool Sequence:
# generate_qr_code → get_weather_from_ip → write_txt_file