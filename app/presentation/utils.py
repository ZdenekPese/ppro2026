"""Pomocné funkce pro prezentační vrstvu."""
from typing import Optional, Union
from uuid import UUID


def parse_optional_uuid(val: Optional[Union[UUID, str]]) -> Optional[UUID]:
    """Bezpečně převede vstupní řetězec nebo UUID na UUID, přičemž prázdné řetězce ošetří jako None."""
    if val is None:
        return None
    if isinstance(val, UUID):
        return val
    if isinstance(val, str):
        cleaned = val.strip()
        if not cleaned:
            return None
        try:
            return UUID(cleaned)
        except (ValueError, AttributeError):
            return None
    return None
