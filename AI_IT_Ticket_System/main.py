
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from typing import Optional
from pathlib import Path
from contextlib import asynccontextmanager
import sqlite3
import csv

from ai.ticket_ai import (
    analyze_ticket,
    seed_demo_tickets,
    search_similar_tickets,
)

ROOT = Path(__file__).resolve().parent
DB_PATH = ROOT / "data" / "tickets.db"
CSV_PATH = ROOT / "data" / "tickets.csv"


# Request model
class TicketCreate(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    description: str = Field(min_length=5, max_length=5000)
    requester: str = Field(default="Employee", max_length=120)


# Database connection
def get_connection():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# Initialize database
def init_db():
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                requester TEXT NOT NULL,
                category TEXT NOT NULL,
                priority TEXT NOT NULL,
                assigned_team TEXT NOT NULL,
                suggested_resolution TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'Open',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)

        count = conn.execute(
            "SELECT COUNT(*) FROM tickets"
        ).fetchone()[0]

        if count == 0:
            seed_demo_tickets(conn)


# Create FastAPI application
@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="AI IT Ticket Management System",
    version="1.0.0",
    lifespan=lifespan,
)

# Serve frontend files
app.mount(
    "/static",
    StaticFiles(directory=str(ROOT / "static")),
    name="static",
)


# Home page
@app.get("/")
def home():
    return FileResponse(ROOT / "static" / "index.html")


# Browser favicon
@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    return Response(status_code=204)


# Health check
@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "service": "AI IT Ticket Management System",
    }


# Create ticket
@app.post("/api/tickets")
def create_ticket(ticket: TicketCreate):
    analysis = analyze_ticket(
        ticket.title,
        ticket.description,
    )

    with get_connection() as conn:
        cursor = conn.execute("""
            INSERT INTO tickets (
                title, description, requester,
                category, priority, assigned_team,
                suggested_resolution, status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, 'Open')
        """, (
            ticket.title,
            ticket.description,
            ticket.requester,
            analysis["category"],
            analysis["priority"],
            analysis["assigned_team"],
            analysis["suggested_resolution"],
        ))

        ticket_id = cursor.lastrowid

        row = conn.execute(
            "SELECT * FROM tickets WHERE id = ?",
            (ticket_id,),
        ).fetchone()

    result = dict(row)

    result["similar_tickets"] = search_similar_tickets(
        ticket.title,
        ticket.description,
        exclude_id=ticket_id,
    )

    result["ai_method"] = analysis.get(
        "method", "Mock AI"
    )

    return result


# List tickets
@app.get("/api/tickets")
def list_tickets(
    status: Optional[str] = None,
    limit: int = 100,
):
    limit = max(1, min(limit, 500))

    with get_connection() as conn:
        if status:
            rows = conn.execute("""
                SELECT * FROM tickets
                WHERE status = ?
                ORDER BY id DESC LIMIT ?
            """, (status, limit)).fetchall()
        else:
            rows = conn.execute("""
                SELECT * FROM tickets
                ORDER BY id DESC LIMIT ?
            """, (limit,)).fetchall()

    return [dict(row) for row in rows]


# Get one ticket
@app.get("/api/tickets/{ticket_id}")
def get_ticket(ticket_id: int):
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM tickets WHERE id = ?",
            (ticket_id,),
        ).fetchone()

    if not row:
        raise HTTPException(
            status_code=404,
            detail="Ticket not found",
        )

    result = dict(row)

    result["similar_tickets"] = search_similar_tickets(
        row["title"],
        row["description"],
        exclude_id=ticket_id,
    )

    return result


# Update ticket status
@app.patch("/api/tickets/{ticket_id}/status")
def update_status(ticket_id: int, status: str):
    allowed = {
        "Open",
        "In Progress",
        "Resolved",
        "Escalated",
    }

    if status not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Status must be one of {sorted(allowed)}",
        )

    with get_connection() as conn:
        cursor = conn.execute(
            "UPDATE tickets SET status = ? WHERE id = ?",
            (status, ticket_id),
        )

        if cursor.rowcount == 0:
            raise HTTPException(
                status_code=404,
                detail="Ticket not found",
            )

        row = conn.execute(
            "SELECT * FROM tickets WHERE id = ?",
            (ticket_id,),
        ).fetchone()

    return dict(row)


# Dashboard metrics
@app.get("/api/metrics")
def metrics():
    with get_connection() as conn:
        total = conn.execute(
            "SELECT COUNT(*) FROM tickets"
        ).fetchone()[0]

        statuses = {
            row["status"]: row["n"]
            for row in conn.execute("""
                SELECT status, COUNT(*) n
                FROM tickets GROUP BY status
            """)
        }

        categories = [
            {"category": row["category"], "count": row["n"]}
            for row in conn.execute("""
                SELECT category, COUNT(*) n
                FROM tickets
                GROUP BY category
                ORDER BY n DESC
            """)
        ]

        priorities = [
            {"priority": row["priority"], "count": row["n"]}
            for row in conn.execute("""
                SELECT priority, COUNT(*) n
                FROM tickets
                GROUP BY priority
                ORDER BY n DESC
            """)
        ]

    return {
        "total": total,
        "statuses": statuses,
        "categories": categories,
        "priorities": priorities,
    }


# Demo CSV data
@app.get("/api/demo-data")
def demo_data():
    if not CSV_PATH.exists():
        return {"message": "CSV dataset not found"}

    with open(
        CSV_PATH,
        newline="",
        encoding="utf-8",
    ) as file:
        return list(csv.DictReader(file))
