import os
import shutil
import subprocess
import urllib.parse
from datetime import datetime

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///e:/Antigravity/Advance-Task-Tracker/database/tasktracker.db")
BACKUP_DIR = "e:/Antigravity/Advance-Task-Tracker/storage/backups"
os.makedirs(BACKUP_DIR, exist_ok=True)

def run_backup():
    print(f"[{datetime.now().isoformat()}] Initiating Database Backup process...")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    if DATABASE_URL.startswith("sqlite:///"):
        # SQLite backup path
        src_path = DATABASE_URL.replace("sqlite:///", "")
        if not os.path.exists(src_path):
            print(f"Error: SQLite source database not found at '{src_path}'")
            return False
            
        dest_filename = f"backup_sqlite_{timestamp}.db"
        dest_path = os.path.join(BACKUP_DIR, dest_filename)
        try:
            shutil.copy2(src_path, dest_path)
            print(f"Success: SQLite database backed up to '{dest_path}'")
            return True
        except Exception as e:
            print(f"Failed to copy SQLite database: {e}")
            return False
            
    elif DATABASE_URL.startswith("postgresql://") or DATABASE_URL.startswith("postgres://"):
        # PostgreSQL backup
        try:
            # Parse DATABASE_URL
            parsed = urllib.parse.urlparse(DATABASE_URL)
            db_name = parsed.path.lstrip("/")
            username = parsed.username
            password = parsed.password
            host = parsed.hostname
            port = parsed.port or 5432
            
            dest_filename = f"backup_postgres_{db_name}_{timestamp}.sql"
            dest_path = os.path.join(BACKUP_DIR, dest_filename)
            
            # Construct pg_dump command
            # Using pg_dump --clean to include DROP table statements in output for easy restores
            cmd = ["pg_dump", "-h", host, "-p", str(port), "-U", username, "-F", "p", "-f", dest_path, db_name]
            
            # Setup environment variables to pass PG_PASSWORD securely without exposing it in cmd args
            env = os.environ.copy()
            if password:
                env["PGPASSWORD"] = password
                
            print(f"Running pg_dump command for database '{db_name}'...")
            result = subprocess.run(cmd, env=env, capture_output=True, text=True)
            
            if result.returncode == 0:
                print(f"Success: PostgreSQL database backed up to '{dest_path}'")
                return True
            else:
                print(f"pg_dump error (code {result.returncode}): {result.stderr}")
                return False
        except Exception as e:
            print(f"Error parsing/running PostgreSQL backup: {e}")
            return False
    else:
        print(f"Unsupported DATABASE_URL scheme in '{DATABASE_URL}'")
        return False

if __name__ == "__main__":
    run_backup()
