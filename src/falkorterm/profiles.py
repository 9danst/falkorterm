from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Profile:
    name: str
    host: str = "localhost"
    port: int = 6379
    password: str | None = None
    graph: str = "falkorterm"


def default_profiles_path() -> Path:
    override = os.environ.get("FALKOR_PROFILES_PATH")
    if override:
        return Path(override)
    xdg = os.environ.get("XDG_DATA_HOME")
    if xdg:
        return Path(xdg) / "falkorterm" / "profiles.json"
    return Path.home() / ".local" / "share" / "falkorterm" / "profiles.json"


class ProfileStore:
    """Persistent named connection profiles."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or default_profiles_path()

    def list(self) -> list[Profile]:
        data = self._read()
        profiles: list[Profile] = []
        for item in data.get("profiles", []):
            if not isinstance(item, dict) or "name" not in item:
                continue
            profiles.append(
                Profile(
                    name=str(item["name"]),
                    host=str(item.get("host", "localhost")),
                    port=int(item.get("port", 6379)),
                    password=item.get("password") or None,
                    graph=str(item.get("graph", "falkorterm")),
                )
            )
        return sorted(profiles, key=lambda p: p.name.lower())

    def get(self, name: str) -> Profile | None:
        for profile in self.list():
            if profile.name == name:
                return profile
        return None

    def save(self, profile: Profile) -> None:
        profiles = [p for p in self.list() if p.name != profile.name]
        profiles.append(profile)
        profiles.sort(key=lambda p: p.name.lower())
        self._write(
            {
                "profiles": [
                    {
                        "name": p.name,
                        "host": p.host,
                        "port": p.port,
                        "password": p.password,
                        "graph": p.graph,
                    }
                    for p in profiles
                ]
            }
        )

    def delete(self, name: str) -> None:
        profiles = [p for p in self.list() if p.name != name]
        self._write(
            {
                "profiles": [
                    {
                        "name": p.name,
                        "host": p.host,
                        "port": p.port,
                        "password": p.password,
                        "graph": p.graph,
                    }
                    for p in profiles
                ]
            }
        )

    def _read(self) -> dict:
        if not self.path.exists():
            return {"profiles": []}
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {"profiles": []}
        if not isinstance(raw, dict):
            return {"profiles": []}
        return raw

    def _write(self, data: dict) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.path.with_suffix(self.path.suffix + ".tmp")
            tmp.write_text(
                json.dumps(data, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            tmp.replace(self.path)
        except OSError:
            return
