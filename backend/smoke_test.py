import requests

BASE = "http://127.0.0.1:8000"

def test_root():
    r = requests.get(BASE + "/")
    print('root', r.status_code, r.json())

def test_chat():
    r = requests.post(BASE + "/chat/message", json={"message": "I want to travel from Bengaluru to Hyderabad tomorrow"})
    print('chat', r.status_code, r.json())

def test_search():
    r = requests.get(BASE + "/transport/search", params={"source":"Bengaluru","destination":"Hyderabad","date":"tomorrow","transport":"bus"})
    print('search', r.status_code, r.json())

if __name__ == '__main__':
    test_root()
    test_chat()
    test_search()
