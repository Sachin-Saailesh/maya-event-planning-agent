import asyncio
import google.genai as genai
from google.genai import types as genai_types

def _call():
    client = genai.Client(api_key='fake_key')
    return client.models.generate_content(
        model='gemini-2.0-flash-preview-image-generation',
        contents='test',
        config=genai_types.GenerateContentConfig(
            response_modalities=['IMAGE', 'TEXT'],
        ),
    )

try:
    _call()
except Exception as e:
    print('EXCEPTION TYPE:', type(e).__name__)
    print('MSG:', str(e)[:300])
