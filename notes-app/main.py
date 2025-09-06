from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import psycopg2
import os

app = FastAPI(title="Notes API", version="1.0.0")

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_NAME = os.getenv("DB_NAME", "notesdb")
DB_USER = os.getenv("DB_USER", "notesuser")
DB_PASS = os.getenv("DB_PASS", "notespwd")

def get_conn():
    return psycopg2.connect(
        host=DB_HOST,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASS
    )

class Note(BaseModel):
    user_id: int
    title: str
    content: str

@app.on_event("startup")
def init_db():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS notes (
            id SERIAL PRIMARY KEY,
            user_id INT,
            title TEXT,
            content TEXT,
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)
    conn.commit()
    cur.close()
    conn.close()

@app.post("/api/v1/notes")
def create_note(note: Note):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("INSERT INTO notes (user_id, title, content) VALUES (%s, %s, %s) RETURNING id",
                (note.user_id, note.title, note.content))
    note_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()
    return {"id": note_id, "status": "created"}

@app.get("/api/v1/notes/{user_id}")
def get_notes(user_id: int):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, title, content, created_at FROM notes WHERE user_id = %s", (user_id,))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [{"id": r[0], "title": r[1], "content": r[2], "created_at": r[3]} for r in rows]

# -----------------------------
# Простая веб-страница для браузера
# -----------------------------
@app.get("/", response_class=HTMLResponse)
def home():
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Notes App</title>
    </head>
    <body>
        <h1>Notes App</h1>
        <form id="noteForm">
            User ID: <input type="number" id="user_id" value="1" /><br/>
            Title: <input type="text" id="title" /><br/>
            Content: <input type="text" id="content" /><br/>
            <button type="submit">Add Note</button>
        </form>
        <h2>Notes:</h2>
        <ul id="notesList"></ul>

        <script>
        const form = document.getElementById('noteForm');
        const notesList = document.getElementById('notesList');

        async function loadNotes() {
            const userId = document.getElementById('user_id').value;
            const res = await fetch(`/api/v1/notes/${userId}`);
            const data = await res.json();
            notesList.innerHTML = '';
            data.forEach(note => {
                const li = document.createElement('li');
                li.textContent = `[${note.id}] ${note.title}: ${note.content} (${note.created_at})`;
                notesList.appendChild(li);
            });
        }

        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            const userId = document.getElementById('user_id').value;
            const title = document.getElementById('title').value;
            const content = document.getElementById('content').value;
            await fetch('/api/v1/notes', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({user_id: parseInt(userId), title, content})
            });
            document.getElementById('title').value = '';
            document.getElementById('content').value = '';
            loadNotes();
        });

        loadNotes();
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)
