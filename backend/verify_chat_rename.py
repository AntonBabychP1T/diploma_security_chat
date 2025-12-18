import requests
import sys
import time

BASE_URL = "http://localhost:8000"
EMAIL = "test_invite@example.com"
PASSWORD = "password123"

def get_token():
    print("Logging in...")
    res = requests.post(f"{BASE_URL}/auth/login", data={
        "username": EMAIL,
        "password": PASSWORD
    })
    if res.status_code != 200:
        print(f"Login failed: {res.text}")
        sys.exit(1)
    return res.json()["access_token"]

def verify_chat_rename():
    token = get_token()
    headers = {"Authorization": f"Bearer {token}"}
    
    # 1. Create Chat
    print("Creating new chat...")
    res = requests.post(f"{BASE_URL}/chats", headers=headers, json={"title": "New Chat"})
    if res.status_code != 200:
        print(f"Failed to create chat: {res.text}")
        return
        
    chat = res.json()
    chat_id = chat["id"]
    print(f"Chat created: ID={chat_id}, Title='{chat['title']}'")
    
    if chat["title"] != "New Chat":
        print("Warning: Initial title is not 'New Chat'")

    # 2. Send Message
    message_content = "To be or not to be, that is the question."
    print(f"Sending message: '{message_content}'...")
    res = requests.post(f"{BASE_URL}/chats/{chat_id}/messages", headers=headers, json={
        "message": message_content
    })
    
    if res.status_code != 200:
        print(f"Failed to send message: {res.text}")
        return
        
    print("Message sent.")
    
    # 3. Check Title
    # Give it a moment? commit is awaited so it should be immediate
    print("Checking chat title...")
    res = requests.get(f"{BASE_URL}/chats/{chat_id}", headers=headers)
    updated_chat = res.json()
    new_title = updated_chat["title"]
    print(f"New Title: '{new_title}'")
    
    expected_start = "To be or not to be"
    if new_title.startswith(expected_start) or new_title != "New Chat":
        print("✅ SUCCESS: Chat renamed successfully")
    else:
        print("❌ FAILURE: Chat title did not change")

if __name__ == "__main__":
    verify_chat_rename()
