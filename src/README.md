# Mergington High School Activities API

A super simple FastAPI application that allows students to view and sign up for extracurricular activities.

## Features

- View all available extracurricular activities
- Sign up for activities as an authenticated teacher
- Unregister students as an authenticated teacher
- Persist activities and registrations in SQLite

## Getting Started

1. Install the dependencies:

   ```
   pip install fastapi uvicorn
   ```

2. Run the application:

   ```
   python app.py
   ```

3. Open your browser and go to:
   - API documentation: http://localhost:8000/docs
   - Alternative documentation: http://localhost:8000/redoc

## API Endpoints

| Method | Endpoint                                                          | Description                                                         |
| ------ | ----------------------------------------------------------------- | ------------------------------------------------------------------- |
| GET    | `/activities`                                                     | Get all activities with their details and current participant count |
| POST   | `/auth/login`                                                      | Start a teacher session                                             |
| POST   | `/auth/logout`                                                     | End the current teacher session                                     |
| GET    | `/auth/me`                                                         | Check the current teacher session                                   |
| POST   | `/activities/{activity_name}/signup?email=student@mergington.edu` | Register a student for an activity (teacher only)                  |
| DELETE | `/activities/{activity_name}/unregister?email=student@mergington.edu` | Remove a student from an activity (teacher only)                |

## Data Model

The application uses a simple data model with meaningful identifiers:

1. **Activities** - Uses a generated database ID and includes:

   - Activity name
   - Description
   - Schedule
   - Maximum number of participants allowed
2. **Participants** - Stores activity registrations:

   - Activity ID
   - Student email

The SQLite database is created automatically at `src/activities.db`. Set the
`ACTIVITIES_DB_PATH` environment variable to use a different location, for
example:

```
ACTIVITIES_DB_PATH=/var/lib/mergington/activities.db python src/app.py
```

The initial activity catalog is inserted only when the database is empty. Existing
activities and registrations are preserved when the server restarts.
