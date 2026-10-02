from fastapi import APIRouter
from pydantic import BaseModel
from typing import List
from typing import Optional

router = APIRouter()

CITY_DISTANCE_MAP = {
    ("bengaluru", "hyderabad"): 570,
    ("hyderabad", "bengaluru"): 570,
    ("bengaluru", "chennai"): 350,
    ("chennai", "bengaluru"): 350,
    ("bengaluru", "mysuru"): 150,
    ("mysuru", "bengaluru"): 150,
    ("bengaluru", "mumbai"): 980,
    ("mumbai", "bengaluru"): 980,
    ("bengaluru", "delhi"): 1740,
    ("delhi", "bengaluru"): 1740,
    ("bengaluru", "pune"): 840,
    ("pune", "bengaluru"): 840,
    ("hyderabad", "chennai"): 610,
    ("chennai", "hyderabad"): 610,
    ("hyderabad", "mumbai"): 710,
    ("mumbai", "hyderabad"): 710,
    ("hyderabad", "delhi"): 1225,
    ("delhi", "hyderabad"): 1225,
    ("hyderabad", "pune"): 500,
    ("pune", "hyderabad"): 500,
    ("chennai", "mumbai"): 1330,
    ("mumbai", "chennai"): 1330,
    ("chennai", "delhi"): 1750,
    ("delhi", "chennai"): 1750,
    ("mumbai", "delhi"): 1160,
    ("delhi", "mumbai"): 1160,
    ("mumbai", "pune"): 150,
    ("pune", "mumbai"): 150,
    ("delhi", "jaipur"): 280,
    ("jaipur", "delhi"): 280,
    ("delhi", "ahmedabad"): 760,
    ("ahmedabad", "delhi"): 760,
    ("delhi", "kolkata"): 1440,
    ("kolkata", "delhi"): 1440,
    ("kochi", "bengaluru"): 370,
    ("bengaluru", "kochi"): 370,
    ("kochi", "chennai"): 590,
    ("chennai", "kochi"): 590,
    ("kochi", "mumbai"): 1180,
    ("mumbai", "kochi"): 1180,
    ("coimbatore", "bengaluru"): 220,
    ("bengaluru", "coimbatore"): 220,
    ("coimbatore", "chennai"): 500,
    ("chennai", "coimbatore"): 500,
}


def normalize_city_name(city: str) -> str:
    cleaned = (city or '').strip().lower().replace('.', '').replace('-', ' ')
    aliases = {
        "bangalore": "bengaluru",
        "b'lore": "bengaluru",
        "madras": "chennai",
        "bombay": "mumbai",
        "calcutta": "kolkata",
        "new delhi": "delhi",
        "trivandrum": "thiruvananthapuram",
    }
    return aliases.get(cleaned, cleaned)


def estimate_distance_km(source: str, destination: str) -> int:
    source_key = normalize_city_name(source)
    destination_key = normalize_city_name(destination)
    if not source_key or not destination_key:
        return 500
    if source_key == destination_key:
        return 0

    direct_key = (source_key, destination_key)
    reverse_key = (destination_key, source_key)
    if direct_key in CITY_DISTANCE_MAP:
        return CITY_DISTANCE_MAP[direct_key]
    if reverse_key in CITY_DISTANCE_MAP:
        return CITY_DISTANCE_MAP[reverse_key]
    return 500


def parse_date_value(date_value: str):
    if not date_value:
        return None
    value = str(date_value).strip().lower()
    today = __import__('datetime').datetime.utcnow().date()

    if value in {'tomorrow'}:
        return today + __import__('datetime').timedelta(days=1)
    if value in {'next monday', 'next tuesday', 'next wednesday', 'next thursday', 'next friday', 'next saturday', 'next sunday'}:
        return today + __import__('datetime').timedelta(days=7)

    try:
        return __import__('datetime').datetime.fromisoformat(value).date()
    except ValueError:
        try:
            return __import__('datetime').datetime.strptime(value, '%d-%m-%Y').date()
        except ValueError:
            return None


def calculate_trip_fare(
    base_fare: float,
    transport_type: str,
    depart_time: str,
    travel_date: str,
    distance_km: int,
    seat_class: str = "economy",
    discount_code: Optional[str] = None,
    loyalty_points: int = 0,
) -> float:
    transport_type = (transport_type or 'bus').lower()
    route_factor = 0.75 + (distance_km / 2200)
    transport_factor = {
        'bus': 1.0,
        'train': 0.82,
        'flight': 1.55,
    }.get(transport_type, 1.0)

    departure_minutes = 0
    try:
        hours, minutes = str(depart_time or '00:00').split(':')[:2]
        departure_minutes = int(hours) * 60 + int(minutes)
    except (ValueError, TypeError):
        departure_minutes = 0

    peak_multiplier = 1.0
    if 6 * 60 <= departure_minutes <= 9 * 60 or 17 * 60 <= departure_minutes <= 20 * 60:
        peak_multiplier = 1.12
    elif departure_minutes >= 21 * 60:
        peak_multiplier = 1.08

    booking_date = parse_date_value(travel_date)
    weekend_multiplier = 1.0
    if booking_date is not None and booking_date.weekday() >= 5:
        weekend_multiplier = 1.12 if transport_type != 'flight' else 1.08

    early_booking_multiplier = 1.0
    if booking_date is not None:
        today = __import__('datetime').datetime.utcnow().date()
        days_ahead = (booking_date - today).days
        if days_ahead >= 14:
            early_booking_multiplier = 0.9
        elif days_ahead >= 7:
            early_booking_multiplier = 0.95

    seat_class_factor = {
        'economy': 1.0,
        'standard': 1.0,
        'premium': 1.22,
        'business': 1.48,
        'first': 1.8,
    }.get((seat_class or 'economy').lower(), 1.0)

    discount_rate = 0.0
    code = (discount_code or '').strip().upper()
    if code in {'SAVE5', 'WELCOME5'}:
        discount_rate += 0.05
    elif code in {'SAVE10', 'LOYAL10', 'TRAVEL10'}:
        discount_rate += 0.10
    elif code in {'SAVE15', 'VIP15', 'TRAVEL15'}:
        discount_rate += 0.15
    elif code in {'SAVE20', 'PLUS20'}:
        discount_rate += 0.20

    loyalty_rate = min(float(loyalty_points or 0) / 1000.0, 0.20)
    discount_rate = min(discount_rate + loyalty_rate, 0.55)
    discount_multiplier = 1.0 - discount_rate

    total = (
        float(base_fare)
        * route_factor
        * transport_factor
        * peak_multiplier
        * early_booking_multiplier
        * weekend_multiplier
        * seat_class_factor
        * discount_multiplier
    )
    return round(total, 2)


class TransportOption(BaseModel):
    id: str
    provider: str
    depart_time: str
    arrive_time: str
    fare: float
    seats_available: int
    transport: str


# Realistic travel inventory across bus, train and flight categories
DATA = [
    TransportOption(id="bus-1", provider="SRS Travels", depart_time="05:30", arrive_time="09:45", fare=420.0, seats_available=16, transport="bus"),
    TransportOption(id="bus-2", provider="KSRTC", depart_time="06:15", arrive_time="10:40", fare=390.0, seats_available=12, transport="bus"),
    TransportOption(id="bus-3", provider="VRL Travels", depart_time="07:10", arrive_time="11:20", fare=450.0, seats_available=11, transport="bus"),
    TransportOption(id="bus-4", provider="Orange Travels", depart_time="08:00", arrive_time="12:30", fare=430.0, seats_available=18, transport="bus"),
    TransportOption(id="bus-5", provider="Sugama Travels", depart_time="08:45", arrive_time="13:10", fare=410.0, seats_available=20, transport="bus"),
    TransportOption(id="bus-6", provider="Bharath Travels", depart_time="09:30", arrive_time="14:05", fare=470.0, seats_available=8, transport="bus"),
    TransportOption(id="bus-7", provider="Morning Star Travels", depart_time="10:15", arrive_time="15:00", fare=495.0, seats_available=13, transport="bus"),
    TransportOption(id="bus-8", provider="Kallada Travels", depart_time="11:00", arrive_time="15:45", fare=440.0, seats_available=15, transport="bus"),
    TransportOption(id="bus-9", provider="Jabbar Travels", depart_time="12:15", arrive_time="16:50", fare=460.0, seats_available=10, transport="bus"),
    TransportOption(id="bus-10", provider="National Travels", depart_time="13:20", arrive_time="18:10", fare=520.0, seats_available=7, transport="bus"),
    TransportOption(id="bus-11", provider="GreenLine Travels", depart_time="14:05", arrive_time="18:35", fare=480.0, seats_available=9, transport="bus"),
    TransportOption(id="bus-12", provider="Sree Kaleshwari Travels", depart_time="15:40", arrive_time="20:15", fare=510.0, seats_available=6, transport="bus"),
    TransportOption(id="bus-13", provider="Shakti Travels", depart_time="06:45", arrive_time="11:00", fare=435.0, seats_available=17, transport="bus"),
    TransportOption(id="bus-14", provider="Lakshmi Travels", depart_time="07:55", arrive_time="12:20", fare=425.0, seats_available=19, transport="bus"),
    TransportOption(id="bus-15", provider="Vijayanand Travels", depart_time="09:05", arrive_time="13:55", fare=470.0, seats_available=12, transport="bus"),
    TransportOption(id="bus-16", provider="Kaveri Travels", depart_time="10:40", arrive_time="15:35", fare=455.0, seats_available=14, transport="bus"),
    TransportOption(id="bus-17", provider="Reliance Travels", depart_time="12:50", arrive_time="17:40", fare=490.0, seats_available=11, transport="bus"),
    TransportOption(id="bus-18", provider="Mahalaxmi Travels", depart_time="17:10", arrive_time="21:50", fare=530.0, seats_available=8, transport="bus"),
    TransportOption(id="bus-19", provider="Naveen Travels", depart_time="18:25", arrive_time="22:55", fare=500.0, seats_available=9, transport="bus"),
    TransportOption(id="bus-20", provider="KPN Travels", depart_time="19:55", arrive_time="00:20", fare=540.0, seats_available=5, transport="bus"),
    TransportOption(id="train-1", provider="Shatabdi Express", depart_time="06:05", arrive_time="09:25", fare=260.0, seats_available=96, transport="train"),
    TransportOption(id="train-2", provider="Intercity Express", depart_time="07:15", arrive_time="10:50", fare=275.0, seats_available=88, transport="train"),
    TransportOption(id="train-3", provider="Rajdhani Express", depart_time="08:30", arrive_time="12:00", fare=290.0, seats_available=82, transport="train"),
    TransportOption(id="train-4", provider="Vande Bharat", depart_time="09:45", arrive_time="13:05", fare=330.0, seats_available=76, transport="train"),
    TransportOption(id="train-5", provider="Express Shuttle", depart_time="11:10", arrive_time="15:20", fare=300.0, seats_available=92, transport="train"),
    TransportOption(id="train-6", provider="Duronto Express", depart_time="12:40", arrive_time="16:30", fare=315.0, seats_available=70, transport="train"),
    TransportOption(id="train-7", provider="Garib Rath", depart_time="14:25", arrive_time="18:45", fare=280.0, seats_available=68, transport="train"),
    TransportOption(id="train-8", provider="Jan Shatabdi", depart_time="16:50", arrive_time="20:35", fare=320.0, seats_available=58, transport="train"),
    TransportOption(id="flight-1", provider="IndiGo", depart_time="05:50", arrive_time="07:10", fare=3200.0, seats_available=6, transport="flight"),
    TransportOption(id="flight-2", provider="Air India", depart_time="07:30", arrive_time="08:50", fare=3650.0, seats_available=4, transport="flight"),
    TransportOption(id="flight-3", provider="SpiceJet", depart_time="09:10", arrive_time="10:35", fare=2980.0, seats_available=8, transport="flight"),
    TransportOption(id="flight-4", provider="GoAir", depart_time="10:55", arrive_time="12:15", fare=3120.0, seats_available=5, transport="flight"),
    TransportOption(id="flight-5", provider="Akasa Air", depart_time="12:40", arrive_time="14:00", fare=3380.0, seats_available=7, transport="flight"),
    TransportOption(id="flight-6", provider="Vistara", depart_time="14:20", arrive_time="15:45", fare=3490.0, seats_available=9, transport="flight"),
    TransportOption(id="flight-7", provider="Qatar Airways", depart_time="16:10", arrive_time="17:30", fare=4180.0, seats_available=3, transport="flight"),
    TransportOption(id="flight-8", provider="Emirates", depart_time="18:05", arrive_time="19:30", fare=4320.0, seats_available=2, transport="flight"),
    TransportOption(id="flight-9", provider="Jet Airways", depart_time="19:35", arrive_time="20:55", fare=4050.0, seats_available=4, transport="flight"),
    TransportOption(id="flight-10", provider="Lufthansa", depart_time="21:10", arrive_time="22:35", fare=4750.0, seats_available=3, transport="flight"),
]


@router.get("/search", response_model=List[TransportOption])
def search(source: str, destination: str, date: str, transport: str = "bus"):
    base_results = [t for t in DATA if t.transport == transport.lower()]
    distance_km = estimate_distance_km(source, destination)

    results = []
    for option in base_results:
        adjusted_fare = calculate_trip_fare(
            option.fare,
            option.transport,
            option.depart_time,
            date,
            distance_km,
        )
        results.append(
            TransportOption(
                id=option.id,
                provider=option.provider,
                depart_time=option.depart_time,
                arrive_time=option.arrive_time,
                fare=adjusted_fare,
                seats_available=option.seats_available,
                transport=option.transport,
            )
        )

    results.sort(key=lambda t: t.depart_time)
    return results


@router.post("/admin/add")
def admin_add(option: TransportOption):
    DATA.append(option)
    return {"status": "added", "id": option.id}


@router.get("/admin/list")
def admin_list(transport: Optional[str] = None):
    if transport:
        return [t for t in DATA if t.transport == transport]
    return DATA
