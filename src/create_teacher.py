"""Create or update a teacher account in the local credentials file."""

import argparse
import base64
import getpass
import hashlib
import json
import os
import secrets
import tempfile
from pathlib import Path

PBKDF2_ITERATIONS = 600_000
TEACHERS_FILE = Path(__file__).with_name("teachers.json")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("username", help="Username to create or update")
    args = parser.parse_args()
    username = args.username.strip()
    if not username:
        parser.error("username cannot be empty")

    password = getpass.getpass("Teacher password: ")
    confirmation = getpass.getpass("Confirm password: ")
    if not password:
        parser.error("password cannot be empty")
    if password != confirmation:
        parser.error("passwords do not match")

    try:
        data = json.loads(TEACHERS_FILE.read_text(encoding="utf-8"))
    except FileNotFoundError:
        data = {"teachers": []}
    except json.JSONDecodeError as error:
        parser.error(f"{TEACHERS_FILE} contains invalid JSON: {error}")

    if not isinstance(data, dict) or not isinstance(data.get("teachers"), list):
        parser.error(f"{TEACHERS_FILE} must contain a 'teachers' list")
    if any(
        not isinstance(teacher, dict)
        or not isinstance(teacher.get("username"), str)
        or not isinstance(teacher.get("password_hash"), str)
        for teacher in data["teachers"]
    ):
        parser.error(f"{TEACHERS_FILE} contains an invalid teacher account")
    usernames = [teacher["username"] for teacher in data["teachers"]]
    if len(usernames) != len(set(usernames)):
        parser.error(f"{TEACHERS_FILE} contains duplicate usernames")

    salt = secrets.token_bytes(16)
    derived_password = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS
    )
    password_hash = "pbkdf2_sha256${}${}${}".format(
        PBKDF2_ITERATIONS,
        base64.urlsafe_b64encode(salt).decode("ascii").rstrip("="),
        base64.urlsafe_b64encode(derived_password).decode("ascii").rstrip("="),
    )

    teachers = [
        teacher
        for teacher in data["teachers"]
        if isinstance(teacher, dict) and teacher.get("username") != username
    ]
    teachers.append({"username": username, "password_hash": password_hash})

    file_descriptor, temporary_path = tempfile.mkstemp(
        dir=TEACHERS_FILE.parent, prefix=".teachers-"
    )
    try:
        with os.fdopen(file_descriptor, "w", encoding="utf-8") as temporary_file:
            json.dump({"teachers": teachers}, temporary_file, indent=2)
            temporary_file.write("\n")
        os.replace(temporary_path, TEACHERS_FILE)
    finally:
        if os.path.exists(temporary_path):
            os.unlink(temporary_path)

    print(f"Teacher account {username!r} saved in {TEACHERS_FILE}.")


if __name__ == "__main__":
    main()
