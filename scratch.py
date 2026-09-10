import os
from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic

load_dotenv()
key = os.getenv('ANTHROPIC_API_KEY')
models = [
    'claude-3-5-sonnet-20241022',
    'claude-3-5-sonnet-20240620', 
    'claude-3-sonnet-20240229', 
    'claude-3-haiku-20240307'
]

for m in models:
    try:
        llm = ChatAnthropic(model_name=m, anthropic_api_key=key, max_tokens=5)
        llm.invoke('hi')
        print(f'{m}: SUCCESS')
    except Exception as e:
        print(f'{m}: {e}')
