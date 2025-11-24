import requests
import sys

BASE_URL = "http://localhost:8000"
INVITE_CODE = "LQQI0H0SAFNP" # From previous generation
EMAIL = "test_invite@example.com"
PASSWORD = "password123"

def test_registration_no_invite():
    print("Testing registration without invite...")
    try:
        res = requests.post(f"{BASE_URL}/auth/register", json={
            "email": "fail@example.com",
            "password": "password123"
        })
        if res.status_code == 422: # Validation error (missing field)
            print("✅ Failed as expected (missing field)")
        else:
            print(f"❌ Unexpected status: {res.status_code} {res.text}")
    except Exception as e:
        print(f"❌ Error: {e}")

def test_registration_invalid_invite():
    print("Testing registration with invalid invite...")
    res = requests.post(f"{BASE_URL}/auth/register", json={
        "email": "fail2@example.com",
        "password": "password123",
        "invite_code": "INVALID"
    })
    if res.status_code == 400 and "Invalid invite code" in res.text:
        print("✅ Failed as expected (invalid invite)")
    else:
        print(f"❌ Unexpected status: {res.status_code} {res.text}")

def test_registration_valid_invite():
    print(f"Testing registration with valid invite {INVITE_CODE}...")
    res = requests.post(f"{BASE_URL}/auth/register", json={
        "email": EMAIL,
        "password": PASSWORD,
        "invite_code": INVITE_CODE
    })
    if res.status_code == 200:
        print("✅ Registration successful")
        return True
    else:
        print(f"❌ Registration failed: {res.status_code} {res.text}")
        return False

def test_registration_reuse_invite():
    print("Testing registration with used invite...")
    res = requests.post(f"{BASE_URL}/auth/register", json={
        "email": "fail3@example.com",
        "password": "password123",
        "invite_code": INVITE_CODE
    })
    if res.status_code == 400 and "already used" in res.text:
        print("✅ Failed as expected (already used)")
    else:
        print(f"❌ Unexpected status: {res.status_code} {res.text}")

def test_login_and_access():
    print("Testing login...")
    res = requests.post(f"{BASE_URL}/auth/login", data={
        "username": EMAIL,
        "password": PASSWORD
    })
    if res.status_code != 200:
        print(f"❌ Login failed: {res.status_code} {res.text}")
        return

    token = res.json()["access_token"]
    print("✅ Login successful")
    
    print("Testing /auth/me...")
    headers = {"Authorization": f"Bearer {token}"}
    res = requests.get(f"{BASE_URL}/auth/me", headers=headers)
    if res.status_code == 200:
        print(f"✅ /auth/me successful: {res.json()}")
    else:
        print(f"❌ /auth/me failed: {res.status_code} {res.text}")

    print("Testing /chats...")
    res = requests.get(f"{BASE_URL}/chats", headers=headers)
    if res.status_code == 200:
        print("✅ /chats successful")
    else:
        print(f"❌ /chats failed: {res.status_code} {res.text}")

if __name__ == "__main__":
    test_registration_no_invite()
    test_registration_invalid_invite()
    if test_registration_valid_invite():
        test_registration_reuse_invite()
        test_login_and_access()
