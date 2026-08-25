import time
from app.agents.research_agent import run_research_agent_sync

print("[Test] Starting standalone Research Agent test...")
start_time = time.time()

try:
    result = run_research_agent_sync("quantum computing")
    elapsed = time.time() - start_time
    print(f"\n[Test] Finished in {elapsed:.2f} seconds!")
    print("\n--- Result ---")
    print(result)
except Exception as e:
    print(f"\n[Test] Error occurred: {e}")