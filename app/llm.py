import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def ask_llm(question: str):
    response = client.responses.create(
         model="gpt-4.1-mini",
        input=question,
    )
    return response; 

response = ask_llm(
    """
    I am a software engineer learning agentic AI.

    Explain:
    1. What is an LLM?
    2. What is a token?
    3. What is context?
    4. What is tool calling?

    Keep each explanation under 50 words.
    """
)

print(response)