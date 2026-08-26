from google import genai
import os
from dotenv import load_dotenv

load_dotenv()

keys = ['GEMINI_API_KEY', 'GEMINI_API_KEY_2', 'GEMINI_API_KEY_3', 'GEMINI_API_KEY_4']

for k in keys:
    key = os.getenv(k)
    try:
        client = genai.Client(api_key=key)
        r = client.models.generate_content(model='gemini-flash-latest', contents='hi')
        print(k, 'OK')
    except Exception as e:
        print(k, 'FAILED:', str(e)[:150])
