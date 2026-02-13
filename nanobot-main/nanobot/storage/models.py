from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from datetime import datetime
import json

@dataclass
class SessionModel:
    id: str
    key: str
    title: str
    created_at: int
    updated_at: int
    meta_json: str = "{}"

    @property
    def metadata(self) -> Dict[str, Any]:
        return json.loads(self.meta_json)

    @metadata.setter
    def metadata(self, value: Dict[str, Any]):
        self.meta_json = json.dumps(value)

@dataclass
class CronJobModel:
    id: str
    session_id: str
    name: str
    schedule_json: str
    payload_json: str
    next_run_at: Optional[int]
    enabled: bool
    created_at: int
    updated_at: int

    @property
    def schedule(self) -> Dict[str, Any]:
        return json.loads(self.schedule_json)

    @property
    def payload(self) -> Dict[str, Any]:
        return json.loads(self.payload_json)
