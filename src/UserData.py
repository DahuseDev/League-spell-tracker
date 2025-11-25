import json
from pathlib import Path

class UserData:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init()
        return cls._instance

    def _init(self):
        self._path = Path("userdata.json")
        self._data = {}
        self._load()

    def _load(self):
        try:
            if self._path.exists():
                with self._path.open("r", encoding="utf-8") as f:
                    self._data = json.load(f) or {}
        except Exception as e:
            print("[USERDATA] Failed to load userdata:", e)
            self._data = {}

    def _save(self):
        try:
            with self._path.open("w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2)
        except Exception as e:
            print("[USERDATA] Failed to write userdata:", e)

    def get(self, key: str, default=None):
        return self._data.get(key, default)

    def get_int(self, key: str, default: int = 0) -> int:
        v = self.get(key, default)
        try:
            return int(v)
        except Exception:
            return default

    def set(self, key: str, value):
        self._data[key] = value
        self._save()