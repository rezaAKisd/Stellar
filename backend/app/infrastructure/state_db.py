"""SQLite-backed state store for persisting projects and tasks."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Optional


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class ProjectRow:
    owner: str
    project_id: str
    title: str
    source: str
    folder_path: str
    item_count: int
    download_status: str
    export_status: str
    download_progress: float
    export_progress: float
    error_message: Optional[str]
    created_at: str
    updated_at: str
    video_urls: str = '[]'  # JSON array
    photo_urls: str = '[]'  # JSON array
    merged_video_url: Optional[str] = None
    zip_bundle_url: Optional[str] = None
    expires_at: Optional[str] = None
    is_expired: int = 0
    submission_date: Optional[str] = None


@dataclass(frozen=True)
class TaskRow:
    task_id: str
    owner: str
    project_id: str
    task_type: str  # download | build
    status: str  # queued | running | success | failed
    progress: float
    message: Optional[str]
    error_message: Optional[str]
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class DestinationUsernameRow:
    id: str
    owner: str
    username: str
    display_name: Optional[str]
    avatar_url: Optional[str]
    last_fetched_at: Optional[str]
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class DestinationHighlightRow:
    id: str
    owner: str
    destination_username_id: str
    instagram_username: str
    highlight_id: str
    name: str
    cover_url: Optional[str]
    item_count: int
    project_id: Optional[str]
    created_at: str
    updated_at: str


class StateDB:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA foreign_keys=ON;")
        return conn

    def init_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS projects (
                    owner TEXT NOT NULL,
                    project_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    source TEXT NOT NULL,
                    folder_path TEXT NOT NULL,
                    item_count INTEGER NOT NULL DEFAULT 0,
                    download_status TEXT NOT NULL DEFAULT 'idle',
                    export_status TEXT NOT NULL DEFAULT 'not_started',
                    download_progress REAL NOT NULL DEFAULT 0.0,
                    export_progress REAL NOT NULL DEFAULT 0.0,
                    error_message TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (owner, project_id)
                );

                CREATE TABLE IF NOT EXISTS tasks (
                    task_id TEXT PRIMARY KEY,
                    owner TEXT NOT NULL,
                    project_id TEXT NOT NULL,
                    task_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    progress REAL NOT NULL DEFAULT 0.0,
                    message TEXT,
                    error_message TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (owner, project_id) REFERENCES projects(owner, project_id)
                        ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_tasks_owner_status_created
                    ON tasks(owner, status, created_at);
                CREATE INDEX IF NOT EXISTS idx_tasks_project_status
                    ON tasks(owner, project_id, status);
                """
            )

    def init_schema_v2(self) -> None:
        """Run migration to add v2 schema changes (artifact tracking, destinations, quotas)"""
        with self._connect() as conn:
            # Check if migration already applied by checking for video_urls column
            cursor = conn.execute("PRAGMA table_info(projects)")
            columns = [row[1] for row in cursor.fetchall()]

            if 'video_urls' not in columns:
                # Add new columns to projects table
                conn.execute("ALTER TABLE projects ADD COLUMN video_urls TEXT DEFAULT '[]'")
                conn.execute("ALTER TABLE projects ADD COLUMN photo_urls TEXT DEFAULT '[]'")
                conn.execute("ALTER TABLE projects ADD COLUMN merged_video_url TEXT")
                conn.execute("ALTER TABLE projects ADD COLUMN zip_bundle_url TEXT")
                conn.execute("ALTER TABLE projects ADD COLUMN expires_at TEXT")
                conn.execute("ALTER TABLE projects ADD COLUMN is_expired INTEGER DEFAULT 0")
                conn.execute("ALTER TABLE projects ADD COLUMN submission_date TEXT")

            # Create new tables and indexes (IF NOT EXISTS handles idempotency)
            conn.executescript(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS idx_projects_owner_source
                    ON projects(owner, source);

                CREATE INDEX IF NOT EXISTS idx_projects_expires_at
                    ON projects(expires_at, is_expired);

                CREATE TABLE IF NOT EXISTS destination_usernames (
                    id TEXT PRIMARY KEY,
                    owner TEXT NOT NULL,
                    username TEXT NOT NULL,
                    display_name TEXT,
                    avatar_url TEXT,
                    last_fetched_at TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(owner, username)
                );

                CREATE INDEX IF NOT EXISTS idx_destination_usernames_owner
                    ON destination_usernames(owner);

                CREATE TABLE IF NOT EXISTS destination_highlights (
                    id TEXT PRIMARY KEY,
                    owner TEXT NOT NULL,
                    destination_username_id TEXT NOT NULL,
                    instagram_username TEXT NOT NULL,
                    highlight_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    cover_url TEXT,
                    item_count INTEGER NOT NULL DEFAULT 0,
                    project_id TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (destination_username_id) REFERENCES destination_usernames(id) ON DELETE CASCADE,
                    FOREIGN KEY (owner, project_id) REFERENCES projects(owner, project_id) ON DELETE SET NULL,
                    UNIQUE(owner, highlight_id)
                );

                CREATE INDEX IF NOT EXISTS idx_destination_highlights_owner_username
                    ON destination_highlights(owner, destination_username_id);

                CREATE INDEX IF NOT EXISTS idx_destination_highlights_project
                    ON destination_highlights(owner, project_id);

                CREATE TABLE IF NOT EXISTS daily_quotas (
                    owner TEXT NOT NULL,
                    submission_date TEXT NOT NULL,
                    submission_count INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (owner, submission_date)
                );

                CREATE INDEX IF NOT EXISTS idx_daily_quotas_date
                    ON daily_quotas(submission_date);

                CREATE TABLE IF NOT EXISTS artifact_downloads (
                    id TEXT PRIMARY KEY,
                    owner TEXT NOT NULL,
                    project_id TEXT NOT NULL,
                    artifact_type TEXT NOT NULL,
                    artifact_url TEXT NOT NULL,
                    downloaded_at TEXT NOT NULL,
                    FOREIGN KEY (owner, project_id) REFERENCES projects(owner, project_id) ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_artifact_downloads_owner_project
                    ON artifact_downloads(owner, project_id);
                """
            )

    def mark_orphaned_tasks_failed(self) -> int:
        """Mark running tasks as failed (useful after restart/reload)."""
        with self._connect() as conn:
            now = _utc_now_iso()
            cur = conn.execute(
                "UPDATE tasks SET status='failed', error_message=?, updated_at=? WHERE status='running'",
                ("Server restarted while task was running", now),
            )
            return cur.rowcount

    def upsert_project(
        self,
        *,
        owner: str,
        project_id: str,
        title: str,
        source: str,
        folder_path: str,
        item_count: int = 0,
        download_status: str = "idle",
        export_status: str = "not_started",
        download_progress: float = 0.0,
        export_progress: float = 0.0,
        error_message: Optional[str] = None,
        expires_at: Optional[str] = None,
        submission_date: Optional[str] = None,
    ) -> None:
        now = _utc_now_iso()
        with self._connect() as conn:
            # Check if new columns exist (for backwards compatibility)
            cursor = conn.execute("PRAGMA table_info(projects)")
            columns = [row[1] for row in cursor.fetchall()]
            has_v2_columns = 'expires_at' in columns

            if has_v2_columns:
                conn.execute(
                    """
                    INSERT INTO projects (
                        owner, project_id, title, source, folder_path,
                        item_count, download_status, export_status,
                        download_progress, export_progress, error_message,
                        expires_at, submission_date,
                        created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(owner, project_id) DO UPDATE SET
                        title=excluded.title,
                        source=excluded.source,
                        folder_path=excluded.folder_path,
                        item_count=excluded.item_count,
                        download_status=excluded.download_status,
                        export_status=excluded.export_status,
                        download_progress=excluded.download_progress,
                        export_progress=excluded.export_progress,
                        error_message=excluded.error_message,
                        expires_at=excluded.expires_at,
                        submission_date=excluded.submission_date,
                        updated_at=excluded.updated_at
                    """,
                    (
                        owner,
                        project_id,
                        title,
                        source,
                        folder_path,
                        int(item_count),
                        download_status,
                        export_status,
                        float(download_progress),
                        float(export_progress),
                        error_message,
                        expires_at,
                        submission_date,
                        now,
                        now,
                    ),
                )
            else:
                # Fallback for old schema (without v2 columns)
                conn.execute(
                    """
                    INSERT INTO projects (
                        owner, project_id, title, source, folder_path,
                        item_count, download_status, export_status,
                        download_progress, export_progress, error_message,
                        created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(owner, project_id) DO UPDATE SET
                        title=excluded.title,
                        source=excluded.source,
                        folder_path=excluded.folder_path,
                        item_count=excluded.item_count,
                        download_status=excluded.download_status,
                        export_status=excluded.export_status,
                        download_progress=excluded.download_progress,
                        export_progress=excluded.export_progress,
                        error_message=excluded.error_message,
                        updated_at=excluded.updated_at
                    """,
                    (
                        owner,
                        project_id,
                        title,
                        source,
                        folder_path,
                        int(item_count),
                        download_status,
                        export_status,
                        float(download_progress),
                        float(export_progress),
                        error_message,
                        now,
                        now,
                    ),
                )

    def list_projects(self, owner: str) -> list[ProjectRow]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM projects
                WHERE owner = ?
                ORDER BY updated_at DESC
                """,
                (owner,),
            ).fetchall()
        return [self._project_from_row(r) for r in rows]

    def get_project(self, owner: str, project_id: str) -> Optional[ProjectRow]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM projects WHERE owner = ? AND project_id = ?",
                (owner, project_id),
            ).fetchone()
        return self._project_from_row(row) if row else None

    def update_project(
        self,
        *,
        owner: str,
        project_id: str,
        fields: dict[str, Any],
    ) -> None:
        if not fields:
            return
        fields = dict(fields)
        fields["updated_at"] = _utc_now_iso()
        assignments = ", ".join([f"{k}=?" for k in fields.keys()])
        values: list[Any] = list(fields.values()) + [owner, project_id]
        with self._connect() as conn:
            conn.execute(
                f"UPDATE projects SET {assignments} WHERE owner = ? AND project_id = ?",
                values,
            )

    def enqueue_task(
        self,
        *,
        task_id: str,
        owner: str,
        project_id: str,
        task_type: str,
        message: Optional[str] = None,
    ) -> None:
        now = _utc_now_iso()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO tasks (
                    task_id, owner, project_id, task_type, status,
                    progress, message, error_message, created_at, updated_at
                ) VALUES (?, ?, ?, ?, 'queued', 0.0, ?, NULL, ?, ?)
                """,
                (task_id, owner, project_id, task_type, message, now, now),
            )

    def task_exists_active(self, *, owner: str, project_id: str, task_type: str) -> bool:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT 1 FROM tasks
                WHERE owner = ? AND project_id = ? AND task_type = ?
                  AND status IN ('queued', 'running')
                LIMIT 1
                """,
                (owner, project_id, task_type),
            ).fetchone()
        return row is not None

    def claim_next_task(self) -> Optional[TaskRow]:
        """
        Atomically claim the next queued task (FIFO).
        Returns the claimed task row or None.
        """
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE;")
            row = conn.execute(
                """
                SELECT * FROM tasks
                WHERE status = 'queued'
                ORDER BY created_at ASC
                LIMIT 1
                """
            ).fetchone()
            if not row:
                conn.execute("COMMIT;")
                return None

            now = _utc_now_iso()
            conn.execute(
                "UPDATE tasks SET status='running', updated_at=? WHERE task_id=? AND status='queued'",
                (now, row["task_id"]),
            )
            conn.execute("COMMIT;")

        return self._task_from_row(row)

    def update_task(
        self,
        *,
        task_id: str,
        fields: dict[str, Any],
    ) -> None:
        if not fields:
            return
        fields = dict(fields)
        fields["updated_at"] = _utc_now_iso()
        assignments = ", ".join([f"{k}=?" for k in fields.keys()])
        values: list[Any] = list(fields.values()) + [task_id]
        with self._connect() as conn:
            conn.execute(
                f"UPDATE tasks SET {assignments} WHERE task_id = ?",
                values,
            )

    def cancel_task(self, owner: str, task_id: str) -> bool:
        """Cancel a queued or running task"""
        with self._connect() as conn:
            cur = conn.execute(
                """
                UPDATE tasks
                SET status = 'cancelled',
                    error_message = 'Task cancelled by user',
                    updated_at = ?
                WHERE task_id = ?
                  AND owner = ?
                  AND status IN ('queued', 'running')
                """,
                (_utc_now_iso(), task_id, owner),
            )
            return cur.rowcount > 0

    def get_task(self, task_id: str) -> Optional[TaskRow]:
        """Get a task by ID"""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM tasks WHERE task_id = ?",
                (task_id,),
            ).fetchone()
            return self._task_from_row(row) if row else None

    def get_active_task_for_project(self, owner: str, project_id: str) -> Optional[TaskRow]:
        """Get the active (queued or running) task for a project"""
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT * FROM tasks
                WHERE owner = ? AND project_id = ? AND status IN ('queued', 'running')
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (owner, project_id),
            ).fetchone()
            return self._task_from_row(row) if row else None

    def get_active_tasks(self, owner: str, project_id: str) -> list[TaskRow]:
        """Get all active (queued or running) tasks for a project"""
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM tasks
                WHERE owner = ? AND project_id = ? AND status IN ('queued', 'running')
                ORDER BY created_at ASC
                """,
                (owner, project_id),
            ).fetchall()
        return [self._task_from_row(row) for row in rows]

    def delete_project(self, owner: str, project_id: str) -> bool:
        with self._connect() as conn:
            # First, unlink any destination highlights that reference this project
            # This avoids the composite foreign key ON DELETE SET NULL issue
            conn.execute(
                "UPDATE destination_highlights SET project_id = NULL WHERE owner = ? AND project_id = ?",
                (owner, project_id),
            )

            # Now delete the project (cascades to tasks via ON DELETE CASCADE)
            cur = conn.execute(
                "DELETE FROM projects WHERE owner = ? AND project_id = ?",
                (owner, project_id),
            )
            return cur.rowcount > 0

    # Quota and Duplicate Detection Methods

    def check_duplicate_url(self, owner: str, source: str) -> bool:
        """Check if URL already exists for this user"""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT 1 FROM projects WHERE owner = ? AND source = ? LIMIT 1",
                (owner, source),
            ).fetchone()
        return row is not None

    def increment_daily_quota(self, owner: str) -> tuple[int, bool]:
        """
        Increment and check daily submission quota.
        Returns (current_count, exceeded) where exceeded is True if over limit (50).
        """
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        now = _utc_now_iso()

        with self._connect() as conn:
            # Get or create quota record
            row = conn.execute(
                "SELECT submission_count FROM daily_quotas WHERE owner = ? AND submission_date = ?",
                (owner, today),
            ).fetchone()

            if row is None:
                # Create new quota record
                conn.execute(
                    """
                    INSERT INTO daily_quotas (owner, submission_date, submission_count, created_at, updated_at)
                    VALUES (?, ?, 1, ?, ?)
                    """,
                    (owner, today, now, now),
                )
                return (1, False)
            else:
                # Increment existing quota
                current_count = row["submission_count"]
                new_count = current_count + 1
                conn.execute(
                    "UPDATE daily_quotas SET submission_count = ?, updated_at = ? WHERE owner = ? AND submission_date = ?",
                    (new_count, now, owner, today),
                )
                return (new_count, new_count > 50)

    def get_concurrent_task_count(self, owner: str) -> int:
        """Count running tasks for user"""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT COUNT(*) as count FROM tasks WHERE owner = ? AND status = 'running'",
                (owner,),
            ).fetchone()
        return row["count"] if row else 0

    # Expiration Methods

    def calculate_expiration_date(self, created_at: str) -> str:
        """Calculate expiration date (created_at + 30 days)"""
        from datetime import timedelta
        created_dt = datetime.fromisoformat(created_at)
        expires_dt = created_dt + timedelta(days=30)
        return expires_dt.isoformat()

    def mark_expired_projects(self) -> int:
        """Mark projects as expired if past expires_at date. Returns count of marked projects."""
        now = _utc_now_iso()
        with self._connect() as conn:
            cur = conn.execute(
                "UPDATE projects SET is_expired = 1, updated_at = ? WHERE expires_at IS NOT NULL AND expires_at < ? AND is_expired = 0",
                (now, now),
            )
            return cur.rowcount

    def cleanup_expired_artifacts(self) -> list[ProjectRow]:
        """Return list of expired projects for file cleanup"""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM projects WHERE is_expired = 1"
            ).fetchall()
        return [self._project_from_row(r) for r in rows]

    # Destination Username Methods

    def upsert_destination_username(
        self,
        *,
        owner: str,
        username: str,
        display_name: Optional[str] = None,
        avatar_url: Optional[str] = None,
        last_fetched_at: Optional[str] = None,
        username_id: Optional[str] = None,
    ) -> str:
        """Create or update destination username. Returns ID."""
        import uuid
        now = _utc_now_iso()
        id_to_use = username_id or str(uuid.uuid4())

        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO destination_usernames (
                    id, owner, username, display_name, avatar_url, last_fetched_at, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(owner, username) DO UPDATE SET
                    display_name = excluded.display_name,
                    avatar_url = excluded.avatar_url,
                    last_fetched_at = excluded.last_fetched_at,
                    updated_at = excluded.updated_at
                """,
                (id_to_use, owner, username, display_name, avatar_url, last_fetched_at, now, now),
            )
        return id_to_use

    def list_destination_usernames(self, owner: str) -> list[DestinationUsernameRow]:
        """Get all destination usernames for owner"""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM destination_usernames WHERE owner = ? ORDER BY created_at DESC",
                (owner,),
            ).fetchall()
        return [self._destination_username_from_row(r) for r in rows]

    def get_destination_username(self, owner: str, username_id: str) -> Optional[DestinationUsernameRow]:
        """Get specific destination username"""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM destination_usernames WHERE owner = ? AND id = ?",
                (owner, username_id),
            ).fetchone()
        return self._destination_username_from_row(row) if row else None

    def delete_destination_username(self, owner: str, username_id: str) -> bool:
        """Delete destination username (cascades to highlights). Returns True if deleted."""
        with self._connect() as conn:
            cur = conn.execute(
                "DELETE FROM destination_usernames WHERE owner = ? AND id = ?",
                (owner, username_id),
            )
            return cur.rowcount > 0

    # Destination Highlight Methods

    def upsert_destination_highlights(
        self, owner: str, username_id: str, highlights: list[dict[str, Any]]
    ) -> int:
        """Bulk upsert destination highlights. Removes old highlights not in the new list. Returns count inserted/updated."""
        import uuid
        now = _utc_now_iso()
        count = 0

        with self._connect() as conn:
            # First, delete highlights that are no longer present in the fetched list
            if highlights:
                highlight_ids = [hl["highlight_id"] for hl in highlights]
                placeholders = ",".join("?" * len(highlight_ids))
                conn.execute(
                    f"""
                    DELETE FROM destination_highlights
                    WHERE owner = ? AND destination_username_id = ?
                    AND highlight_id NOT IN ({placeholders})
                    """,
                    [owner, username_id] + highlight_ids,
                )
            else:
                # If no highlights fetched, delete all for this username
                conn.execute(
                    """
                    DELETE FROM destination_highlights
                    WHERE owner = ? AND destination_username_id = ?
                    """,
                    (owner, username_id),
                )

            # Then upsert the new/updated highlights
            for hl in highlights:
                hl_id = str(uuid.uuid4())
                conn.execute(
                    """
                    INSERT INTO destination_highlights (
                        id, owner, destination_username_id, instagram_username, highlight_id,
                        name, cover_url, item_count, project_id, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(owner, highlight_id) DO UPDATE SET
                        name = excluded.name,
                        cover_url = excluded.cover_url,
                        item_count = excluded.item_count,
                        updated_at = excluded.updated_at
                    """,
                    (
                        hl_id,
                        owner,
                        username_id,
                        hl.get("instagram_username", ""),
                        hl["highlight_id"],
                        hl["name"],
                        hl.get("cover_url"),
                        hl.get("item_count", 0),
                        None,
                        now,
                        now,
                    ),
                )
                count += 1
        return count

    def list_destination_highlights(
        self, owner: str, username_id: str
    ) -> list[DestinationHighlightRow]:
        """Get all highlights for a destination username"""
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM destination_highlights
                WHERE owner = ? AND destination_username_id = ?
                ORDER BY created_at DESC
                """,
                (owner, username_id),
            ).fetchall()
        return [self._destination_highlight_from_row(r) for r in rows]

    def link_highlight_to_project(self, owner: str, highlight_id: str, project_id: str) -> None:
        """Link destination highlight to project after download"""
        now = _utc_now_iso()
        with self._connect() as conn:
            conn.execute(
                "UPDATE destination_highlights SET project_id = ?, updated_at = ? WHERE owner = ? AND highlight_id = ?",
                (project_id, now, owner, highlight_id),
            )

    # Audit Logging

    def log_artifact_download(
        self, owner: str, project_id: str, artifact_type: str, artifact_url: str
    ) -> None:
        """Log artifact download for audit trail"""
        import uuid
        now = _utc_now_iso()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO artifact_downloads (id, owner, project_id, artifact_type, artifact_url, downloaded_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (str(uuid.uuid4()), owner, project_id, artifact_type, artifact_url, now),
            )

    def _project_from_row(self, row: sqlite3.Row) -> ProjectRow:
        return ProjectRow(
            owner=row["owner"],
            project_id=row["project_id"],
            title=row["title"],
            source=row["source"],
            folder_path=row["folder_path"],
            item_count=int(row["item_count"]),
            download_status=row["download_status"],
            export_status=row["export_status"],
            download_progress=float(row["download_progress"]),
            export_progress=float(row["export_progress"]),
            error_message=row["error_message"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            video_urls=row["video_urls"] if "video_urls" in row.keys() else "[]",
            photo_urls=row["photo_urls"] if "photo_urls" in row.keys() else "[]",
            merged_video_url=row["merged_video_url"] if "merged_video_url" in row.keys() else None,
            zip_bundle_url=row["zip_bundle_url"] if "zip_bundle_url" in row.keys() else None,
            expires_at=row["expires_at"] if "expires_at" in row.keys() else None,
            is_expired=row["is_expired"] if "is_expired" in row.keys() else 0,
            submission_date=row["submission_date"] if "submission_date" in row.keys() else None,
        )

    def _task_from_row(self, row: sqlite3.Row) -> TaskRow:
        return TaskRow(
            task_id=row["task_id"],
            owner=row["owner"],
            project_id=row["project_id"],
            task_type=row["task_type"],
            status=row["status"],
            progress=float(row["progress"]),
            message=row["message"],
            error_message=row["error_message"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def _destination_username_from_row(self, row: sqlite3.Row) -> DestinationUsernameRow:
        return DestinationUsernameRow(
            id=row["id"],
            owner=row["owner"],
            username=row["username"],
            display_name=row["display_name"],
            avatar_url=row["avatar_url"],
            last_fetched_at=row["last_fetched_at"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def _destination_highlight_from_row(self, row: sqlite3.Row) -> DestinationHighlightRow:
        return DestinationHighlightRow(
            id=row["id"],
            owner=row["owner"],
            destination_username_id=row["destination_username_id"],
            instagram_username=row["instagram_username"],
            highlight_id=row["highlight_id"],
            name=row["name"],
            cover_url=row["cover_url"],
            item_count=int(row["item_count"]),
            project_id=row["project_id"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
