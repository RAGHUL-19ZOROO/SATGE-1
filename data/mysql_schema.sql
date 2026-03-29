CREATE DATABASE IF NOT EXISTS ai_lms;
USE ai_lms;

CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    full_name VARCHAR(120) NOT NULL,
    email VARCHAR(160) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role ENUM('teacher', 'student', 'admin') NOT NULL,
    is_active TINYINT(1) NOT NULL DEFAULT 1,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_login_at TIMESTAMP NULL DEFAULT NULL
);

CREATE TABLE IF NOT EXISTS login_audit (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    login_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ip_address VARCHAR(64) NULL,
    user_agent VARCHAR(255) NULL,
    CONSTRAINT fk_login_audit_user
        FOREIGN KEY (user_id) REFERENCES users(id)
        ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS student_notes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    topic_slug VARCHAR(120) NOT NULL,
    note_text MEDIUMTEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uq_student_topic_notes (user_id, topic_slug),
    CONSTRAINT fk_student_notes_user
        FOREIGN KEY (user_id) REFERENCES users(id)
        ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS subjects (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(120) NOT NULL UNIQUE,
    code VARCHAR(50) NOT NULL UNIQUE,
    description TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP
);

CREATE INDEX idx_subjects_code ON subjects(code);

CREATE TABLE IF NOT EXISTS departments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    code VARCHAR(30) NOT NULL UNIQUE,
    name VARCHAR(120) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS semesters (
    id INT AUTO_INCREMENT PRIMARY KEY,
    semester_no INT NOT NULL UNIQUE,
    title VARCHAR(120) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS academic_subjects (
    id INT AUTO_INCREMENT PRIMARY KEY,
    department_id INT NOT NULL,
    semester_id INT NOT NULL,
    subject_code VARCHAR(50) NOT NULL,
    subject_name VARCHAR(150) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_academic_subject_department
        FOREIGN KEY (department_id) REFERENCES departments(id)
        ON DELETE CASCADE,
    CONSTRAINT fk_academic_subject_semester
        FOREIGN KEY (semester_id) REFERENCES semesters(id)
        ON DELETE CASCADE,
    UNIQUE KEY uq_academic_subject (department_id, semester_id, subject_code)
);

CREATE TABLE IF NOT EXISTS staff_assignments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    staff_user_id INT NOT NULL,
    academic_subject_id INT NOT NULL,
    class_name VARCHAR(80) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_staff_assignment_user
        FOREIGN KEY (staff_user_id) REFERENCES users(id)
        ON DELETE CASCADE,
    CONSTRAINT fk_staff_assignment_subject
        FOREIGN KEY (academic_subject_id) REFERENCES academic_subjects(id)
        ON DELETE CASCADE,
    UNIQUE KEY uq_staff_assignment (staff_user_id, academic_subject_id, class_name)
);

CREATE TABLE IF NOT EXISTS student_profiles (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    register_number VARCHAR(60) NULL,
    department_id INT NOT NULL,
    semester_id INT NOT NULL,
    class_name VARCHAR(80) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_student_profile_user
        FOREIGN KEY (user_id) REFERENCES users(id)
        ON DELETE CASCADE,
    CONSTRAINT fk_student_profile_department
        FOREIGN KEY (department_id) REFERENCES departments(id)
        ON DELETE CASCADE,
    CONSTRAINT fk_student_profile_semester
        FOREIGN KEY (semester_id) REFERENCES semesters(id)
        ON DELETE CASCADE,
    UNIQUE KEY uq_student_profile_user (user_id)
);

CREATE TABLE IF NOT EXISTS staff_uploaded_notes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    staff_assignment_id INT NOT NULL,
    topic_slug VARCHAR(120) NOT NULL,
    unit_title VARCHAR(150) NOT NULL,
    topic_title VARCHAR(150) NOT NULL,
    note_title VARCHAR(150) NOT NULL,
    original_file_name VARCHAR(255) NOT NULL,
    stored_file_path VARCHAR(255) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_staff_note_assignment
        FOREIGN KEY (staff_assignment_id) REFERENCES staff_assignments(id)
        ON DELETE CASCADE
);

-- Insert users after generating password hashes in Python:

--
-- Example:
-- INSERT INTO users (full_name, email, password_hash, role) VALUES
-- ('OS Teacher', 'teacher@lms.com', 'paste_generated_hash_here', 'teacher'),
-- ('OS Student', 'student@lms.com', 'paste_generated_hash_here', 'student'),
-- ('System Admin', 'admin@lms.com', 'paste_generated_hash_here', 'admin');

-- Insert default subject for OS:
-- INSERT INTO subjects (name, code, description) VALUES
-- ('Operating Systems', 'OS', 'Learn about operating systems, processes, memory management, and scheduling');
