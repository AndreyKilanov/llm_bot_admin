from enum import StrEnum


class LoopMode(StrEnum):
    """Режимы зацикливания воспроизведения."""
    
    NONE = "none"           # Без зацикливания
    TRACK = "track"         # Зацикливание текущего трека
    PLAYLIST = "playlist"   # Зацикливание плейлиста
