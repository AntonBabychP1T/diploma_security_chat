import requests

BASE_URL = "http://localhost:8000"
EMAIL = "test_invite@example.com"
PASSWORD = "password123"

def debug_chats():
    print("Logging in...")
    res = requests.post(f"{BASE_URL}/auth/login", data={
        "username": EMAIL,
        "password": PASSWORD
    })
    if res.status_code != 200:
        print(f"❌ Login failed: {res.status_code} {res.text}")
        return

    token = res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    print("Calling /chats...")
    res = requests.get(f"{BASE_URL}/chats", headers=headers)
    print(f"Status: {res.status_code}")
    print(f"Response: {res.text}")

if __name__ == "__main__":
    debug_chats()
