"""Google Drive OAuth, duplicate checking and upload.

Scope
-----
The default is `drive.file`, which lets this app see and manage only the files
it created. That is the least privilege that still supports the duplicate
check, because the files being checked for are its own previous uploads.

If your destination folder rejects an upload under `drive.file`, the folder
was not created by this app and Google will not let a `drive.file` client
write into it. The fix is to let this tool create its own subfolder, or — as
a last resort — widen `GOOGLE_DRIVE_SCOPES` to the full drive scope, which
grants read/write over the entire Drive. Prefer the subfolder.

Duplicates
----------
Every upload carries `appProperties.runKey`, a deterministic key of
report slug + calendar date. The check queries that key first, then falls
back to a filename-prefix match so a file placed by hand still counts.
"""

from __future__ import annotations

import mimetypes
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from .logging_utils import redact

DEFAULT_SCOPES = ["https://www.googleapis.com/auth/drive.file"]

CATEGORY_AUTH_FAILED = "drive_auth_failed"
CATEGORY_UPLOAD_FAILED = "drive_upload_failed"
CATEGORY_LOOKUP_FAILED = "drive_lookup_failed"
CATEGORY_MISSING_CREDENTIALS = "drive_credentials_missing"

_MIME_BY_EXTENSION = {
    "csv": "text/csv",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "xls": "application/vnd.ms-excel",
    "pdf": "application/pdf",
}


class DriveError(Exception):
    def __init__(self, category: str, detail: str = ""):
        super().__init__(f"{category}: {detail}" if detail else category)
        self.category = category
        self.detail = detail


@dataclass
class ExistingFile:
    file_id: str
    name: str


def guess_mime(path: Path) -> str:
    extension = path.suffix.lstrip(".").lower()
    if extension in _MIME_BY_EXTENSION:
        return _MIME_BY_EXTENSION[extension]
    return mimetypes.guess_type(path.name)[0] or "application/octet-stream"


def _escape(value: str) -> str:
    """Escape a value for a Drive query string literal."""
    return value.replace("\\", "\\\\").replace("'", "\\'")


class DriveUploader:
    """Thin wrapper over the Drive v3 files API.

    Constructed lazily: `--dry-run` never builds one, so a dry run needs no
    Google credentials at all.
    """

    def __init__(self, cfg, logger):
        self.cfg = cfg
        self.log = logger
        self._service = None

    # -- auth --------------------------------------------------------------

    def _credentials(self):
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow

        scopes = self.cfg.google_scopes or DEFAULT_SCOPES
        token_file = Path(self.cfg.google_token_file)
        creds_file = Path(self.cfg.google_credentials_file)

        creds = None
        if token_file.exists():
            try:
                creds = Credentials.from_authorized_user_file(str(token_file), scopes)
            except ValueError:
                # Usually a scope change since the token was written.
                self.log.warning("Stored token does not match the configured "
                                 "scopes; re-authorisation required")
                creds = None

        if creds and creds.valid:
            return creds

        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                self._write_token(token_file, creds)
                return creds
            except Exception:
                self.log.warning("Token refresh failed; re-authorisation required")

        if not creds_file.exists():
            raise DriveError(
                CATEGORY_MISSING_CREDENTIALS,
                "OAuth client file not found; download it from Google Cloud "
                "Console and point GOOGLE_CREDENTIALS_FILE at it")

        # Opens a browser for consent. Interactive by design — an unattended
        # scheduled run reuses the token written here.
        flow = InstalledAppFlow.from_client_secrets_file(str(creds_file), scopes)
        creds = flow.run_local_server(port=0)
        self._write_token(token_file, creds)
        return creds

    def _write_token(self, token_file: Path, creds) -> None:
        token_file.parent.mkdir(parents=True, exist_ok=True)
        token_file.write_text(creds.to_json(), encoding="utf-8")
        try:
            token_file.chmod(0o600)
        except OSError:
            pass
        self.log.info("Stored Drive token outside the repository")

    @property
    def service(self):
        if self._service is None:
            from googleapiclient.discovery import build
            try:
                self._service = build("drive", "v3",
                                      credentials=self._credentials(),
                                      cache_discovery=False)
            except DriveError:
                raise
            except Exception as exc:
                raise DriveError(CATEGORY_AUTH_FAILED,
                                 type(exc).__name__) from None
        return self._service

    # -- duplicate check ---------------------------------------------------

    def find_existing(self, folder_id: str, run_key: str,
                      filename_prefix: str) -> Optional[ExistingFile]:
        """Return a matching file already in the folder, if any.

        Matches on the deterministic run key first. The filename-prefix
        fallback catches a file uploaded before appProperties existed, or one
        a person dropped in by hand.
        """
        by_run_key = (
            f"'{_escape(folder_id)}' in parents and trashed = false and "
            f"appProperties has {{ key='runKey' and value='{_escape(run_key)}' }}")
        by_name = (
            f"'{_escape(folder_id)}' in parents and trashed = false and "
            f"name contains '{_escape(filename_prefix)}'")

        for query, exact_prefix in ((by_run_key, False), (by_name, True)):
            try:
                response = self.service.files().list(
                    q=query,
                    spaces="drive",
                    fields="files(id, name)",
                    pageSize=10,
                    supportsAllDrives=True,
                    includeItemsFromAllDrives=True,
                ).execute()
            except DriveError:
                raise
            except Exception as exc:
                raise DriveError(CATEGORY_LOOKUP_FAILED, type(exc).__name__) from None

            for item in response.get("files", []):
                # `name contains` is a substring match anywhere in the name,
                # so the filename query confirms the prefix itself.
                if exact_prefix and not item.get("name", "").startswith(filename_prefix):
                    continue
                return ExistingFile(item["id"], item.get("name", ""))
        return None

    # -- upload ------------------------------------------------------------

    def upload(self, path: Path, folder_id: str, run_key: str,
               report_slug: str) -> str:
        """Upload a validated file. Returns the Drive file id."""
        from googleapiclient.http import MediaFileUpload

        path = Path(path)
        metadata: dict[str, Any] = {
            "name": path.name,
            "parents": [folder_id],
            "appProperties": {
                "runKey": run_key,
                "reportSlug": report_slug,
                "source": "extendedreach-report-sync-poc",
            },
        }
        media = MediaFileUpload(str(path), mimetype=guess_mime(path),
                                resumable=True)
        try:
            created = self.service.files().create(
                body=metadata,
                media_body=media,
                fields="id",
                supportsAllDrives=True,
            ).execute()
        except DriveError:
            raise
        except Exception as exc:
            detail = type(exc).__name__
            if "HttpError" in detail:
                detail += (" — if this is a 403 on the folder, the drive.file "
                           "scope cannot write to a folder this app did not "
                           "create; see the module docstring")
            raise DriveError(CATEGORY_UPLOAD_FAILED, redact(detail)) from None

        file_id = created.get("id", "")
        self.log.info("Uploaded to Drive (file id %s)", file_id)
        return file_id
