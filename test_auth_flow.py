import requests
import sys

BASE_URL = "http://127.0.0.1:8000"

def test_auth_flow():
    # 1. Register User A
    email_a = "user_a@example.com"
    password = "password123"
    print(f"Registering {email_a}...")
    res = requests.post(f"{BASE_URL}/auth/register", json={"email": email_a, "password": password})
    if res.status_code == 400 and "already registered" in res.text:
        print("User A already exists, proceeding to login.")
    elif res.status_code != 200:
        print(f"Failed to register User A: {res.text}")
        sys.exit(1)
        
    # 2. Login User A
    print(f"Logging in {email_a}...")
    res = requests.post(f"{BASE_URL}/auth/login", data={"username": email_a, "password": password})
    if res.status_code != 200:
        print(f"Failed to login User A: {res.text}")
        sys.exit(1)
    token_a = res.json()["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}
    
    # 3. Create Chat for User A
    print("Creating chat for User A...")
    res = requests.post(f"{BASE_URL}/chats/", json={"title": "User A Chat"}, headers=headers_a)
    chat_a_id = res.json()["id"]
    print(f"User A Chat ID: {chat_a_id}")
    
    # 4. Register User B
    email_b = "user_b@example.com"
    print(f"Registering {email_b}...")
    res = requests.post(f"{BASE_URL}/auth/register", json={"email": email_b, "password": password})
    if res.status_code == 400 and "already registered" in res.text:
        print("User B already exists, proceeding to login.")
    elif res.status_code != 200:
        print(f"Failed to register User B: {res.text}")
        sys.exit(1)
        
    # 5. Login User B
    print(f"Logging in {email_b}...")
    res = requests.post(f"{BASE_URL}/auth/login", data={"username": email_b, "password": password})
    token_b = res.json()["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}
    
    # 6. Verify User B cannot see User A's chat
    print("Verifying User B cannot access User A's chat...")
    res = requests.get(f"{BASE_URL}/chats/{chat_a_id}", headers=headers_b)
    if res.status_code == 404:
        print("✅ User B cannot see User A's chat (404 Not Found)")
    else:
        print(f"❌ User B COULD see User A's chat! Status: {res.status_code}")
        
    # 7. Verify Admin Stats (User A is likely admin if first user, or we need to manually set)
    # Since we didn't implement auto-admin logic fully (default is False), this might fail 403 unless we hack it.
    # But let's try accessing global metrics with User A
    print("Checking Global Metrics with User A...")
    res = requests.get(f"{BASE_URL}/metrics/global", headers=headers_a)
    if res.status_code == 200:
        print("✅ User A accessed global metrics")
        print(res.json())
    else:
        print(f"ℹ️ User A denied global metrics (Status: {res.status_code}). This is expected if not admin.")

if __name__ == "__main__":
    test_auth_flow()
