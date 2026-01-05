from __future__ import annotations

import json
import os
import random
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

from qtpy import QtCore

from models import (
    AppState,
    AuthState,
    ClipItem,
    ClipStatus,
    DownloadState,
    ExportMode,
    ImportState,
    Phase,
    ProjectState,
    ProjectStatus,
    RenderState,
    ToastMessage,
)
from services.instagram_service import InstagramService


@dataclass
class ImportLinkChanged:
    link: str


@dataclass
class FetchHighlight:
    pass


@dataclass
class ConnectWithSessionToken:
    session_id: str


@dataclass
class DisconnectSession:
    pass


@dataclass
class StartDownload:
    pass


@dataclass
class PauseDownload:
    item_id: Optional[str] = None


@dataclass
class ResumeDownload:
    item_id: Optional[str] = None


@dataclass
class RetryFailed:
    pass


@dataclass
class ReorderClips:
    new_order: List[str]


@dataclass
class ToggleSelectClip:
    clip_id: str


@dataclass
class SetSelectedClips:
    clip_ids: List[str]


@dataclass
class SetExportMode:
    mode: ExportMode


@dataclass
class UpdateVideoSetting:
    key: str
    value: object


@dataclass
class PreviewSettings:
    pass


@dataclass
class SaveSettings:
    pass


@dataclass
class BuildVideo:
    pass


@dataclass
class Export:
    pass


@dataclass
class OpenProjectFolder:
    pass


@dataclass
class CreateProject:
    title: str = "Untitled Project"


@dataclass
class SelectProject:
    project_id: str


@dataclass
class ClearSelection:
    pass


@dataclass
class DeleteProject:
    pass


@dataclass
class NavigatePhase:
    phase: Phase


@dataclass
class RemoveClip:
    clip_id: str


@dataclass
class SetCoverClip:
    clip_id: str


@dataclass
class MarkExportSeparately:
    clip_ids: List[str]


@dataclass
class AddToast:
    message: str
    level: str = "info"


class Store(QtCore.QObject):
    stateChanged = QtCore.Signal(object)

    def __init__(self):
        super().__init__()
        self._state = AppState()
        self._instagram_service = InstagramService()
        self._auth_thread: Optional[QtCore.QThread] = None
        self._download_timer = QtCore.QTimer()
        self._download_timer.setInterval(250)
        self._download_timer.timeout.connect(self._tick_download)
        self._render_timer = QtCore.QTimer()
        self._render_timer.setInterval(200)
        self._render_timer.timeout.connect(self._tick_render)
        self._preview_timer = QtCore.QTimer()
        self._preview_timer.setSingleShot(True)
        self._preview_timer.timeout.connect(self._finish_preview)
        self._load_session()

    def get_state(self) -> AppState:
        return self._state

    def dispatch(self, action: object) -> None:
        if isinstance(action, CreateProject):
            self._create_project(action.title)
        elif isinstance(action, SelectProject):
            self._state.current_project_id = action.project_id
            self._emit()
        elif isinstance(action, ClearSelection):
            self._state.current_project_id = None
            self._emit()
        elif isinstance(action, NavigatePhase):
            self._navigate_phase(action.phase)
        elif isinstance(action, ImportLinkChanged):
            project = self._current_project()
            if project:
                project.link = action.link
                project.import_state = ImportState.EMPTY
                project.last_error = ""
                self._emit()
        elif isinstance(action, ConnectWithSessionToken):
            self._connect_with_session_token(action.session_id)
        elif isinstance(action, DisconnectSession):
            self._disconnect_session()
        elif isinstance(action, FetchHighlight):
            self._fetch_highlight_stub()
        elif isinstance(action, StartDownload):
            self._start_download()
        elif isinstance(action, PauseDownload):
            self._pause_download(action.item_id)
        elif isinstance(action, ResumeDownload):
            self._resume_download(action.item_id)
        elif isinstance(action, RetryFailed):
            self._retry_failed()
        elif isinstance(action, ReorderClips):
            self._reorder_clips(action.new_order)
        elif isinstance(action, ToggleSelectClip):
            self._toggle_select_clip(action.clip_id)
        elif isinstance(action, SetSelectedClips):
            self._set_selected_clips(action.clip_ids)
        elif isinstance(action, SetExportMode):
            project = self._current_project()
            if project:
                project.settings.export_mode = action.mode
                project.settings_dirty = True
                self._emit()
        elif isinstance(action, UpdateVideoSetting):
            project = self._current_project()
            if project and hasattr(project.settings, action.key):
                setattr(project.settings, action.key, action.value)
                project.settings_dirty = True
                self._emit()
        elif isinstance(action, PreviewSettings):
            self._preview_settings()
        elif isinstance(action, SaveSettings):
            project = self._current_project()
            if project:
                project.settings_dirty = False
                self._add_toast("Settings saved", "success")
        elif isinstance(action, BuildVideo):
            self._navigate_phase(Phase.SETTINGS)
        elif isinstance(action, Export):
            self._start_export()
        elif isinstance(action, OpenProjectFolder):
            self._add_toast("Project folder opened", "info")
        elif isinstance(action, RemoveClip):
            self._remove_clip(action.clip_id)
        elif isinstance(action, SetCoverClip):
            self._set_cover(action.clip_id)
        elif isinstance(action, MarkExportSeparately):
            self._mark_export_separately(action.clip_ids)
        elif isinstance(action, AddToast):
            self._add_toast(action.message, action.level)
        elif isinstance(action, DeleteProject):
            self._delete_project()

    def _emit(self) -> None:
        self.stateChanged.emit(self._state)

    def _current_project(self) -> Optional[ProjectState]:
        project_id = self._state.current_project_id
        if project_id:
            return self._state.projects.get(project_id)
        return None

    def _create_project(self, title: str) -> None:
        project_id = str(uuid.uuid4())
        project = ProjectState(id=project_id, title=title)
        project.last_updated = self._now_label()
        self._state.projects[project_id] = project
        self._state.current_project_id = project_id
        self._state.phase = Phase.IMPORT
        self._emit()

    def _navigate_phase(self, phase: Phase) -> None:
        project = self._current_project()
        if not project:
            return
        if phase == Phase.EXPORT and not project.download_done:
            return
        if phase == Phase.SETTINGS and not project.clips:
            return
        if phase == Phase.ARRANGE and project.download_state == DownloadState.IDLE:
            return
        self._state.phase = phase
        self._emit()

    def _fetch_highlight_stub(self) -> None:
        project = self._current_project()
        if not project:
            self._create_project("New Project")
            project = self._current_project()
        if not project:
            return
        if self._state.auth_state != AuthState.CONNECTED:
            project.import_state = ImportState.ERROR
            project.last_error = "Connect your session to fetch highlights."
            self._emit()
            return
        if not project.link.strip():
            project.import_state = ImportState.ERROR
            project.last_error = "Please paste a highlight link."
            self._emit()
            return
        project.import_state = ImportState.LOADING
        project.last_error = ""
        self._emit()

        def finish():
            if "error" in project.link:
                project.import_state = ImportState.ERROR
                project.last_error = "We couldn't fetch that link. Please check and try again."
                self._emit()
                return
            item_count = random.choice([12, 16, 18, 24])
            project.title = "Summer Highlights"
            project.item_count = item_count
            project.import_state = ImportState.READY
            project.status = ProjectStatus.DRAFT
            project.last_updated = self._now_label()
            project.clips = self._build_clip_items(item_count)
            project.settings_dirty = False
            project.download_state = DownloadState.IDLE
            project.download_done = False
            project.download_progress = 0.0
            self._add_toast("Highlight found", "success")
            self._emit()

        QtCore.QTimer.singleShot(1200, finish)

    def _connect_with_session_token(self, session_id: str) -> None:
        if self._state.auth_state == AuthState.CONNECTING:
            return
        token = session_id.strip()
        if not token:
            self._state.auth_state = AuthState.ERROR
            self._state.auth_error = "Session token is required."
            self._emit()
            return
        self._state.auth_state = AuthState.CONNECTING
        self._state.auth_error = ""
        self._emit()

        worker = InstagramConnectWorker(token, self._instagram_service)
        thread = QtCore.QThread()
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(self._on_auth_finished)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        self._auth_thread = thread
        thread.start()

    def _on_auth_finished(self, success: bool, message: str, session_id: Optional[str]) -> None:
        if success and session_id:
            self._state.auth_state = AuthState.CONNECTED
            self._state.session_id = session_id
            self._state.auth_error = ""
            self._save_session(session_id)
            self._add_toast("Session connected", "success")
        else:
            self._state.auth_state = AuthState.ERROR
            self._state.auth_error = message
        self._emit()

    def _disconnect_session(self) -> None:
        self._state.auth_state = AuthState.DISCONNECTED
        self._state.session_id = None
        self._state.auth_error = ""
        self._delete_session_file()
        self._emit()

    def _build_clip_items(self, count: int) -> List[ClipItem]:
        items: List[ClipItem] = []
        for index in range(count):
            media_type = "video" if index % 3 != 0 else "photo"
            label = f"Clip {index + 1:02d}"
            items.append(
                ClipItem(
                    id=str(uuid.uuid4()),
                    label=label,
                    media_type=media_type,
                    duration=6 if media_type == "video" else None,
                    status=ClipStatus.WAITING,
                    progress=0,
                )
            )
        return items

    def _start_download(self) -> None:
        project = self._current_project()
        if not project:
            return
        if not project.clips:
            project.last_error = "No items to download yet."
            self._emit()
            return
        project.download_state = DownloadState.DOWNLOADING
        project.status = ProjectStatus.DOWNLOADING
        project.last_error = ""
        project.download_done = False
        self._state.phase = Phase.DOWNLOAD
        for clip in project.clips:
            if clip.status in (ClipStatus.FAILED, ClipStatus.PAUSED):
                clip.status = ClipStatus.WAITING
        if not self._download_timer.isActive():
            self._download_timer.start()
        self._emit()

    def _pause_download(self, item_id: Optional[str]) -> None:
        project = self._current_project()
        if not project:
            return
        if item_id is None:
            project.download_state = DownloadState.PAUSED
            for clip in project.clips:
                if clip.status == ClipStatus.DOWNLOADING:
                    clip.status = ClipStatus.PAUSED
            self._download_timer.stop()
        else:
            for clip in project.clips:
                if clip.id == item_id and clip.status in (ClipStatus.WAITING, ClipStatus.DOWNLOADING):
                    clip.status = ClipStatus.PAUSED
        self._emit()

    def _resume_download(self, item_id: Optional[str]) -> None:
        project = self._current_project()
        if not project:
            return
        if item_id is None:
            project.download_state = DownloadState.DOWNLOADING
            for clip in project.clips:
                if clip.status == ClipStatus.PAUSED:
                    clip.status = ClipStatus.WAITING
            if not self._download_timer.isActive():
                self._download_timer.start()
        else:
            for clip in project.clips:
                if clip.id == item_id and clip.status in (ClipStatus.PAUSED, ClipStatus.FAILED):
                    was_failed = clip.status == ClipStatus.FAILED
                    clip.status = ClipStatus.WAITING
                    if was_failed:
                        clip.progress = 0
            if project.download_state == DownloadState.PAUSED:
                project.download_state = DownloadState.DOWNLOADING
                if not self._download_timer.isActive():
                    self._download_timer.start()
        self._emit()

    def _retry_failed(self) -> None:
        project = self._current_project()
        if not project:
            return
        for clip in project.clips:
            if clip.status == ClipStatus.FAILED:
                clip.status = ClipStatus.WAITING
                clip.progress = 0
        project.download_state = DownloadState.DOWNLOADING
        if not self._download_timer.isActive():
            self._download_timer.start()
        self._emit()

    def _tick_download(self) -> None:
        project = self._current_project()
        if not project or project.download_state != DownloadState.DOWNLOADING:
            return
        active = [
            clip for clip in project.clips
            if clip.status in (ClipStatus.WAITING, ClipStatus.DOWNLOADING)
        ]
        if not active:
            paused = [clip for clip in project.clips if clip.status == ClipStatus.PAUSED]
            if paused:
                project.download_state = DownloadState.PAUSED
                self._download_timer.stop()
                self._emit()
                return
            failed = [clip for clip in project.clips if clip.status == ClipStatus.FAILED]
            project.download_state = DownloadState.PARTIAL_FAILED if failed else DownloadState.COMPLETED
            project.download_done = not failed
            project.status = ProjectStatus.READY if project.download_done else ProjectStatus.ERROR
            project.last_updated = self._now_label()
            self._download_timer.stop()
            self._emit()
            return

        current = next((clip for clip in active if clip.status == ClipStatus.DOWNLOADING), None)
        if not current:
            current = active[0]
            current.status = ClipStatus.DOWNLOADING

        current.progress += random.randint(6, 14)
        if "fail" in project.link and current.progress > 65 and random.random() < 0.15:
            current.status = ClipStatus.FAILED
        elif current.progress >= 100:
            current.progress = 100
            current.status = ClipStatus.COMPLETED

        total = len(project.clips)
        progress_sum = sum(clip.progress for clip in project.clips)
        project.download_progress = progress_sum / max(total, 1)
        completed = len([clip for clip in project.clips if clip.status == ClipStatus.COMPLETED])
        project.storage_used_gb = round(0.08 * completed, 2)
        self._emit()

    def _reorder_clips(self, new_order: List[str]) -> None:
        project = self._current_project()
        if not project:
            return
        lookup = {clip.id: clip for clip in project.clips}
        project.clips = [lookup[clip_id] for clip_id in new_order if clip_id in lookup]
        self._emit()

    def _toggle_select_clip(self, clip_id: str) -> None:
        project = self._current_project()
        if not project:
            return
        for clip in project.clips:
            if clip.id == clip_id:
                clip.selected = not clip.selected
        self._emit()

    def _set_selected_clips(self, clip_ids: List[str]) -> None:
        project = self._current_project()
        if not project:
            return
        for clip in project.clips:
            clip.selected = clip.id in clip_ids
        self._emit()

    def _remove_clip(self, clip_id: str) -> None:
        project = self._current_project()
        if not project:
            return
        project.clips = [clip for clip in project.clips if clip.id != clip_id]
        project.item_count = len(project.clips)
        project.download_done = project.download_done and bool(project.clips)
        self._emit()

    def _set_cover(self, clip_id: str) -> None:
        project = self._current_project()
        if not project:
            return
        for clip in project.clips:
            if clip.id == clip_id:
                project.cover_path = clip.thumbnail_path
                project.last_updated = self._now_label()
                break
        self._emit()

    def _mark_export_separately(self, clip_ids: List[str]) -> None:
        project = self._current_project()
        if not project:
            return
        for clip in project.clips:
            if clip.id in clip_ids:
                clip.export_separately = True
        self._emit()

    def _delete_project(self) -> None:
        project_id = self._state.current_project_id
        if not project_id:
            return
        self._state.projects.pop(project_id, None)
        self._state.current_project_id = next(iter(self._state.projects), None)
        self._state.phase = Phase.IMPORT
        self._emit()

    def _preview_settings(self) -> None:
        project = self._current_project()
        if not project:
            return
        project.preview_state = "rendering"
        self._emit()
        if self._preview_timer.isActive():
            self._preview_timer.stop()
        self._preview_timer.start(1100)

    def _finish_preview(self) -> None:
        project = self._current_project()
        if not project:
            return
        project.preview_state = "ready"
        self._emit()

    def _start_export(self) -> None:
        project = self._current_project()
        if not project:
            return
        if not project.clips:
            project.render_state = RenderState.ERROR
            project.last_error = "No clips available for export."
            self._emit()
            return
        project.render_state = RenderState.RENDERING
        project.render_progress = 0.0
        project.last_error = ""
        self._state.phase = Phase.EXPORT
        if not self._render_timer.isActive():
            self._render_timer.start()
        self._emit()

    def _tick_render(self) -> None:
        project = self._current_project()
        if not project or project.render_state != RenderState.RENDERING:
            return
        project.render_progress += random.uniform(4.0, 9.0)
        if project.render_progress >= 100:
            project.render_progress = 100
            project.render_state = RenderState.DONE
            project.status = ProjectStatus.EXPORTED
            project.last_updated = self._now_label()
            self._render_timer.stop()
        self._emit()

    def _add_toast(self, message: str, level: str = "info") -> None:
        toast = ToastMessage(id=str(uuid.uuid4()), message=message, level=level)
        self._state.ui.toasts.append(toast)
        self._emit()

        def clear_toast():
            self._state.ui.toasts = [t for t in self._state.ui.toasts if t.id != toast.id]
            self._emit()

        QtCore.QTimer.singleShot(3200, clear_toast)

    def _load_session(self) -> None:
        path = self._session_path()
        if not os.path.exists(path):
            return
        try:
            with open(path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
            session_id = data.get("session_id")
            if session_id:
                self._state.session_id = session_id
                self._state.auth_state = AuthState.CONNECTED
        except Exception:
            self._state.auth_state = AuthState.DISCONNECTED

    def _save_session(self, session_id: str) -> None:
        path = self._session_path()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        payload = {"session_id": session_id, "saved_at": datetime.now().isoformat()}
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle)

    def _delete_session_file(self) -> None:
        path = self._session_path()
        if os.path.exists(path):
            try:
                os.remove(path)
            except OSError:
                pass

    @staticmethod
    def _session_path() -> str:
        return os.path.expanduser("~/.stellar/session.json")

    @staticmethod
    def _now_label() -> str:
        return datetime.now().strftime("%b %d, %H:%M")


class InstagramConnectWorker(QtCore.QObject):
    finished = QtCore.Signal(bool, str, object)

    def __init__(self, session_id: str, service: InstagramService):
        super().__init__()
        self._session_id = session_id
        self._service = service

    @QtCore.Slot()
    def run(self) -> None:
        try:
            session_id = self._service.connect_with_session_id(self._session_id)
            self.finished.emit(True, "Connected", session_id)
        except Exception as exc:
            self.finished.emit(False, str(exc), None)
