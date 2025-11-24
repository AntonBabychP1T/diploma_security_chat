import requests
import sys

BASE_URL = "http://localhost:8000"
EMAIL = "test_invite@example.com"
PASSWORD = "password123"

def reproduce():
    print("Logging in...")
    try:
        res = requests.post(f"{BASE_URL}/auth/login", data={
            "username": EMAIL,
            "password": PASSWORD
        })
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to server. Is it running?")
        return

    if res.status_code != 200:
        print(f"❌ Login failed: {res.status_code} {res.text}")
        return

    token = res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    print("\nTesting POST /chats/ (with slash)...")
    res = requests.post(f"{BASE_URL}/chats/", json={"title": "Test Chat"}, headers=headers)
    print(f"Status: {res.status_code}")
    try:
        print(f"Response: {res.json()}")
    except:
        print(f"Response: {res.text}")

    print("\nTesting POST /chats (without slash)...")
    res = requests.post(f"{BASE_URL}/chats", json={"title": "Test Chat No Slash"}, headers=headers)
    print(f"Status: {res.status_code}")
    # If it's a redirect, requests follows it by default, so we see final status
    print(f"History: {[r.status_code for r in res.history]}")
    print(f"Response: {res.text}")

if __name__ == "__main__":
    reproduce()
