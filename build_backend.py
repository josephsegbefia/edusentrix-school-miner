from __future__ import annotations

import base64
import hashlib
import re
import zipfile
from collections.abc import Iterable
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PYPROJECT = ROOT / "pyproject.toml"
SRC_DIR = ROOT / "src"


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _extract_string(content: str, key: str) -> str:
    match = re.search(rf'^{re.escape(key)}\s*=\s*"([^"]+)"\s*$', content, re.MULTILINE)
    if not match:
        raise ValueError(f"Missing string value for {key!r} in pyproject.toml")
    return match.group(1)


def _extract_list(content: str, header: str, key: str) -> list[str]:
    section_match = re.search(
        rf"^\[{re.escape(header)}\]\s*(.*?)(?=^\[|\Z)", content, re.MULTILINE | re.DOTALL
    )
    if not section_match:
        return []
    section = section_match.group(1)
    list_match = re.search(
        rf"^{re.escape(key)}\s*=\s*\[(.*?)\]\s*$",
        section,
        re.MULTILINE | re.DOTALL,
    )
    if not list_match:
        return []
    return re.findall(r'"([^"]+)"', list_match.group(1))


def _project_metadata() -> dict[str, object]:
    content = _read_text(PYPROJECT)
    project_match = re.search(r"^\[project\]\s*(.*?)(?=^\[|\Z)", content, re.MULTILINE | re.DOTALL)
    if not project_match:
        raise ValueError("Missing [project] section in pyproject.toml")
    project = project_match.group(1)
    scripts = _extract_list(content, "project.scripts", "schoolminer")
    script_target = scripts[0] if scripts else _extract_string(content, "schoolminer")
    return {
        "name": _extract_string(project, "name"),
        "version": _extract_string(project, "version"),
        "description": _extract_string(project, "description"),
        "requires_python": _extract_string(project, "requires-python"),
        "dependencies": _extract_list(content, "project", "dependencies"),
        "script_target": script_target,
    }


def _dist_info_dir(metadata: dict[str, object]) -> str:
    return f"{str(metadata['name']).replace('-', '_')}-{metadata['version']}.dist-info"


def _wheel_name(metadata: dict[str, object]) -> str:
    dist = str(metadata["name"]).replace("-", "_")
    return f"{dist}-{metadata['version']}-py3-none-any.whl"


def _metadata_text(metadata: dict[str, object]) -> str:
    lines = [
        "Metadata-Version: 2.1",
        f"Name: {metadata['name']}",
        f"Version: {metadata['version']}",
        f"Summary: {metadata['description']}",
        f"Requires-Python: {metadata['requires_python']}",
    ]
    for dependency in metadata["dependencies"]:
        lines.append(f"Requires-Dist: {dependency}")
    lines.append("")
    return "\n".join(lines)


def _wheel_text() -> str:
    return (
        "Wheel-Version: 1.0\n"
        "Generator: local-build-backend\n"
        "Root-Is-Purelib: true\n"
        "Tag: py3-none-any\n"
    )


def _entry_points_text(metadata: dict[str, object]) -> str:
    return f"[console_scripts]\nschoolminer = {metadata['script_target']}\n"


def _iter_package_files() -> Iterable[tuple[Path, str]]:
    for path in SRC_DIR.rglob("*"):
        if path.is_file():
            yield path, path.relative_to(SRC_DIR).as_posix()


def _record_line(path: str, content: bytes) -> str:
    digest = hashlib.sha256(content).digest()
    encoded = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return f"{path},sha256={encoded},{len(content)}"


def _build_archive(
    wheel_directory: str,
    metadata_directory: str | None = None,
    editable: bool = False,
) -> str:
    metadata = _project_metadata()
    wheel_directory_path = Path(wheel_directory)
    wheel_directory_path.mkdir(parents=True, exist_ok=True)
    wheel_name = _wheel_name(metadata)
    wheel_path = wheel_directory_path / wheel_name
    dist_info = _dist_info_dir(metadata)
    record_rows: list[str] = []

    with zipfile.ZipFile(wheel_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        if editable:
            pth_name = f"{str(metadata['name']).replace('-', '_')}.pth"
            pth_content = f"{SRC_DIR.resolve()}\n".encode()
            archive.writestr(pth_name, pth_content)
            record_rows.append(_record_line(pth_name, pth_content))
        else:
            for source_path, archive_name in _iter_package_files():
                content = source_path.read_bytes()
                archive.writestr(archive_name, content)
                record_rows.append(_record_line(archive_name, content))

        metadata_name = f"{dist_info}/METADATA"
        metadata_content = _metadata_text(metadata).encode()
        archive.writestr(metadata_name, metadata_content)
        record_rows.append(_record_line(metadata_name, metadata_content))

        wheel_meta_name = f"{dist_info}/WHEEL"
        wheel_meta_content = _wheel_text().encode()
        archive.writestr(wheel_meta_name, wheel_meta_content)
        record_rows.append(_record_line(wheel_meta_name, wheel_meta_content))

        entry_points_name = f"{dist_info}/entry_points.txt"
        entry_points_content = _entry_points_text(metadata).encode()
        archive.writestr(entry_points_name, entry_points_content)
        record_rows.append(_record_line(entry_points_name, entry_points_content))

        if metadata_directory:
            metadata_dir = Path(metadata_directory)
            metadata_dir.mkdir(parents=True, exist_ok=True)
            (metadata_dir / "METADATA").write_text(_metadata_text(metadata), encoding="utf-8")
            (metadata_dir / "WHEEL").write_text(_wheel_text(), encoding="utf-8")
            (metadata_dir / "entry_points.txt").write_text(
                _entry_points_text(metadata), encoding="utf-8"
            )

        record_name = f"{dist_info}/RECORD"
        record_rows.append(f"{record_name},,")
        record_content = "\n".join(record_rows).encode()
        archive.writestr(record_name, record_content)

    return wheel_name


def build_wheel(
    wheel_directory: str,
    config_settings: dict[str, object] | None = None,
    metadata_directory: str | None = None,
) -> str:
    return _build_archive(wheel_directory, metadata_directory=metadata_directory, editable=False)


def build_editable(
    wheel_directory: str,
    config_settings: dict[str, object] | None = None,
    metadata_directory: str | None = None,
) -> str:
    return _build_archive(wheel_directory, metadata_directory=metadata_directory, editable=True)


def get_requires_for_build_wheel(
    config_settings: dict[str, object] | None = None,
) -> list[str]:
    return []


def get_requires_for_build_editable(
    config_settings: dict[str, object] | None = None,
) -> list[str]:
    return []


def prepare_metadata_for_build_wheel(
    metadata_directory: str,
    config_settings: dict[str, object] | None = None,
) -> str:
    metadata = _project_metadata()
    dist_info = _dist_info_dir(metadata)
    target_dir = Path(metadata_directory) / dist_info
    target_dir.mkdir(parents=True, exist_ok=True)
    (target_dir / "METADATA").write_text(_metadata_text(metadata), encoding="utf-8")
    (target_dir / "WHEEL").write_text(_wheel_text(), encoding="utf-8")
    (target_dir / "entry_points.txt").write_text(_entry_points_text(metadata), encoding="utf-8")
    return dist_info


def prepare_metadata_for_build_editable(
    metadata_directory: str,
    config_settings: dict[str, object] | None = None,
) -> str:
    return prepare_metadata_for_build_wheel(metadata_directory, config_settings)
