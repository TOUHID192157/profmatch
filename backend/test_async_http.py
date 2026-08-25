from curl_cffi import requests as cf_requests
from app.core.config import settings

response = cf_requests.post(
    f"{settings.openrouter_base_url}/chat/completions",
    headers={
        "Authorization": f"Bearer {settings.openrouter_api_key}",
        "Content-Type": "application/json",
    },
    json={
        "model": settings.openrouter_model,
        "messages": [{"role": "user", "content": "Say hello"}],
    },
    impersonate="chrome",
    timeout=45,
)

print("STATUS:", response.status_code)
print("BODY:", response.text[:500])