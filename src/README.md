# Mergington High School Activities API

A FastAPI application that lets students view extracurricular activities and their participants. Only logged-in teachers can add or remove student enrollments.

## Getting started

1. Install the dependencies from the repository root:

   ```
   pip install -r requirements.txt
   ```

2. From this directory, create a teacher account. The script prompts for a password and stores only its PBKDF2 hash in the local, Git-ignored `teachers.json` file. Running it again with an existing username updates that account's password.

   ```
   python create_teacher.py teacher
   ```

3. Start the API from this directory:

   ```
   uvicorn app:app --reload
   ```

4. Open http://localhost:8000. Anyone can view activities and participants. Use the account icon in the upper-right corner to log in before enrolling or unregistering students.

Teacher sessions are held in an HTTP-only, same-site cookie and expire after eight hours. Without configuration, the signing key is generated at startup, so sessions are invalidated when the server restarts. For a persistent or multi-worker deployment, configure `SESSION_SECRET` with a stable, randomly generated value of at least 32 bytes. For an HTTPS deployment, also set `COOKIE_SECURE=true` so browsers only send the session cookie over HTTPS.

## API endpoints

| Method | Endpoint | Description |
| ------ | -------- | ----------- |
| GET | `/activities` | Get all activities and their participants |
| POST | `/auth/login` | Log in as a teacher |
| GET | `/auth/status` | Check the current teacher login |
| POST | `/auth/logout` | Log out |
| POST | `/activities/{activity_name}/signup?email=student@mergington.edu` | Enroll a student (teacher login required) |
| DELETE | `/activities/{activity_name}/unregister?email=student@mergington.edu` | Unregister a student (teacher login required) |
