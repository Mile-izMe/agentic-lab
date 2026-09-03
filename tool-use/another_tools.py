import requests
import qrcode
from qrcode.image.styledpil import StyledPilImage
import display_functions
from dotenv import load_dotenv
import aisuite as ai

_ = load_dotenv()
client = ai.Client()

def get_weather_from_ip():
    """
    Gets the current, high, and low temperature in Fahrenheit for the user's
    location and returns it to the user.
    """
    # Get location coordinates from the IP address
    lat, lon = requests.get('https://ipinfo.io/json').json()['loc'].split(',')

    # Set parameters for the weather API call
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m",
        "daily": "temperature_2m_max,temperature_2m_min",
        "temperature_unit": "fahrenheit",
        "timezone": "auto"
    }

    # Get weather data
    weather_data = requests.get("https://api.open-meteo.com/v1/forecast", params=params).json()

    # Format and return the simplified string
    return (
        f"Current: {weather_data['current']['temperature_2m']}°F, "
        f"High: {weather_data['daily']['temperature_2m_max'][0]}°F, "
        f"Low: {weather_data['daily']['temperature_2m_min'][0]}°F"
    )

# Write a text file
def write_txt_file(file_path: str, content: str):
    """
    Write a string into a .txt file (overwrites if exists).
    Args:
        file_path (str): Destination path.
        content (str): Text to write.
    Returns:
        str: Path to the written file.
    """
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
    return file_path


# Create a QR code
def generate_qr_code(data: str, filename: str, image_path: str):
    """Generate a QR code image given data and an image path.

    Args:
        data: Text or URL to encode
        filename: Name for the output PNG file (without extension)
        image_path: Path to the image to be used in the QR code
    """
    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_H)
    qr.add_data(data)

    img = qr.make_image(image_factory=StyledPilImage, embedded_image_path=image_path)
    output_file = f"{filename}.png"
    img.save(output_file)

    return f"QR code saved as {output_file} containing: {data[:50]}..."



# * USING TOOLS
# The LLM will choose the appropriate tool based on the prompt you send it.

# * WEATHER
# prompt = "Can you get the weather for my location?"
# response = client.chat.completions.create(
#     model="openai:o4-mini",
#     messages=[{"role": "user", "content": (
#         prompt
#     )}],
#     tools=[
#         get_weather_from_ip,
#         write_txt_file,
#         generate_qr_code
#     ],
#     max_turns=5
# )

# display_functions.pretty_print_chat_completion(response)
# 🧠 LLM Action: get_weather_from_ip
# {}

# 🔧 Tool Response: get_weather_from_ip
# "Current: 60.0\u00b0F, High: 76.7\u00b0F, Low: 57.6\u00b0F"

# ✅ Final Assistant Message:
# The current temperature at your location is 60.0°F, with a high of 76.7°F and a low of 57.6°F. Is there anything else you’d like to know?

# 🧭 Tool Sequence:
# get_weather_from_ip


# * TXT
# prompt = "Can you make a txt note for me called reminders.txt that reminds me to call Daniel tomorrow at 7PM?"

# response = client.chat.completions.create(
#     model="openai:o4-mini",
#     messages=[{"role": "user", "content": (
#         prompt
#     )}],
#     tools=[
#         get_weather_from_ip,
#         write_txt_file,
#         generate_qr_code
#     ],
#     max_turns=5
# )

# display_functions.pretty_print_chat_completion(response)
# 🧠 LLM Action: write_txt_file
# {
#   "file_path": "reminders.txt",
#   "content": "Reminder: Call Daniel tomorrow at 7PM"
# }

# 🔧 Tool Response: write_txt_file
# "reminders.txt"

# ✅ Final Assistant Message:
# Your note has been saved as "reminders.txt" with your reminder to call Daniel tomorrow at 7PM. Let me know if there’s anything else you’d like!

# 🧭 Tool Sequence:
# write_txt_file

# Open -> Reminder: Call Daniel tomorrow at 7PM
# with open('reminders.txt', 'r') as file:
#     contents = file.read()
#     print(contents)


# # * QR
# prompt = "Can you make a QR code for me using my company's logo that goes to www.deeplearning.ai? The logo is located at `dl_logo.jpg`. You can call it dl_qr_code."

# response = client.chat.completions.create(
#     model="openai:o4-mini",
#     messages=[{"role": "user", "content": (
#         prompt
#     )}],
#     tools=[
#         get_weather_from_ip,
#         write_txt_file,
#         generate_qr_code
#     ],
#     max_turns=5
# )

# display_functions.pretty_print_chat_completion(response)
# 🧠 LLM Action: generate_qr_code
# {
#   "data": "www.deeplearning.ai",
#   "filename": "dl_qr_code",
#   "image_path": "dl_logo.jpg"
# }

# 🔧 Tool Response: generate_qr_code
# "QR code saved as dl_qr_code.png containing: www.deeplearning.ai..."

# ✅ Final Assistant Message:
# Your QR code has been generated and saved as dl_qr_code.png. It embeds the DeepLearning.ai logo and points to www.deeplearning.ai. Let me know if you need anything else!

# 🧭 Tool Sequence:
# generate_qr_code

