"""Compare frontend TS interfaces with the FastAPI/Pydantic schemas."""

from __future__ import annotations

import inspect
import json
import pathlib
import re

from pydantic import BaseModel

import app.schemas.academic as academic
import app.schemas.ai as ai
import app.schemas.auth as auth
import app.schemas.course as course
import app.schemas.dashboard as dashboard
import app.schemas.document as document
import app.schemas.study as study

MODULES = [academic, ai, auth, course, dashboard, document, study]

MODELS: dict[str, type[BaseModel]] = {}
for module in MODULES:
    for name, obj in vars(module).items():
        if inspect.isclass(obj) and issubclass(obj, BaseModel) and obj is not BaseModel:
            MODELS.setdefault(name, obj)


def snake(name: str) -> str:
    return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()


def ts_interfaces(path: pathlib.Path) -> dict[str, dict[str, str]]:
    text = path.read_text(encoding="utf-8")
    out: dict[str, dict[str, str]] = {}
    pattern = re.compile(r"export interface (\w+) \{(.*?)\n\}", re.S)
    for match in pattern.finditer(text):
        name, body = match.group(1), match.group(2)
        fields: dict[str, str] = {}
        for line in body.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("//") or stripped.startswith("/*") or stripped.startswith("*"):
                continue
            field = re.match(r"(\w+)(\?)?:\s*(.+)$", stripped)
            if field:
                fields[field.group(1)] = field.group(3).rstrip(",")
        out[name] = fields
    return out


def main() -> None:
    ts_path = pathlib.Path(__file__).resolve().parent.parent.parent / "frontend" / "src" / "lib" / "types.ts"
    interfaces = ts_interfaces(ts_path)
    problems = 0
    for ts_name, ts_fields in interfaces.items():
        model = MODELS.get(ts_name)
        if model is None:
            print(f"[?] TS interface {ts_name} has no matching schema")
            continue
        props = model.model_json_schema().get("properties", {})
        py_fields = {snake(key): value for key, value in props.items()}
        missing = sorted(set(py_fields) - set(ts_fields))
        extra = sorted(set(ts_fields) - set(py_fields))
        if missing or extra:
            problems += 1
            print(f"[!] {ts_name}")
            if missing:
                print(f"    missing in TS : {missing}")
            if extra:
                print(f"    extra in TS   : {extra}")
    print(f"\nchecked {len(interfaces)} interfaces, {problems} with differences")


if __name__ == "__main__":
    main()
