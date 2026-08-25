import asyncio
import time
from app.services.search_service import search_professors_web, extract_professors_with_gemini

async def main():
    print("[Test] Calling search_professors_web...")
    raw = await search_professors_web("quantum computing")
    print(f"[Test] Got {len(raw)} raw results")

    print("[Test] Calling extract_professors_with_gemini (with retry)...")
    for attempt in range(1, 4):
        try:
            professors = await extract_professors_with_gemini(raw)
            print(f"[Test] SUCCESS on attempt {attempt}: Got {len(professors)} professors")
            print(professors)
            return
        except Exception as e:
            print(f"[Test] Attempt {attempt} failed: {e}")
            if attempt < 3:
                print("[Test] Waiting 10s before retry...")
                time.sleep(10)

    print("[Test] All attempts failed.")

asyncio.run(main())