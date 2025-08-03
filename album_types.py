from pydantic import BaseModel
from typing import Optional, Set

class AlbumRow(BaseModel):
    title: str
    ids: Set[Optional[str]] = set()
    years: Set[Optional[str]] = set()
    owned: bool = False
