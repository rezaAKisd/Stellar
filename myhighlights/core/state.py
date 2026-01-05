"""Centralized application state"""
from qtpy.QtCore import QObject, Signal
from typing import List, Dict, Optional
from ..models.job import HighlightJob
from ..models.auth import AuthState


class AppState(QObject):
    """Centralized application state with signals"""

    # Signals
    jobs_changed = Signal()
    auth_changed = Signal()
    toast_message = Signal(str, str)  # message, type ('info', 'success', 'error')

    # Fine-grained progress signals
    download_progress = Signal(str, float, str, str)  # job_id, progress, speed_text, eta_text
    build_progress = Signal(str, float, str)  # job_id, progress, stage

    def __init__(self):
        super().__init__()
        self.auth = AuthState()
        self.jobs: List[HighlightJob] = []
        self._jobs_dict: Dict[str, HighlightJob] = {}

    def add_job(self, job: HighlightJob):
        """Add a new job"""
        self.jobs.insert(0, job)  # Add to beginning for newest first
        self._jobs_dict[job.id] = job
        self.jobs_changed.emit()

    def update_job(self, job: HighlightJob):
        """Update an existing job (triggers UI refresh)"""
        if job.id in self._jobs_dict:
            self.jobs_changed.emit()

    def remove_job(self, job_id: str):
        """Remove a job"""
        if job_id in self._jobs_dict:
            job = self._jobs_dict[job_id]
            self.jobs.remove(job)
            del self._jobs_dict[job_id]
            self.jobs_changed.emit()

    def set_jobs(self, jobs: List[HighlightJob]):
        """Replace all jobs (used for restore on startup)."""
        self.jobs = list(jobs)
        self._jobs_dict = {job.id: job for job in self.jobs}
        self.jobs_changed.emit()

    def get_job(self, job_id: str) -> Optional[HighlightJob]:
        """Get job by ID"""
        return self._jobs_dict.get(job_id)

    def set_auth(self, auth: AuthState):
        """Update authentication state"""
        self.auth = auth
        self.auth_changed.emit()

    def show_toast(self, message: str, msg_type: str = "info"):
        """Show toast notification"""
        self.toast_message.emit(message, msg_type)
