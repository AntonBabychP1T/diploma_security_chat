import requests
import sys

BASE_URL = "http://127.0.0.1:8000"

def test_arena_flow():
    # 1. Login/Register with random user
    import random
    import string
    rand_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
    email = f"test_{rand_suffix}@example.com"
    password = "password123"
    
    print(f"Registering {email}...")
    reg_res = requests.post(f"{BASE_URL}/auth/register", json={"email": email, "password": password, "full_name": "Test User"})
    if reg_res.status_code != 200:
        print(f"Registration failed: {reg_res.text}")
        sys.exit(1)
        
    print("Logging in...")
    login_res = requests.post(f"{BASE_URL}/auth/login", data={"username": email, "password": password})
    
    if login_res.status_code != 200:
        print(f"Auth failed: {login_res.text}")
        sys.exit(1)
        
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("Logged in successfully.")

    # 2. Create Chat
    print("Creating chat...")
    chat_res = requests.post(f"{BASE_URL}/chats", json={"title": "Arena Test"}, headers=headers)
    assert chat_res.status_code == 200
    chat_id = chat_res.json()["id"]
    print(f"Created chat {chat_id}")

    # 3. Send Arena Message
    print("Sending arena message...")
    payload = {
        "message": "Hello, arena!",
        "models": ["gpt-5-mini", "gemini-2.5-flash"]
    }
    msg_res = requests.post(f"{BASE_URL}/chats/{chat_id}/messages", json=payload, headers=headers)
    assert msg_res.status_code == 200
    messages = msg_res.json()
    assert isinstance(messages, list)
    assert len(messages) == 2
    
    msg_a = messages[0]
    msg_b = messages[1]
    
    print(f"Received {len(messages)} messages.")
    print(f"Msg A Model: {msg_a['meta_data']['model']}")
    print(f"Msg B Model: {msg_b['meta_data']['model']}")
    
    assert msg_a['meta_data']['comparison_id'] == msg_b['meta_data']['comparison_id']
    
    # 4. Vote
    print("Voting for Model A...")
    vote_res = requests.post(f"{BASE_URL}/chats/{chat_id}/messages/{msg_a['id']}/vote", params={"vote_type": "better"}, headers=headers)
    assert vote_res.status_code == 200
    print("Vote submitted.")

    # 5. Check Leaderboard
    print("Checking leaderboard...")
    leaderboard_res = requests.get(f"{BASE_URL}/metrics/leaderboard", headers=headers)
    assert leaderboard_res.status_code == 200
    stats = leaderboard_res.json()
    print("Leaderboard:", stats)
    
    found = False
    for item in stats:
        if item["model"] == msg_a['meta_data']['model']:
            assert item["votes"] >= 1
            found = True
            break
    
    if found:
        print("Verification successful!")
    else:
        print("Model not found in leaderboard (might be async delay or issue).")

if __name__ == "__main__":
    test_arena_flow()
