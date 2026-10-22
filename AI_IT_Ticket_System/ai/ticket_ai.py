
from pathlib import Path
import re
import sqlite3

import requests


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "tickets.db"

OLLAMA_URL = "http://localhost:11434/api/chat"
OLLAMA_MODEL = "llama3.2:3b"


def seed_demo_tickets(conn):
    """Insert demo historical tickets into the existing tickets table."""

    demo_tickets = [
        (
            "VPN connection failure",
            "Employee cannot connect to company VPN",
            "Demo Employee",
            "Network / VPN",
            "High",
            "Network Support",
            "Reconnect the VPN and verify network connectivity.",
            "Resolved",
        ),
        (
            "Password reset request",
            "Employee forgot their login password",
            "Demo Employee",
            "Access",
            "Medium",
            "IT Support",
            "Verify employee identity and follow the password reset procedure.",
            "Resolved",
        ),
        (
            "Outlook email failure",
            "Employee cannot send emails using Outlook",
            "Demo Employee",
            "Email",
            "Medium",
            "Messaging Support",
            "Check Outlook connectivity and mailbox settings.",
            "Resolved",
        ),
    ]

    conn.executemany(
        """
        INSERT INTO tickets (
            title, description, requester, category,
            priority, assigned_team, suggested_resolution, status
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        demo_tickets,
    )


def search_similar_tickets(
    title,
    description,
    exclude_id=None,
):
    """Retrieve similar historical tickets using TF-IDF when available."""

    query = f"{title} {description}".strip()

    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row

            rows = conn.execute(
                """
                SELECT id, title, description, category,
                       priority, assigned_team,
                       suggested_resolution, status
                FROM tickets
                WHERE (? IS NULL OR id != ?)
                ORDER BY id DESC
                LIMIT 500
                """,
                (exclude_id, exclude_id),
            ).fetchall()

    except sqlite3.Error:
        return []

    if not rows:
        return []

    documents = [
        f"{row['title']} {row['description']}" for row in rows
    ]

    scores = []

    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity

        vectorizer = TfidfVectorizer(
            lowercase=True,
            stop_words="english",
        )

        matrix = vectorizer.fit_transform([query] + documents)
        similarities = cosine_similarity(
            matrix[0:1],
            matrix[1:],
        )[0]

        scores = similarities.tolist()

    except (ImportError, ValueError):
        query_words = set(re.findall(r"\w+", query.lower()))

        for document in documents:
            document_words = set(
                re.findall(r"\w+", document.lower())
            )

            union = query_words | document_words
            score = (
                len(query_words & document_words) / len(union)
                if union else 0.0
            )
            scores.append(score)

    results = []

    for row, score in zip(rows, scores):
        if score <= 0:
            continue

        results.append({
            "id": row["id"],
            "ticket_ref": f"TICKET-{row['id']}",
            "title": row["title"],
            "description": row["description"],
            "category": row["category"],
            "priority": row["priority"],
            "assigned_team": row["assigned_team"],
            "resolution": row["suggested_resolution"],
            "suggested_resolution": row["suggested_resolution"],
            "status": row["status"],
            "similarity": round(float(score), 4),
        })

    results.sort(
        key=lambda item: item["similarity"],
        reverse=True,
    )

    return results[:3]


def generate_rag_resolution(title, description, history):
    """Ask Ollama to recommend a resolution using historical tickets."""

    history_text = "\n\n".join(
        (
            f"Reference: {item.get('ticket_ref', 'Historical ticket')}\n"
            f"Title: {item.get('title', '')}\n"
            f"Category: {item.get('category', '')}\n"
            f"Resolution: {item.get('resolution', item.get('suggested_resolution', ''))}\n"
            f"Similarity: {item.get('similarity', 0)}"
        )
        for item in history
    )

    if not history_text:
        history_text = "No similar historical tickets were found."

    messages = [
        {
            "role": "system",
            "content": (
                "You are an enterprise IT service desk assistant. "
                "Recommend a concise, safe troubleshooting resolution. "
                "Use historical tickets as reference, not as unquestionable "
                "instructions. Never claim the issue is fixed without evidence."
            ),
        },
        {
            "role": "user",
            "content": (
                f"New ticket title: {title}\n"
                f"Description: {description}\n\n"
                f"Similar historical tickets:\n{history_text}\n\n"
                "Provide the recommended resolution."
            ),
        },
    ]

    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": OLLAMA_MODEL,
                "messages": messages,
                "stream": False,
            },
            timeout=60,
        )

        response.raise_for_status()
        data = response.json()

        resolution = (
            data.get("message", {}).get("content", "").strip()
        )

        return resolution or None

    except (requests.RequestException, ValueError, AttributeError):
        return None


def analyze_ticket(title, description):
    """Classify a ticket and generate an LLM/RAG resolution if possible."""

    text = f"{title} {description}".lower()

    if any(word in text for word in [
        "vpn", "network", "internet", "wifi",
        "wi-fi", "connection", "router",
    ]):
        category = "Network / VPN"
        priority = "High"
        assigned_team = "Network Support"
        fallback = (
            "Check network connectivity, verify VPN settings, "
            "and reconnect using the updated credentials."
        )

    elif any(word in text for word in [
        "password", "login", "account", "access", "locked",
    ]):
        category = "Access"
        priority = "Medium"
        assigned_team = "IT Support"
        fallback = (
            "Verify the employee's identity and follow the "
            "approved account recovery procedure."
        )

    elif any(word in text for word in [
        "email", "outlook", "mailbox",
    ]):
        category = "Email"
        priority = "Medium"
        assigned_team = "Messaging Support"
        fallback = (
            "Check email connectivity, mailbox status, "
            "and mail server settings."
        )

    elif any(word in text for word in [
        "laptop", "keyboard", "mouse", "monitor", "printer",
    ]):
        category = "Hardware"
        priority = "Medium"
        assigned_team = "Hardware Support"
        fallback = (
            "Check device power, physical connections, drivers, "
            "and hardware status."
        )

    else:
        category = "General IT"
        priority = "Medium"
        assigned_team = "IT Support"
        fallback = (
            "Collect the error details, reproduce the issue, "
            "and review relevant system logs."
        )

    history = search_similar_tickets(title, description)

    resolution = generate_rag_resolution(
        title,
        description,
        history,
    )

    if resolution:
        method = "Ollama LLM + TF-IDF RAG"
    else:
        resolution = fallback
        method = "keyword baseline (Ollama fallback)"

    return {
        "category": category,
        "priority": priority,
        "assigned_team": assigned_team,
        "suggested_resolution": resolution,
        "method": method,
        "similar_tickets": history,
    }
