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
