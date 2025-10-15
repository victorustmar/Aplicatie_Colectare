# app/utils/rates.py
# Single source pentru denumirile tipurilor de baterii și ordinea lor.
# Nu mai conține tarife.

from typing import Dict, List, Tuple

# Cheie -> etichetă în română (conform șablonului din tabel)
LABELS: Dict[str, str] = {
    # Baterii portabile – categoria 1
    "1a": "Alcaline",
    "1b": "Litiu",
    "1c": "Zinc carbon",
    "1d": "Zinc aer",
    "1e": "Oxid de mercur (HgO)",
    "1f": "Oxid de argint (Ag₂O)",
    "1g": "Ansamblu de baterii",
    "1h": "Altele",

    # Baterii portabile – categoria 2
    "2a": "Nichel Cadmiu (NiCd)",
    "2b": "Plumb",
    "2c": "Nichel metal hidrură (NiMH)",
    "2d": "Litiu ion",
    "2e": "Litiu polimer",
    "2f": "Altele",

    # Baterii auto – categoria 3
    "3a": "Plumb acid",
    "3b": "Nichel cadmiu (NiCd)",
    "3c": "Altele",

    # Baterii industriale – categoria 4
    "4a": "Plumb acid",
    "4b": "Nichel cadmiu (NiCd)",
    "4c": "Altele",
}

# Grupare pentru UI/factură (titlu + ordinea rândurilor)
SECTIONS: List[Tuple[str, str, List[str]]] = [
    (
        "PORTABLE_12",
        "Baterii portabile (categoriile 1 și 2)",
        ["1a","1b","1c","1d","1e","1f","1g","1h","2a","2b","2c","2d","2e","2f"],
    ),
    (
        "AUTO_3",
        "Baterii auto (categoria 3)",
        ["3a","3b","3c"],
    ),
    (
        "INDUSTRIAL_4",
        "Baterii industriale (categoria 4)",
        ["4a","4b","4c"],
    ),
]

# Listă liniară utilă dacă vrei doar ordinea cheilor
ALL_KEYS: List[str] = [k for _, _, keys in SECTIONS for k in keys]
