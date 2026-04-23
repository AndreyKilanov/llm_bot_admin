from pydantic import BaseModel, HttpUrl


class TrackInfo(BaseModel):
    """Схема информации о музыкальном треке."""
    title: str
    raw_title: str
    url: HttpUrl | str
    duration: int = 0
    thumbnail: HttpUrl | str = ""
    uploader: str = "Неизвестно"
    id: str = ""
    view_count: int = 0
    added_by: str | None = None
    source: str | None = None


class PlaylistInfo(BaseModel):
    """Схема информации о плейлисте."""
    title: str
    url: HttpUrl | str
    tracks: list[TrackInfo]
