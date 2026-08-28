import json
from google.genai import types as genai_types
from groq import Groq
from app.core.config import settings
from app.services.llm_service import _gemini_tool_to_groq_tool

raw_schema = {
    "properties": {
        "research_interests": {
            "title": "Research Interests",
            "type": "string"
        }
    },
    "required": ["research_interests"],
    "title": "search_professorsArguments",
    "type": "object"
}

tool = genai_types.FunctionDeclaration(
    name="search_professors",
    description="Search the web for professors.",
    parameters=raw_schema,
)

groq_tool = _gemini_tool_to_groq_tool(tool)
print("Converted Groq tool schema:")
print(json.dumps(groq_tool, indent=2))

client = Groq(api_key=settings.groq_api_key)
try:
    response = client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[{"role": "user", "content": "Find professors researching quantum computing"}],
        tools=[groq_tool],
        tool_choice="auto",
    )
    print("\nSUCCESS")
    print(response.choices[0].message)
except Exception as e:
    print("\nFAILED")
    print(f"Error: {e}")