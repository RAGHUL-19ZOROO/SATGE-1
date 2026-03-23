## Learning System

Flask-based LMS for an Operating Systems course with video lessons, text content, notes, and direct messaging.

### Features

- Home page with available units and topics
- Topic page with ordered sections: Overview, Text Content, Notes, and DA (DM)
- Staff content page to create units/topics and upload TXT/PDF notes
- Admin directory management for semester, courses, staff, and student
- Direct messaging between staff and students
- Local uploads folder for note storage

### Course Structure

- Course: `Operating Systems`
- Units: Introduction, Process Management, Memory Management, Storage Management
- Topics are stored in `data/course_catalog.json` and each topic maps to video and notes

### Setup

1. Install dependencies:
   `pip install -r requirements.txt`
2. Add a `.env` file with:

```env
FLASK_SECRET_KEY=dev-secret-key
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your_mysql_password
MYSQL_DATABASE=ai_lms
```

3. Run the app:
   `flask --app app run`

### MySQL Auth Setup

1. Run the schema in `data/mysql_schema.sql`.
2. Insert at least one `staff` and one `student` user into the `users` table.
3. Store passwords as hashes generated with `werkzeug.security.generate_password_hash`.

### Routes

- `GET/POST /login` login for staff, student, and admin
- `GET /logout` clear session
- `GET /` home page
- `GET /topic/<topic_slug>` topic learning page
- `GET /staff` staff upload page
- `POST /upload` upload notes
- `POST /staff/unit` create unit
- `POST /staff/topic` create topic
- `GET /download/<topic_slug>` download notes
- `GET /dm` direct message page
