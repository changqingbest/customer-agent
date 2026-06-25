from copy import deepcopy


class SessionStore:
    def __init__(self) -> None:
        self._lead_fields: dict[str, dict] = {}

    def merge(self, session_id: str, new_fields: dict) -> dict:
        current = deepcopy(self._lead_fields.get(session_id, {}))
        for key, value in new_fields.items():
            if value not in (None, "", False):
                current[key] = value
            elif key not in current:
                current[key] = value
        self._lead_fields[session_id] = current
        return deepcopy(current)
