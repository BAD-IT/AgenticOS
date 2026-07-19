import asyncio
import os
import asyncpg
from src.maintenance.diagnostics import triage_fatal_error
from src.maintenance.idle_daemon import check_queues_empty, garbage_collection, flush_vram, generate_skill_from_task

DB_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/agenticos")

async def run_tests():
    print("--- Test 1: Triage (Category B Classification) ---")
    mock_error_trace = "Exception in request: HTTP 401 Unauthorized for endpoint api.openai.com/v1"
    category = triage_fatal_error(mock_error_trace)
    print(f"Error Trace: {mock_error_trace}")
    print(f"Triaged as: {category}")
    assert "Category B" in category

    print("\n--- Test 2: Idle Mode Activation (Garbage Collection) ---")
    # Mock empty queues
    queues = {"tasks_queue": 0, "pending_queue": 0, "user_input_queue": 5}
    is_idle = check_queues_empty(queues)
    print(f"System Idle State: {is_idle}")
    assert is_idle is True
    
    # Create mock tmp file
    os.makedirs("workspace/outbox", exist_ok=True)
    with open("workspace/outbox/mock_cache.tmp", "w") as f:
        f.write("garbage data")
        
    removed_count = garbage_collection()
    vram_flushed = flush_vram()
    print(f"Garbage Collected Files: {removed_count}")
    print(f"VRAM Flushed: {vram_flushed}")
    assert removed_count > 0
    assert vram_flushed is True

    print("\n--- Test 3: Experience Consolidation (Skill Generation & pgvector) ---")
    skill = generate_skill_from_task("Deploy Kubernetes Cluster", "Step 1: Fail\nStep 2: Fix Helm\nStep 3: Success")
    print(f"Generated Skill Abstraction: {skill['skill_abstraction']}")
    print(f"Generated Vector: {skill['embedding']}")
    
    print("\nConnecting to PostgreSQL to insert embedding...")
    conn = await asyncpg.connect(DB_URL)
    
    # Insert the skill natively using pgvector cast
    await conn.execute(
        "INSERT INTO agent_skills (task_intent, skill_abstraction, embedding) VALUES ($1, $2, $3::vector)",
        skill['task_intent'], skill['skill_abstraction'], str(skill['embedding'])
    )
    
    # Query to verify pgvector insertion
    row = await conn.fetchrow("SELECT id, embedding FROM agent_skills ORDER BY id DESC LIMIT 1")
    print(f"DB Read Verification - ID: {row['id']}, Vector: {row['embedding']}")
    assert row['embedding'] is not None
    
    await conn.close()

    print("\nSUCCESS: All SRE Diagnostics, Triage, and Skill Generation logic passed!")

if __name__ == "__main__":
    asyncio.run(run_tests())
