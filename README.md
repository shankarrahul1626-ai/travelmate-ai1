# TravelMate AI – Intelligent Ticket Booking Assistant

This repository contains a starter scaffold for TravelMate AI: a chat-driven ticket booking assistant.

Quick start (backend):

1. Create and activate a Python environment.

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r backend/requirements.txt
uvicorn backend.app.main:app --reload
```

Quick start (frontend):

```powershell
cd frontend
npm install
npm run dev
```

Open the frontend in the browser (Vite will show the URL). The simple chat UI posts messages to the backend `/chat/message` endpoint.

What's included:
- FastAPI backend with simple rule-based chatbot, transport search, and in-memory bookings.
- React frontend (Vite) with a minimal chat interface.

Next steps:
- Integrate an LLM (OpenAI, local) for natural language understanding.
- Replace simulated transport data with real APIs.
- Implement seat selection, payment integration, PDF ticket generation, and admin dashboard.

API examples

- Chat (POST):

```bash
curl -s -X POST http://127.0.0.1:8000/chat/message -H "Content-Type: application/json" -d '{"message":"I want to go from Bengaluru to Hyderabad tomorrow"}'
```

- Search transports (GET):

```bash
curl -s "http://127.0.0.1:8000/transport/search?source=Bengaluru&destination=Hyderabad&date=tomorrow&transport=bus"
```

- Create booking (POST):

```bash
curl -s -X POST http://127.0.0.1:8000/booking/create -H "Content-Type: application/json" -d '{"user_id":"demo","transport_id":"bus-1","seats":2}'
```

- Pay booking (POST):

```bash
curl -s -X POST http://127.0.0.1:8000/booking/pay/<booking_id>
```

- Get ticket path (GET):

```bash
curl -s http://127.0.0.1:8000/booking/ticket/<booking_id>
```

- Booking history (GET):

```bash
curl -s http://127.0.0.1:8000/booking/history
```

Developer notes

- Recommended backend run (from repo root):

```powershell
python -m venv .venv
. .venv\Scripts\Activate.ps1
pip install -r backend/requirements.txt
cd backend
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

- Run the smoke test (after server is running):

```powershell
cd backend
python smoke_test.py
```

Frontend quick run:

```powershell
cd frontend
npm install
npm run dev
```

If you'd like, I can run the smoke test now (I need the backend server running). I can also continue implementing the admin UI and JWT-based auth next.
