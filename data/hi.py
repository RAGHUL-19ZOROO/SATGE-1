from werkzeug.security import generate_password_hash
print(generate_password_hash("teacher123"))
print(generate_password_hash("student123"))