from typing import List, Optional, Any, Dict
from pydantic import BaseModel, HttpUrl, Field

class Film(BaseModel):
    mubi_id: int
    title: str
    original_title: Optional[str] = None
    genres: List[str]
    countries: List[str]
    year: Optional[int] = None
    duration: Optional[int] = None
    directors: List[Any]  # Can be list of strings (GitHub) or dicts (API), normalized later but strictly should be one.
                          # Since we want to ENFORCE schema, let's look at what we produce.
                          # We produce list of strings in backend/films.json.
                          # So we should enforce that or Union.
                          # The user asked to ensure generated jsons are according to schema.
                          # backend/films.json has list of strings.
                          # But the plugin code I just fixed expects list of dicts.
                          # Wait, I fixed the plugin to accept EITHER (by normalizing).
                          # But ideally the backend should produce cleaner data.
                          # Let's define the schema as what the backend produces for now (List[str]).
                          # Actually, looking at `films.json` it is `["Director 1", "Director 2"]`.
    directors: List[str]
    
    popularity: Optional[int] = None
    average_rating_out_of_ten: Optional[float] = None
    short_synopsis: Optional[str] = None
    default_editorial: Optional[str] = None
    
    # Series specific fields (often null for films)
    episode: Optional[Dict[str, Any]] = None
    series: Optional[Dict[str, Any]] = None

    # Allow extra fields for now to avoid breaking on minor API changes
    class Config:
        extra = 'ignore'

class Meta(BaseModel):
    generated_at: str
    version: int
    total_count: int
    mode: str

class MubiDatabase(BaseModel):
    meta: Meta
    items: List[Film]
