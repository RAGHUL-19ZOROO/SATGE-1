## AI Learning System

Modern AI-powered LMS built with Flask, HTML, CSS, and JavaScript for an Operating Systems course.

### Features

- Home page with available subjects/topics
- Topic learning page with YouTube video, AI explanation, chatbot, MCQ test, and result feedback
- Staff upload page for TXT/PDF notes
- OpenRouter integration using `openai/gpt-4o-mini`
- Local uploads folder for note storage
- Optional chat persistence in browser localStorage

### Course Structure

- Course: `Operating Systems`
- Units: Introduction, Process Management, Memory Management, Storage Management
- Topics are stored in [data/course_catalog.json](/C:/LMS/data/course_catalog.json) and each topic maps to its own video and notes file

### Setup

1. Install dependencies:
   `pip install -r requirements.txt`
2. Add a `.env` file with:

```env
OPENROUTER_API_KEY=your_key_here
OPENROUTER_MODEL=openai/gpt-4o-mini
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

1. Run the schema in [mysql_schema.sql](/C:/LMS/data/mysql_schema.sql).
2. Insert at least one `teacher` and one `student` user into the `users` table.
3. Store passwords as hashes generated with `werkzeug.security.generate_password_hash`.

### Routes

- `GET/POST /login` login for teacher and student
- `GET /logout` clear session
- `GET /` home page
- `GET /topic/<topic_slug>` topic learning page
- `GET /staff` staff upload page
- `POST /learn` generate explanation + MCQs
- `POST /doubt` answer topic doubts
- `POST /test` evaluate MCQ answers
- `POST /upload` upload notes
- `GET /download/<topic_slug>` download notes
