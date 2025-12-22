from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field


# ─────────────────────────────────────────────
# Nested Models for Film Data
# ─────────────────────────────────────────────

class ContentRating(BaseModel):
    """Content/age rating information."""
    label: Optional[str] = None
    rating_code: Optional[str] = None
    description: Optional[str] = None
    icon_url: Optional[str] = None


class ContentWarning(BaseModel):
    """Content warning tag."""
    id: int
    name: str
    key: str


class Stills(BaseModel):
    """Still image URLs at various sizes."""
    small: Optional[str] = None
    medium: Optional[str] = None
    standard: Optional[str] = None
    retina: Optional[str] = None
    small_overlaid: Optional[str] = None
    large_overlaid: Optional[str] = None
    standard_push: Optional[str] = None


class Artwork(BaseModel):
    """Artwork asset with format and URL."""
    format: str
    locale: Optional[str] = None
    image_url: str


class MediaOptions(BaseModel):
    """Media playback options."""
    duration: Optional[int] = None
    hd: Optional[bool] = None


class PlaybackLanguages(BaseModel):
    """Audio and subtitle language options."""
    audio_options: List[str] = []
    extended_audio_options: List[str] = []
    subtitle_options: List[str] = []
    media_options: Optional[MediaOptions] = None
    media_features: List[str] = []



class Consumable(BaseModel):
    """Film availability and playback information (per-country).
    
    Note: The following fields were pruned from the JSON to reduce file size:
    - offered: Always [{"type": "catalogue", ...}]
    - film_id: Already at top level
    - film_date_message: Always null
    - exclusive: Always false, not used
    - permit_download: Always true, not used
    """
    available_at: Optional[str] = None
    availability: Optional[str] = None
    availability_ends_at: Optional[str] = None
    expires_at: Optional[str] = None
    # Playback languages moved to global Film scope
    
    
class Award(BaseModel):
    """Award information."""
    name: Optional[str] = None
    category: Optional[str] = None
    year: Optional[int] = None


class Rating(BaseModel):
    """Multi-source rating entry."""
    source: str
    score_over_10: float
    voters: int


# ─────────────────────────────────────────────
# Main Film Model
# ─────────────────────────────────────────────

class Film(BaseModel):
    """
    Complete film data model matching the extended Mubi API schema.
    Used for both films.json and series.json entries.
    """
    # Core identifiers
    mubi_id: int
    tmdb_id: Optional[int] = None
    imdb_id: Optional[str] = None
    
    # Basic metadata
    title: str
    original_title: Optional[str] = None
    year: Optional[int] = None
    duration: Optional[int] = None
    genres: List[str] = []
    directors: List[str] = []
    short_synopsis: Optional[str] = None
    default_editorial: Optional[str] = None
    historic_countries: List[str] = []
    
    # Mubi-specific ratings
    popularity: Optional[int] = None
    average_rating_out_of_ten: Optional[float] = None
    number_of_ratings: Optional[int] = None
    hd: Optional[bool] = None
    critic_review_rating: Optional[float] = None
    
    # Content rating & warnings
    content_rating: Optional[ContentRating] = None
    content_warnings: List[ContentWarning] = []
    
    # Imagery & artwork
    stills: Optional[Stills] = None
    still_url: Optional[str] = None
    portrait_image: Optional[str] = None
    artworks: List[Artwork] = []
    
    # Trailers
    trailer_url: Optional[str] = None
    trailer_id: Optional[int] = None
    optimised_trailers: Optional[List[Dict[str, Any]]] = None
    
    # Availability & playback
    # Consumable info is now per-country in available_countries
    playback_languages: Optional[PlaybackLanguages] = None

    # Awards & press
    award: Optional[Award] = None
    press_quote: Optional[Any] = None  # Can be str or dict
    
    # Series/episode info (null for regular films)
    episode: Optional[Dict[str, Any]] = None
    series: Optional[Dict[str, Any]] = None
    
    # Scraper-added metadata
    available_countries: Dict[str, Consumable] = {}
    
    # Multi-source ratings (enriched)
    ratings: List[Rating] = []

    # Bayesian Calcuations

    
    class Config:
        extra = 'ignore'  # Allow extra fields for API compatibility


# ─────────────────────────────────────────────
# Database Wrapper Models
# ─────────────────────────────────────────────

class Meta(BaseModel):
    """Metadata about the generated JSON file."""
    generated_at: str
    version: int
    version_label: Optional[str] = None  # Human-readable version (e.g., "1.0-beta.1")
    total_count: int
    mode: str


class BayesStats(BaseModel):
    """Bayesian Rating Calibration Constants."""
    global_mean_C: float
    mubi_confidence_m: float


class MubiDatabase(BaseModel):
    """Root model for films.json and series.json files."""
    meta: Meta
    bayes_stats: Optional[BayesStats] = None
    items: List[Film]
