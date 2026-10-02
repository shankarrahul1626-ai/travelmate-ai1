import re
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class MessageIn(BaseModel):
    user_id: Optional[str] = None
    message: str


class MessageOut(BaseModel):
    reply: str
    context: Optional[dict] = None


DAYS = {
    "monday": "monday",
    "tuesday": "tuesday",
    "wednesday": "wednesday",
    "thursday": "thursday",
    "friday": "friday",
    "saturday": "saturday",
    "sunday": "sunday",
}


@router.post("/message", response_model=MessageOut)
def handle_message(payload: MessageIn):
    """Simple rule-based travel intent parser for the TravelMate demo app."""
    text = payload.message.lower().strip()
    context = {}

    date_value = None
    date_match = re.search(r"\b(?:next\s+)?(?:tomorrow|monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b", text)
    if date_match:
        matched_date = date_match.group(0).strip()
        date_value = matched_date
        if matched_date == "tomorrow":
            date_value = "tomorrow"
        elif matched_date.startswith("next "):
            date_value = matched_date
        else:
            date_value = matched_date
        text = text[:date_match.start()].strip() + " " + text[date_match.end():].strip()
        text = re.sub(r"\s+", " ", text).strip()

    if date_value:
        context["date"] = date_value

    text_for_route = text
    route_match = re.search(r"\bfrom\s+([a-z]+(?:\s+[a-z]+)*)\s+to\s+([a-z]+(?:\s+[a-z]+)*)\b", text_for_route)
    if route_match:
        source = route_match.group(1).strip()
        destination = route_match.group(2).strip()
        context["source"] = source.title()
        context["destination"] = destination.title()
    else:
        direct_match = re.search(r"\bto\s+([a-z]+(?:\s+[a-z]+)*)\b", text_for_route)
        if direct_match:
            destination = direct_match.group(1).strip()
            context["destination"] = destination.title()

    transport = None
    for candidate in ("bus", "train", "flight"):
        if candidate in text:
            transport = candidate
            break
    if transport:
        context["transport"] = transport

    passenger_match = re.search(r"(?:for\s+|about\s+|take\s+)?(\d+)\s+(?:passenger|passengers)", text)
    if passenger_match:
        context["passengers"] = int(passenger_match.group(1))

    if "source" in context and "destination" in context and "transport" not in context:
        reply = "Sure! Which mode of transport would you prefer?\n- Bus\n- Train\n- Flight"
    elif "transport" in context and "date" in context and "source" in context and "destination" in context:
        reply = "I have the route and date. Do you want me to book it now?"
    elif "transport" in context and "date" in context:
        reply = "How many passengers are travelling?"
    elif "transport" in context:
        reply = "Which date do you want to travel?"
    elif "source" in context and "destination" in context:
        reply = "Great route! Which mode of transport would you prefer?"
    else:
        reply = "Hi, I can help you book tickets. Please tell me your travel like 'I want to go from Bengaluru to Hyderabad tomorrow'."

    return MessageOut(reply=reply, context=context)
