"""Back up s0686_rel privately, then add its views counter with instant DDL."""

import hashlib
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import text

from database import db_engine


def main():
    root = Path(".hw9_runtime/backups")
    root.mkdir(parents=True, exist_ok=True)
    backup = root / ("s0686_rel_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + ".sql")
    url = db_engine.url
    assert url.database == "s0686_rel"
    environment = {**os.environ, "MYSQL_PWD": url.password or ""}
    with backup.open("wb") as stream:
        os.chmod(backup, 0o600)
        subprocess.run(["/opt/homebrew/opt/mysql@8.4/bin/mysqldump", "--host", url.host or "127.0.0.1",
                        "--port", str(url.port or 3306), "--user", url.username or "root", "--single-transaction",
                        "--no-tablespaces", "--set-gtid-purged=OFF", "s0686_rel"], env=environment, stdout=stream, check=True)
    record = {"timestamp": datetime.now(timezone.utc).isoformat(), "backup_private": str(backup),
              "backup_bytes": backup.stat().st_size, "backup_sha256": hashlib.sha256(backup.read_bytes()).hexdigest()}
    with db_engine.begin() as connection:
        record["database"] = connection.execute(text("SELECT DATABASE()")).scalar()
        record["rows_before"] = connection.execute(text("SELECT COUNT(*) FROM rental_listings")).scalar()
        columns = [row[0] for row in connection.execute(text("SHOW COLUMNS FROM rental_listings"))]
        if "view_count" not in columns:
            connection.execute(text("ALTER TABLE rental_listings ADD COLUMN view_count BIGINT UNSIGNED NOT NULL DEFAULT 0, ALGORITHM=INSTANT"))
            record["migration"] = "Added view_count using MySQL 8 instant DDL, after private backup"
        else:
            record["migration"] = "view_count already present; no alteration"
        connection.execute(text("CREATE TABLE IF NOT EXISTS s0686_cache_version (id INT PRIMARY KEY, version BIGINT NOT NULL)"))
        connection.execute(text("INSERT IGNORE INTO s0686_cache_version(id,version) VALUES(1,1)"))
        record["version_table"] = "s0686_cache_version, one global data-version row"
        record["rows_after"] = connection.execute(text("SELECT COUNT(*) FROM rental_listings")).scalar()
    Path("reports/hw09/raw").mkdir(parents=True, exist_ok=True)
    Path("reports/hw09/raw/setup.json").write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps(record, indent=2))


if __name__ == "__main__":
    main()
