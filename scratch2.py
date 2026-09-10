import os
from dotenv import load_dotenv
import requests

load_dotenv()
key = os.getenv('ANTHROPIC_API_KEY')

response = requests.get(
    'https://api.anthropic.com/v1/models',
    headers={
        'x-api-key': key,
        'anthropic-version': '2023-06-01'
    }
)
print(response.status_code)
print(response.json())
