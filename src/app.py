"""
High School Management System API

A super simple FastAPI application that allows students to view and sign up
for extracurricular activities at Mergington High School.
"""

import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Response
from fastapi import Cookie
from pydantic import BaseModel
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse

app = FastAPI(title="Mergington High School API",
              description="API for viewing and signing up for extracurricular activities")

# Mount the static files directory
current_dir = Path(__file__).parent
app.mount("/static", StaticFiles(directory=os.path.join(Path(__file__).parent,
          "static")), name="static")

TEACHERS_FILE = current_dir / "teachers.json"
SESSION_COOKIE = "teacher_session"
SESSION_DURATION = 8 * 60 * 60
PBKDF2_ITERATIONS = 600_000
_configured_session_secret = os.getenv("SESSION_SECRET")
if _configured_session_secret and len(_configured_session_secret.encode("utf-8")) < 32:
    raise RuntimeError("SESSION_SECRET must be at least 32 bytes long")
SESSION_SECRET = (
    _configured_session_secret.encode("utf-8")
    if _configured_session_secret
    else secrets.token_bytes(32)
)

# In-memory activity database
activities = {
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


class LoginRequest(BaseModel):
    username: str
    password: str


def load_teachers():
    try:
        data = json.loads(TEACHERS_FILE.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise HTTPException(
            status_code=503,
            detail="Teacher accounts are not configured. Follow the setup instructions.",
        ) from None
    except json.JSONDecodeError as error:
        raise HTTPException(
            status_code=500,
            detail="The teacher accounts file contains invalid JSON.",
        ) from error

    if not isinstance(data, dict) or not isinstance(data.get("teachers"), list):
        raise HTTPException(
            status_code=500,
            detail='The teacher accounts file must contain a "teachers" list.',
        )

    teachers = {}
    for teacher in data["teachers"]:
        if (
            not isinstance(teacher, dict)
            or not isinstance(teacher.get("username"), str)
            or not isinstance(teacher.get("password_hash"), str)
            or teacher["username"] in teachers
        ):
            raise HTTPException(
                status_code=500,
                detail="The teacher accounts file contains an invalid or duplicate account.",
            )
        teachers[teacher["username"]] = teacher["password_hash"]
    return teachers


def verify_password(password: str, encoded_hash: str) -> bool:
    try:
        algorithm, iterations, salt, expected = encoded_hash.split("$")
        iteration_count = int(iterations)
        if algorithm != "pbkdf2_sha256" or not 100_000 <= iteration_count <= 1_000_000:
            return False
        salt_bytes = base64.urlsafe_b64decode(salt + "=" * (-len(salt) % 4))
        expected_bytes = base64.urlsafe_b64decode(expected + "=" * (-len(expected) % 4))
    except (ValueError, TypeError):
        return False

    actual = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt_bytes, iteration_count
    )
    return hmac.compare_digest(actual, expected_bytes)


def create_session(username: str) -> str:
    payload = json.dumps(
        {"username": username, "expires": int(time.time()) + SESSION_DURATION},
        separators=(",", ":"),
    ).encode("utf-8")
    encoded_payload = base64.urlsafe_b64encode(payload).decode("ascii").rstrip("=")
    signature = hmac.new(
        SESSION_SECRET, encoded_payload.encode("ascii"), hashlib.sha256
    ).digest()
    encoded_signature = base64.urlsafe_b64encode(signature).decode("ascii").rstrip("=")
    return f"{encoded_payload}.{encoded_signature}"


def get_session_username(session: str | None) -> str | None:
    if not session:
        return None
    try:
        encoded_payload, encoded_signature = session.split(".")
        expected_signature = hmac.new(
            SESSION_SECRET, encoded_payload.encode("ascii"), hashlib.sha256
        ).digest()
        signature = base64.urlsafe_b64decode(
            encoded_signature + "=" * (-len(encoded_signature) % 4)
        )
        if not hmac.compare_digest(signature, expected_signature):
            return None

        payload = base64.urlsafe_b64decode(
            encoded_payload + "=" * (-len(encoded_payload) % 4)
        )
        session_data = json.loads(payload)
        username = session_data["username"]
        if (
            not isinstance(username, str)
            or session_data["expires"] < time.time()
            or username not in load_teachers()
        ):
            return None
        return username
    except (ValueError, KeyError, TypeError, UnicodeDecodeError, json.JSONDecodeError):
        return None


def require_teacher(session: str | None = Cookie(default=None, alias=SESSION_COOKIE)):
    username = get_session_username(session)
    if username is None:
        raise HTTPException(status_code=401, detail="Teacher login required")
    return username


@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")


@app.post("/auth/login")
def login(credentials: LoginRequest, response: Response):
    teachers = load_teachers()
    password_hash = teachers.get(credentials.username)
    if password_hash is None or not verify_password(credentials.password, password_hash):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    response.set_cookie(
        key=SESSION_COOKIE,
        value=create_session(credentials.username),
        max_age=SESSION_DURATION,
        httponly=True,
        secure=os.getenv("COOKIE_SECURE", "false").lower() == "true",
        samesite="strict",
        path="/",
    )
    return {"username": credentials.username}


@app.get("/auth/status")
def auth_status(session: str | None = Cookie(default=None, alias=SESSION_COOKIE)):
    username = get_session_username(session)
    return {"authenticated": username is not None, "username": username}


@app.post("/auth/logout")
def logout(response: Response):
    response.delete_cookie(
        key=SESSION_COOKIE,
        httponly=True,
        secure=os.getenv("COOKIE_SECURE", "false").lower() == "true",
        samesite="strict",
        path="/",
    )
    return {"message": "Logged out"}


@app.get("/activities")
def get_activities():
    return activities


@app.post("/activities/{activity_name}/signup")
def signup_for_activity(
    activity_name: str, email: str, teacher: str = Depends(require_teacher)
):
    """Sign up a student for an activity (teachers only)."""
    # Validate activity exists
    if activity_name not in activities:
        raise HTTPException(status_code=404, detail="Activity not found")

    # Get the specific activity
    activity = activities[activity_name]

    # Validate student is not already signed up
    if email in activity["participants"]:
        raise HTTPException(
            status_code=400,
            detail="Student is already signed up"
        )

    # Add student
    activity["participants"].append(email)
    return {"message": f"Signed up {email} for {activity_name}"}


@app.delete("/activities/{activity_name}/unregister")
def unregister_from_activity(
    activity_name: str, email: str, teacher: str = Depends(require_teacher)
):
    """Unregister a student from an activity (teachers only)."""
    # Validate activity exists
    if activity_name not in activities:
        raise HTTPException(status_code=404, detail="Activity not found")

    # Get the specific activity
    activity = activities[activity_name]

    # Validate student is signed up
    if email not in activity["participants"]:
        raise HTTPException(
            status_code=400,
            detail="Student is not signed up for this activity"
        )

    # Remove student
    activity["participants"].remove(email)
    return {"message": f"Unregistered {email} from {activity_name}"}
