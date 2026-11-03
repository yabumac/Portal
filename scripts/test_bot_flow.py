print("1: Starting script", flush=True)
import asyncio
import os
import sys
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

os.environ["MOCK_SEND"] = "1"

print("2: Importing index", flush=True)
from api import index
print("3: Importing db, state, whatsapp", flush=True)
from bot import db, state, whatsapp
print("4: Importing curriculum", flush=True)
from content import curriculum
print("5: Defining run_tests", flush=True)

async def run_tests():
    print("==================================================", flush=True)
    print("Testing WhatsApp Learning Bot Progression & Persistence", flush=True)
    print("==================================================", flush=True)

    test_wa_id = "251911998877"
    print("Step 0: deleting test user", flush=True)
    db.delete_user(test_wa_id)
    print("Step 0 done", flush=True)

    # 1. Fresh user sends "hi"
    print("\n--- Step 1: User says 'hi' (Fresh) ---", flush=True)
    await index.handle_text(test_wa_id, "hi")
    print("Step 1 handle_text returned", flush=True)
    st1 = state.get_state(test_wa_id)
    print(f"User state after 'hi': phase={st1.get('phase')}, lesson_index={st1.get('lesson_index')}")
    assert st1 is not None, "User state should exist in DB"
    assert st1.get("phase") == "idle", f"Expected phase 'idle', got {st1.get('phase')}"

    # 2. User taps 'enroll' button
    print("\n--- Step 2: User taps 'enroll' ---")
    await index.handle_button_click(test_wa_id, index.ENROLL)
    st2 = state.get_state(test_wa_id)
    print(f"User state after enroll: phase={st2.get('phase')}, lesson_index={st2.get('lesson_index')}")
    assert st2.get("phase") == "lesson", f"Expected phase 'lesson', got {st2.get('phase')}"
    assert st2.get("lesson_index") == 0, f"Expected lesson_index 0, got {st2.get('lesson_index')}"

    # 3. User says 'hi' while in progress on Module 1 (Must NOT reset!)
    print("\n--- Step 3: User says 'hi' while in progress on Module 1 ---")
    await index.handle_text(test_wa_id, "hi")
    st3 = state.get_state(test_wa_id)
    print(f"User state after 'hi' mid-course: phase={st3.get('phase')}, lesson_index={st3.get('lesson_index')}")
    assert st3.get("lesson_index") == 0, "Lesson index must remain 0"
    assert st3.get("phase") == "lesson", "Phase must remain in progress"

    # 4. User taps 'quiz_ready'
    print("\n--- Step 4: User continues to quiz ---")
    await index.handle_button_click(test_wa_id, index.READY_QUIZ)
    st4 = state.get_state(test_wa_id)
    print(f"User state after READY_QUIZ: phase={st4.get('phase')}")
    assert st4.get("phase") == "quiz", f"Expected phase 'quiz', got {st4.get('phase')}"

    # 5. User submits correct answer 'C' (Diversified answer)
    print("\n--- Step 5: User answers quiz option 'C' ---")
    await index.handle_button_click(test_wa_id, f"{index.ANSWER_PREFIX}C")
    st5 = state.get_state(test_wa_id)
    print(f"User state after quiz answer: phase={st5.get('phase')}, lesson_index={st5.get('lesson_index')}")
    assert st5.get("lesson_index") == 1, f"Expected advancement to lesson_index 1, got {st5.get('lesson_index')}"
    assert "lesson_1" in st5.get("completed_lessons", []), "lesson_1 should be marked completed"

    # 6. Admin analytics query
    print("\n--- Step 6: Query Admin Analytics Summary ---")
    analytics = db.get_analytics_summary()
    summary = analytics["summary"]
    users = analytics["users"]
    print(f"Total Users: {summary['total_users']}")
    print(f"Active Learners: {summary['active_learners']}")
    print(f"Completed Graduates: {summary['completed_learners']}")
    print(f"Total Interactions: {summary['total_interactions']}")
    
    found_user = next((u for u in users if u["phone_number"] == test_wa_id), None)
    assert found_user is not None, f"User {test_wa_id} must appear in admin analytics users list!"
    print(f"Found User in Admin Registry: {found_user['phone_number']}, Progress: {found_user['progress_percent']}%, Phase: {found_user['phase']}")
    assert found_user["completed_count"] == 1, "Completed count should be 1"

    # Clean up test user
    db.delete_user(test_wa_id)
    print("\n[ALL TESTS PASSED] Flow, video-first structure, and persistence validated!")

if __name__ == "__main__":
    print("6: Calling asyncio.run", flush=True)
    asyncio.run(run_tests())
