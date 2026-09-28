"""
High School Management System API

A super simple FastAPI application that allows students to view and sign up
for extracurricular activities at Mergington High School.
"""

import json
import secrets
import sqlite3
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
import os
import uvicorn

app = FastAPI(title="Mergington High School API",
              description="API for viewing and signing up for extracurricular activities")

# Mount the static files directory
current_dir = Path(__file__).parent
app.mount("/static", StaticFiles(directory=os.path.join(Path(__file__).parent,
          "static")), name="static")

database_path = Path(os.getenv("ACTIVITIES_DB_PATH", current_dir / "activities.db"))

with open(current_dir / "teachers.json", encoding="utf-8") as teachers_file:
    teachers = json.load(teachers_file)["teachers"]

teacher_sessions = {}


class LoginRequest(BaseModel):
    username: str
    password: str

# Initial activity catalog used to seed a new database.
initial_activities = {
    "Chess Club": {
        "description": "Learn strategies and compete in chess tournaments",
        "schedule": "Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 12,
        "participants": ["michael@mergington.edu", "daniel@mergington.edu"]
    },
    "Programming Class": {
        "description": "Learn programming fundamentals and build software projects",
        "schedule": "Tuesdays and Thursdays, 3:30 PM - 4:30 PM",
        "max_participants": 20,
        "participants": ["emma@mergington.edu", "sophia@mergington.edu"]
    },
    "Gym Class": {
        "description": "Physical education and sports activities",
        "schedule": "Mondays, Wednesdays, Fridays, 2:00 PM - 3:00 PM",
        "max_participants": 30,
        "participants": ["john@mergington.edu", "olivia@mergington.edu"]
    },
    "Soccer Team": {
        "description": "Join the school soccer team and compete in matches",
        "schedule": "Tuesdays and Thursdays, 4:00 PM - 5:30 PM",
        "max_participants": 22,
        "participants": ["liam@mergington.edu", "noah@mergington.edu"]
    },
    "Basketball Team": {
        "description": "Practice and play basketball with the school team",
        "schedule": "Wednesdays and Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["ava@mergington.edu", "mia@mergington.edu"]
    },
    "Art Club": {
        "description": "Explore your creativity through painting and drawing",
        "schedule": "Thursdays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["amelia@mergington.edu", "harper@mergington.edu"]
    },
    "Drama Club": {
        "description": "Act, direct, and produce plays and performances",
        "schedule": "Mondays and Wednesdays, 4:00 PM - 5:30 PM",
        "max_participants": 20,
        "participants": ["ella@mergington.edu", "scarlett@mergington.edu"]
    },
    "Math Club": {
        "description": "Solve challenging problems and participate in math competitions",
        "schedule": "Tuesdays, 3:30 PM - 4:30 PM",
        "max_participants": 10,
        "participants": ["james@mergington.edu", "benjamin@mergington.edu"]
    },
    "Debate Team": {
        "description": "Develop public speaking and argumentation skills",
        "schedule": "Fridays, 4:00 PM - 5:30 PM",
        "max_participants": 12,
        "participants": ["charlotte@mergington.edu", "henry@mergington.edu"]
    }
}


def get_connection():
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database():
    database_path.parent.mkdir(parents=True, exist_ok=True)
    with get_connection() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS activities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                description TEXT NOT NULL,
                schedule TEXT NOT NULL,
                max_participants INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS participants (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                activity_id INTEGER NOT NULL,
                email TEXT NOT NULL,
                UNIQUE(activity_id, email),
                FOREIGN KEY(activity_id) REFERENCES activities(id) ON DELETE CASCADE
            );
            """
        )
        activity_count = connection.execute(
            "SELECT COUNT(*) FROM activities"
        ).fetchone()[0]
        if activity_count == 0:
            for name, activity in initial_activities.items():
                cursor = connection.execute(
                    """
                    INSERT INTO activities (name, description, schedule, max_participants)
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        name,
                        activity["description"],
                        activity["schedule"],
                        activity["max_participants"],
                    ),
                )
                connection.executemany(
                    "INSERT INTO participants (activity_id, email) VALUES (?, ?)",
                    [
                        (cursor.lastrowid, email)
                        for email in activity["participants"]
                    ],
                )


initialize_database()


@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")


@app.get("/activities")
def get_activities():
    with get_connection() as connection:
        activity_rows = connection.execute(
            "SELECT * FROM activities ORDER BY name"
        ).fetchall()
        participant_rows = connection.execute(
            "SELECT activity_id, email FROM participants ORDER BY id"
        ).fetchall()

    participants_by_activity = {}
    for participant in participant_rows:
        participants_by_activity.setdefault(participant["activity_id"], []).append(
            participant["email"]
        )

    return {
        activity["name"]: {
            "description": activity["description"],
            "schedule": activity["schedule"],
            "max_participants": activity["max_participants"],
            "participants": participants_by_activity.get(activity["id"], []),
        }
        for activity in activity_rows
    }


@app.get("/auth/me")
def get_current_user(request: Request):
    session_id = request.cookies.get("teacher_session")
    username = teacher_sessions.get(session_id)
    return {"authenticated": username is not None, "username": username}


@app.post("/auth/login")
def login(credentials: LoginRequest, response: Response):
    teacher = next(
        (
            teacher
            for teacher in teachers
            if teacher["username"] == credentials.username
            and teacher["password"] == credentials.password
        ),
        None,
    )
    if teacher is None:
        raise HTTPException(status_code=401, detail="Invalid teacher credentials")

    session_id = secrets.token_urlsafe(32)
    teacher_sessions[session_id] = teacher["username"]
    response.set_cookie(
        "teacher_session",
        session_id,
        httponly=True,
        samesite="lax",
        max_age=60 * 60 * 8,
    )
    return {"message": "Teacher login successful", "username": teacher["username"]}


@app.post("/auth/logout")
def logout(request: Request, response: Response):
    session_id = request.cookies.get("teacher_session")
    teacher_sessions.pop(session_id, None)
    response.delete_cookie("teacher_session")
    return {"message": "Teacher logout successful"}


def require_teacher(request: Request):
    session_id = request.cookies.get("teacher_session")
    username = teacher_sessions.get(session_id)
    if username is None:
        raise HTTPException(status_code=401, detail="Teacher login required")
    return username


@app.post("/activities/{activity_name}/signup")
def signup_for_activity(activity_name: str, email: str, request: Request):
    """Sign up a student for an activity"""
    require_teacher(request)

    with get_connection() as connection:
        connection.execute("BEGIN IMMEDIATE")
        activity = connection.execute(
            "SELECT id, max_participants FROM activities WHERE name = ?",
            (activity_name,),
        ).fetchone()
        if activity is None:
            raise HTTPException(status_code=404, detail="Activity not found")

        participant_exists = connection.execute(
            "SELECT 1 FROM participants WHERE activity_id = ? AND email = ?",
            (activity["id"], email),
        ).fetchone()
        if participant_exists is not None:
            raise HTTPException(status_code=400, detail="Student is already signed up")

        participant_count = connection.execute(
            "SELECT COUNT(*) FROM participants WHERE activity_id = ?",
            (activity["id"],),
        ).fetchone()[0]
        if participant_count >= activity["max_participants"]:
            raise HTTPException(status_code=400, detail="Activity is full")

        connection.execute(
            "INSERT INTO participants (activity_id, email) VALUES (?, ?)",
            (activity["id"], email),
        )
    return {"message": f"Signed up {email} for {activity_name}"}


@app.delete("/activities/{activity_name}/unregister")
def unregister_from_activity(activity_name: str, email: str, request: Request):
    """Unregister a student from an activity"""
    require_teacher(request)

    with get_connection() as connection:
        activity = connection.execute(
            "SELECT id FROM activities WHERE name = ?",
            (activity_name,),
        ).fetchone()
        if activity is None:
            raise HTTPException(status_code=404, detail="Activity not found")

        result = connection.execute(
            "DELETE FROM participants WHERE activity_id = ? AND email = ?",
            (activity["id"], email),
        )
        if result.rowcount == 0:
            raise HTTPException(
                status_code=400,
                detail="Student is not signed up for this activity",
            )
    return {"message": f"Unregistered {email} from {activity_name}"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
