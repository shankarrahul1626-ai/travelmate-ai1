import os
import sqlite3
import uuid
from datetime import datetime
from typing import Optional

import qrcode
from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

# fpdf may not be installed in every environment used to run the server; import lazily
try:
    from fpdf import FPDF
except Exception:
    FPDF = None

router = APIRouter()

BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DATABASE_PATH = os.path.join(BACKEND_DIR, "travelmate.db")


class BookingRequest(BaseModel):
    user_id: Optional[str]
    transport_id: str
    seats: int
    source: Optional[str] = None
    destination: Optional[str] = None
    date: Optional[str] = None
    provider: Optional[str] = None
    amount: Optional[float] = None
    transport_type: Optional[str] = None
    seat_class: Optional[str] = "economy"
    discount_code: Optional[str] = None
    loyalty_points: int = 0


class BookingResponse(BaseModel):
    booking_id: str
    status: str
    transport_id: str


def get_db_connection():
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_db():
    connection = get_db_connection()
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS bookings (
            booking_id TEXT PRIMARY KEY,
            user_id TEXT,
            transport_id TEXT NOT NULL,
            seats INTEGER NOT NULL,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            source TEXT,
            destination TEXT,
            date TEXT,
            amount REAL DEFAULT 0,
            provider TEXT,
            transport_type TEXT,
            seat_class TEXT,
            discount_code TEXT,
            loyalty_points INTEGER DEFAULT 0
        )
        """
    )

    existing_columns = [row[1] for row in connection.execute("PRAGMA table_info(bookings)").fetchall()]
    required_columns = {
        "source": "TEXT",
        "destination": "TEXT",
        "date": "TEXT",
        "amount": "REAL DEFAULT 0",
        "provider": "TEXT",
        "transport_type": "TEXT",
        "seat_class": "TEXT",
        "discount_code": "TEXT",
        "loyalty_points": "INTEGER DEFAULT 0",
    }
    for column_name, column_type in required_columns.items():
        if column_name not in existing_columns:
            connection.execute(f"ALTER TABLE bookings ADD COLUMN {column_name} {column_type}")

    connection.commit()
    connection.close()


init_db()


def row_to_booking(row):
    return {
        "booking_id": row["booking_id"],
        "user_id": row["user_id"],
        "transport_id": row["transport_id"],
        "seats": row["seats"],
        "status": row["status"],
        "created_at": row["created_at"],
        "source": row["source"],
        "destination": row["destination"],
        "date": row["date"],
        "amount": row["amount"],
        "provider": row["provider"],
        "transport_type": row["transport_type"],
        "seat_class": row["seat_class"],
        "discount_code": row["discount_code"],
        "loyalty_points": row["loyalty_points"],
    }


def get_booking(booking_id: str):
    connection = get_db_connection()
    row = connection.execute(
        "SELECT * FROM bookings WHERE booking_id = ?",
        (booking_id,),
    ).fetchone()
    connection.close()
    if row is None:
        return None
    return row_to_booking(row)


def create_booking_record(
    user_id: Optional[str],
    transport_id: str,
    seats: int,
    source: Optional[str] = None,
    destination: Optional[str] = None,
    date: Optional[str] = None,
    amount: Optional[float] = None,
    provider: Optional[str] = None,
    transport_type: Optional[str] = None,
    seat_class: Optional[str] = "economy",
    discount_code: Optional[str] = None,
    loyalty_points: int = 0,
):
    if seats <= 0:
        raise HTTPException(status_code=400, detail="Seats must be greater than zero")

    booking_id = str(uuid.uuid4())
    created_at = datetime.utcnow().isoformat()
    booking = {
        "booking_id": booking_id,
        "user_id": user_id,
        "transport_id": transport_id,
        "seats": seats,
        "status": "pending",
        "created_at": created_at,
        "source": source,
        "destination": destination,
        "date": date,
        "amount": float(amount or 0),
        "provider": provider,
        "transport_type": transport_type,
        "seat_class": seat_class or "economy",
        "discount_code": discount_code,
        "loyalty_points": int(loyalty_points or 0),
    }

    connection = get_db_connection()
    connection.execute(
        """
        INSERT INTO bookings (
            booking_id, user_id, transport_id, seats, status, created_at,
            source, destination, date, amount, provider, transport_type,
            seat_class, discount_code, loyalty_points
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            booking_id,
            user_id,
            transport_id,
            seats,
            booking["status"],
            created_at,
            booking["source"],
            booking["destination"],
            booking["date"],
            booking["amount"],
            booking["provider"],
            booking["transport_type"],
            booking["seat_class"],
            booking["discount_code"],
            booking["loyalty_points"],
        ),
    )
    connection.commit()
    connection.close()
    return booking


def update_booking_status(booking_id: str, status: str):
    connection = get_db_connection()
    cursor = connection.execute(
        "UPDATE bookings SET status = ? WHERE booking_id = ?",
        (status, booking_id),
    )
    connection.commit()
    connection.close()
    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="Booking not found")
    return get_booking(booking_id)


def bookings_for_user(user_id: Optional[str] = None):
    connection = get_db_connection()
    if user_id:
        rows = connection.execute(
            "SELECT * FROM bookings WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,),
        ).fetchall()
    else:
        rows = connection.execute("SELECT * FROM bookings ORDER BY created_at DESC").fetchall()
    connection.close()
    return [row_to_booking(row) for row in rows]


def clear_all_bookings():
    connection = get_db_connection()
    connection.execute("DELETE FROM bookings")
    connection.commit()
    connection.close()
    return {"status": "cleared"}


@router.post("/create", response_model=BookingResponse)
def create_booking(req: BookingRequest):
    booking = create_booking_record(
        req.user_id,
        req.transport_id,
        req.seats,
        source=req.source,
        destination=req.destination,
        date=req.date,
        amount=req.amount,
        provider=req.provider,
        transport_type=req.transport_type,
        seat_class=req.seat_class,
        discount_code=req.discount_code,
        loyalty_points=req.loyalty_points,
    )
    return BookingResponse(
        booking_id=booking["booking_id"],
        status=booking["status"],
        transport_id=booking["transport_id"],
    )


@router.post("/confirm/{booking_id}")
def confirm_booking(booking_id: str):
    booking = get_booking(booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    updated = update_booking_status(booking_id, "confirmed")
    return {"status": updated["status"], "booking_id": booking_id}


@router.post("/pay/{booking_id}")
def pay_booking(booking_id: str, background_tasks: BackgroundTasks):
    booking = get_booking(booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    updated = update_booking_status(booking_id, "paid")
    background_tasks.add_task(generate_ticket_pdf, updated)
    return {"status": updated["status"], "booking_id": booking_id}


def generate_qr_code_png(booking_id: str, payload: Optional[str] = None):
    out_dir = os.path.join(BACKEND_DIR, "tickets")
    os.makedirs(out_dir, exist_ok=True)
    token = payload or f"TravelMate:{booking_id}"
    qr = qrcode.QRCode(version=1, box_size=8, border=2)
    qr.add_data(token)
    qr.make(fit=True)
    image = qr.make_image(fill_color="black", back_color="white")
    path = os.path.join(out_dir, f"qr_{booking_id}.png")
    image.save(path)
    return path


def generate_ticket_pdf(booking: dict):
    out_dir = os.path.join(BACKEND_DIR, "tickets")
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, f"ticket_{booking['booking_id']}.pdf")
    qr_path = generate_qr_code_png(booking['booking_id'], f"BOOKING:{booking['booking_id']}|{booking.get('source') or 'N/A'}->{booking.get('destination') or 'N/A'}")
    if FPDF is not None:
        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()

        pdf.set_fill_color(15, 23, 42)
        pdf.rect(0, 0, 210, 24, 'F')
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("Arial", "B", 16)
        pdf.text(14, 15, "TravelMate AI - Boarding Pass")

        pdf.set_text_color(15, 23, 42)
        pdf.set_font("Arial", "B", 11)
        pdf.set_xy(14, 34)
        pdf.cell(0, 8, txt=f"Booking ID: {booking['booking_id']}", ln=True)

        pdf.set_font("Arial", "", 10)
        pdf.cell(0, 8, txt=f"Provider: {booking.get('provider') or booking.get('transport_id')}", ln=True)
        pdf.cell(0, 8, txt=f"Route: {booking.get('source') or 'N/A'} -> {booking.get('destination') or 'N/A'}", ln=True)
        pdf.cell(0, 8, txt=f"Date: {booking.get('date') or 'N/A'}", ln=True)
        pdf.cell(0, 8, txt=f"Seats: {booking.get('seats') or 0}", ln=True)

        if os.path.exists(qr_path):
            pdf.image(qr_path, x=150, y=34, w=42, h=42)

        pdf.set_draw_color(148, 163, 184)
        pdf.line(14, 112, 196, 112)

        pdf.set_font("Arial", "B", 11)
        pdf.text(14, 122, "Passenger")
        pdf.set_font("Arial", "", 10)
        pdf.text(14, 130, booking.get('user_id') or 'Guest Traveller')

        pdf.set_font("Arial", "B", 11)
        pdf.text(70, 122, "Status")
        pdf.set_font("Arial", "", 10)
        pdf.text(70, 130, (booking.get('status') or 'pending').upper())

        pdf.set_font("Arial", "B", 11)
        pdf.text(126, 122, "Amount")
        pdf.set_font("Arial", "", 10)
        pdf.text(126, 130, f"Rs {float(booking.get('amount') or 0):,.2f}")

        pdf.set_font("Arial", "B", 11)
        pdf.text(14, 150, "Invoice Summary")
        pdf.set_font("Arial", "", 10)
        amount = float(booking.get('amount') or 0)
        service_fee = round(amount * 0.04, 2)
        tax_amount = round(amount * 0.07, 2)
        total_paid = round(amount + service_fee + tax_amount, 2)
        pdf.text(14, 160, f"Ticket fare: Rs {amount:,.2f}")
        pdf.text(14, 168, f"Service fee: Rs {service_fee:,.2f}")
        pdf.text(14, 176, f"Taxes: Rs {tax_amount:,.2f}")
        pdf.text(14, 184, f"Seat class: {booking.get('seat_class') or 'economy'}")
        pdf.text(14, 192, f"Discount: {booking.get('discount_code') or 'N/A'}")
        pdf.text(14, 200, f"Total paid: Rs {total_paid:,.2f}")

        pdf.output(path)
    else:
        with open(path, 'w', encoding='utf-8') as f:
            f.write('TravelMate AI - Boarding Pass\n')
            f.write(f"Booking ID: {booking['booking_id']}\n")
            f.write(f"Provider: {booking.get('provider') or booking.get('transport_id')}\n")
            f.write(f"Route: {booking.get('source') or 'N/A'} → {booking.get('destination') or 'N/A'}\n")
            f.write(f"Seats: {booking.get('seats') or 0}\n")
            f.write(f"Amount: Rs {float(booking.get('amount') or 0):,.2f}\n")
    return path


@router.get("/ticket/{booking_id}")
def get_ticket(booking_id: str):
    path = os.path.join(BACKEND_DIR, "tickets", f"ticket_{booking_id}.pdf")
    if not os.path.exists(path):
        booking = get_booking(booking_id)
        if booking is None:
            raise HTTPException(status_code=404, detail="Ticket not found")
        path = generate_ticket_pdf(booking)
    return FileResponse(path, media_type="application/pdf", filename=f"ticket_{booking_id}.pdf")


@router.get("/ticket-qr/{booking_id}")
def get_ticket_qr(booking_id: str):
    qr_path = os.path.join(BACKEND_DIR, "tickets", f"qr_{booking_id}.png")
    if not os.path.exists(qr_path):
        booking = get_booking(booking_id)
        if booking is None:
            raise HTTPException(status_code=404, detail="Ticket QR not found")
        qr_path = generate_qr_code_png(booking_id, f"BOOKING:{booking_id}|{booking.get('source') or 'N/A'}->{booking.get('destination') or 'N/A'}")
    return FileResponse(qr_path, media_type="image/png", filename=f"qr_{booking_id}.png")


@router.post("/cancel/{booking_id}")
def cancel_booking(booking_id: str):
    booking = get_booking(booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    updated = update_booking_status(booking_id, "cancelled")
    return {"status": updated["status"], "booking_id": booking_id}


@router.get("/user/{user_id}")
def user_bookings(user_id: str):
    return bookings_for_user(user_id)


@router.get("/history")
def booking_history(user_id: Optional[str] = None):
    return bookings_for_user(user_id)


@router.delete("/history")
def clear_booking_history():
    return clear_all_bookings()
