"""Pomocné funkce pro prezentační vrstvu."""
from pathlib import Path
from typing import Optional, Union
from uuid import UUID

from fastapi.templating import Jinja2Templates


def resolve_product_image(code: str, name: str = "") -> str:
    """Namapuje SKU kód nebo název hračky na ilustrační obrázek v /static/img/toys/."""
    upper_code = (code or "").upper()
    lower_name = (name or "").lower()

    exact_code_map = {
        "KAC-001": "spinning_top.svg",
        "KAC-002": "duck.svg",
        "AUT-003": "firetruck.svg",
        "HLV-001": "hedgehog_cage.svg",
        "HLV-002": "puzzle_tower.svg",
        "HLV-003": "puzzle_board.svg",
    }
    if upper_code in exact_code_map:
        return f"/static/img/toys/{exact_code_map[upper_code]}"

    prefix_map = {
        "VLK": "train.svg",
        "KON": "rocking_horse.svg",
        "KOS": "blocks.svg",
        "AUT": "car.svg",
        "DOM": "domino.svg",
        "PUZ": "puzzle_board.svg",
        "LET": "airplane.svg",
        "LOD": "sailboat.svg",
        "MECH": "woodpecker.svg",
        "HUD": "xylophone.svg",
        "LOU": "theater.svg",
    }
    prefix = upper_code.split("-")[0] if "-" in upper_code else upper_code
    if prefix in prefix_map:
        return f"/static/img/toys/{prefix_map[prefix]}"

    keyword_map = [
        (("vláč", "vlák", "lokomotiv"), "train.svg"),
        (("kačer", "kachn"), "duck.svg"),
        (("káč",), "spinning_top.svg"),
        (("koník", "kůň", "houpací"), "rocking_horse.svg"),
        (("kostk", "staveb"), "blocks.svg"),
        (("hasič",), "firetruck.svg"),
        (("aut", "náklaď", "voz"), "car.svg"),
        (("ježek", "klec"), "hedgehog_cage.svg"),
        (("věž", "krouž"), "puzzle_tower.svg"),
        (("domino",), "domino.svg"),
        (("puzzle", "tangram", "vklád"), "puzzle_board.svg"),
        (("letad", "dvouploš"), "airplane.svg"),
        (("loď", "plachetn"), "sailboat.svg"),
        (("datel", "slepič", "klap"), "woodpecker.svg"),
        (("xylofon", "rumba", "hudeb"), "xylophone.svg"),
        (("loutk", "divad"), "theater.svg"),
    ]
    for keywords, filename in keyword_map:
        if any(kw in lower_name for kw in keywords):
            return f"/static/img/toys/{filename}"

    return "/static/img/toys/default_toy.svg"


def get_templates(templates_dir: Optional[Path] = None) -> Jinja2Templates:
    """Vytvoří instanci Jinja2Templates se sdílenými globálními pomocníky (např. náhledy hraček)."""
    target_dir = templates_dir or (Path(__file__).resolve().parent / "templates")
    templates = Jinja2Templates(directory=str(target_dir))
    templates.env.globals["toy_image_url"] = resolve_product_image
    return templates


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

