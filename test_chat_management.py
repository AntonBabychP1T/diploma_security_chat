import requests

BASE_URL = "http://127.0.0.1:8000"

def test_chat_management():
    # 1. Create a chat
    print("Creating chat...")
    res = requests.post(f"{BASE_URL}/chats/", json={"title": "Test Chat"})
    assert res.status_code == 200
    chat = res.json()
    chat_id = chat["id"]
    print(f"Created chat {chat_id}: {chat['title']}")

    # 2. Rename chat
    print("Renaming chat...")
    new_title = "Renamed Test Chat"
    res = requests.patch(f"{BASE_URL}/chats/{chat_id}", json={"title": new_title})
    assert res.status_code == 200
    updated_chat = res.json()
    assert updated_chat["title"] == new_title
    print(f"Renamed chat {chat_id} to: {updated_chat['title']}")

    # 3. Verify rename
    res = requests.get(f"{BASE_URL}/chats/{chat_id}")
    assert res.json()["title"] == new_title

    # 4. Delete chat
    print("Deleting chat...")
    res = requests.delete(f"{BASE_URL}/chats/{chat_id}")
    assert res.status_code == 200
    
    # 5. Verify deletion
    res = requests.get(f"{BASE_URL}/chats/{chat_id}")
    assert res.status_code == 404
    print("Chat deleted successfully")

if __name__ == "__main__":
    test_chat_management()
