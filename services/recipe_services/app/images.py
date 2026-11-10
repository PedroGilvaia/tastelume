import re
import uuid
from pathlib import Path

from .config import settings

_NAME_RE = re.compile(r"^[a-f0-9]{32}\.(jpg|png|webp)$")
MEDIA_TYPES = {"jpg": "image/jpeg", "png": "image/png", "webp": "image/webp"}


def detect_extension(data: bytes) -> str | None:
    """Identifica o tipo pelo conteúdo (não confia no Content-Type nem no nome enviados)."""
    if data.startswith(b"\xff\xd8\xff"):
        return "jpg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    return None


def save_image(data: bytes, ext: str) -> str:
    directory = Path(settings.image_dir)
    directory.mkdir(parents=True, exist_ok=True)
    name = f"{uuid.uuid4().hex}.{ext}"  # nome gerado pelo servidor
    (directory / name).write_bytes(data)
    return name


def resolve_image(name: str) -> Path | None:
    if not _NAME_RE.match(name):
        return None
    path = Path(settings.image_dir) / name
    return path if path.is_file() else None


def delete_image(name: str | None) -> None:
    if name and (path := resolve_image(name)):
        path.unlink(missing_ok=True)
