import os
import time
import json

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

questions = [
    "What is an LLM?",
    "What is an AI agent?",
    "What is tool calling?",
]
qustion2="""
    Explain what an LLM is for a software engineer who is new to AI.

    Give:
    - a short definition
    - 3 key concepts
    - 2 practical examples
    """

response = client.responses.create(
    model = "gpt-4.1-mini",
    input = qustion2,
   text={
        "format": {
            "type": "json_schema",
            "name": "llm_explanation",
            "schema": {
                "type": "object",
                "properties": {
                    "definition": {
                        "type": "string"
                    },
                    "key_concepts": {
                        "type": "array",
                        "items": {
                            "type": "string"
                        }
                    },
                    "examples": {
                        "type": "array",
                        "items": {
                            "type": "string"
                        }
                    }
                },
                "required": [
                    "definition",
                    "key_concepts",
                    "examples"
                ],
                "additionalProperties": False
            },
            "strict": True
        }
    }
)

data = json.loads(response.output_text)

print(data["definition"])
#print(response.output_text)







  