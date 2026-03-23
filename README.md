# Learning Paradiso

Learning Paradiso is a comprehensive, scalable Learning Management System (LMS) designed to serve as a 360-degree digital partner for college students and faculty.

Unlike rigid templates, this platform provides dynamic infrastructure that mirrors the complexity of a real-world university. It is tailored for Anna University style curriculum workflows while remaining accessible to non-technical users.

## Project Vision

Learning Paradiso is built to combine academic structure, content delivery, and communication into one unified platform.

## Key Value Propositions

- Zero-Code Management: The platform is built for educators, not programmers. Admins and teachers can add subjects, create units, and upload multimedia content through an intuitive dashboard without writing code.
- Granular Academic Organization: Students can be managed by Department, Year, and Semester so each learner sees content relevant to their academic path.
- Scalability and Efficiency: With a Flask and MySQL backend, the system supports expanding subjects and user growth while maintaining reliable performance.
- Comprehensive Student Partnership: The platform functions as a learning hub, not just a file host.

## Student Learning Hub Includes

- Structured Learning Paths: Topic-level overviews, text content, and PDF/TXT notes.
- Direct Communication: Built-in messaging through `/dm` for staff-student communication.
- Curriculum Alignment: Subject-code-based organization matching official syllabus structure.

## Core Functionality by Role

- Admin: Full control of departments, subject codes, and secure account management across campus.
- Staff: Streamlined tools to create units, define topic slugs, and upload downloadable resources.
- Students: Centralized home view to track units and dive into topic-specific learning.

## Existing Platform Features

- Home page with available units and topics
- Topic page with ordered sections: Overview, Text Content, Notes, and DA (DM)
- Staff pages to create units/topics and upload TXT/PDF notes
- Admin curriculum management for departments and subjects with subject codes
- Admin account management for staff and students with email/password
- Direct messaging between staff and students
- Local uploads folder for note storage

## Curriculum Structure

- App Name: Learning Paradiso
- Example course: Operating Systems
- Example units: Introduction, Process Management, Memory Management, Storage Management
- Topics are stored in `data/course_catalog.json` with video and notes mapping
- Department and subject catalog is stored in `data/anna_curriculum.json`

## Setup

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Create a `.env` file:

```env
FLASK_SECRET_KEY=dev-secret-key
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your_mysql_password
MYSQL_DATABASE=ai_lms
```

3. Run the app:

```bash
flask --app app run
```

## MySQL Auth Setup

1. Run the schema in `data/mysql_schema.sql`.
2. Insert at least one `staff` and one `student` user into the `users` table.
3. Store passwords as hashes generated with `werkzeug.security.generate_password_hash`.

## Routes

- `GET/POST /login` login for staff, student, and admin
- `GET /logout` clear session
- `GET /` home page
- `GET /topic/<topic_slug>` topic learning page
- `GET /staff` staff upload page
- `GET /admin` admin management page
- `POST /upload` upload notes
- `POST /staff/unit` create unit
- `POST /staff/topic` create topic
- `POST /admin/curriculum/department` add department
- `POST /admin/curriculum/subject` add subject with subject code
- `POST /admin/users` create staff/student account
- `GET /download/<topic_slug>` download notes
- `GET /dm` direct message page
