import asyncio
from src.graph.workflow import create_graph
from src.core.models import GraphState, TaskObject, TaskStatus
from src.core.config import settings

async def main():
    print("Initializing LangGraph Cognitive Engine...")
    app = create_graph()
    
    # Create a mock task mimicking a DB row
    task = TaskObject(
        task_id="test-e2e",
        intent=f"Write a file named {settings.OUTBOX_DIR}/test.txt with the content 'Hello from LangGraph'",
        status=TaskStatus.USER_INPUT
    )
    
    state = {
        "current_task": task,
        "tool_error_count": 0,
        "failed_tool_hashes": [],
        "messages": [],
        "overseer_invocation_count": 0
    }
    
    print(f"\nStarting Execution for Intent: {task.intent}")
    
    # Run the graph
    try:
        final_state = await app.ainvoke(state)
        
        print("\n=== Execution Complete ===")
        current_task = final_state.get('current_task')
        if current_task:
            print(f"Final Task Status: {current_task.status}")
        print("Messages Trace:")
        for msg in final_state.get('messages', []):
            msg_type = type(msg).__name__
            print(f"[{msg_type}]: {msg.content}")
            
    except Exception as e:
        print(f"Graph execution failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())
