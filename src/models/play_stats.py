from pydantic import BaseModel


class PlayStats(BaseModel):
    date: str
    play_count: int