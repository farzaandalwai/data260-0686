import os
import secrets
import subprocess
import tempfile
from pathlib import Path

import bcrypt
from sqlalchemy import inspect, text
from sqlalchemy.engine import make_url

from database import DATABASE_URL, db_engine


def backup_database():
    url = make_url(DATABASE_URL)
    descriptor, path = tempfile.mkstemp(prefix="s0686_hw7_before_users_", suffix=".sql", dir="/tmp")
    os.close(descriptor)
    os.chmod(path, 0o600)
    environment = os.environ.copy()
    environment["MYSQL_PWD"] = url.password or ""
    command = [
        "mysqldump",
        "--no-defaults",
        "--single-transaction",
        "--no-tablespaces",
        "--host", url.host or "127.0.0.1",
        "--port", str(url.port or 3306),
        "--user", url.username or "",
        url.database or "s0686_rel",
    ]
    with open(path, "wb") as output:
        subprocess.run(command, env=environment, stdout=output, check=True)
    if b"Dump completed" not in Path(path).read_bytes()[-200:]:
        raise RuntimeError("Database backup did not complete")
    return path


def add_columns():
    columns = {column["name"] for column in inspect(db_engine).get_columns("users")}
    with db_engine.begin() as connection:
        if "username" not in columns:
            connection.execute(text("ALTER TABLE users ADD COLUMN username VARCHAR(100) NULL"))
            connection.execute(text("UPDATE users SET username = CONCAT('legacy_', id) WHERE username IS NULL"))
            connection.execute(text("ALTER TABLE users MODIFY username VARCHAR(100) NOT NULL"))
            connection.execute(text("ALTER TABLE users ADD UNIQUE KEY uq_users_username (username)"))
        if "role" not in columns:
            connection.execute(text("ALTER TABLE users ADD COLUMN role VARCHAR(20) NOT NULL DEFAULT 'reader'"))


def seed_accounts():
    credentials = {}
    with db_engine.begin() as connection:
        for role in ("reader", "writer", "moderator"):
            username = f"{role}0686"
            exists = connection.execute(
                text("SELECT id FROM users WHERE username = :username"), {"username": username}
            ).first()
            if exists:
                continue
            password = secrets.token_urlsafe(18)
            password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
            connection.execute(
                text("INSERT INTO users (name, email, username, password_hash, role) VALUES (:name, :email, :username, :password_hash, :role)"),
                {
                    "name": username,
                    "email": f"{username}@example.invalid",
                    "username": username,
                    "password_hash": password_hash,
                    "role": role,
                },
            )
            credentials[username] = password
    if credentials:
        import json

        descriptor, path = tempfile.mkstemp(prefix="s0686_hw7_accounts_", suffix=".json", dir="/tmp")
        os.close(descriptor)
        os.chmod(path, 0o600)
        Path(path).write_text(json.dumps(credentials))
        print(f"Private test account file: {path}")


def ensure_jwt_secret():
    env_path = Path(__file__).resolve().parents[1] / ".env"
    if "JWT_SECRET=" not in env_path.read_text():
        with env_path.open("a") as output:
            output.write(f"\nJWT_SECRET={secrets.token_urlsafe(48)}\n")


if __name__ == "__main__":
    backup_path = backup_database()
    print(f"Private pre-migration database backup: {backup_path}")
    add_columns()
    seed_accounts()
    ensure_jwt_secret()
    print("User schema migration complete")
