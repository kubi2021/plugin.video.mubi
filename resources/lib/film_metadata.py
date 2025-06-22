import xbmc
from typing import List, Optional


class FilmMetadata:
    def __init__(
        self, 
        title: str, 
        director: List[str], 
        year: Optional[int], 
        duration: Optional[int], 
        country: List[str], 
        plot: str, 
        plotoutline: str, 
        genre: List[str], 
        originaltitle: str, 
        rating: Optional[float] = 0.0, 
        votes: Optional[int] = 0, 
        castandrole: Optional[str] = "", 
        dateadded: Optional[str] = "", 
        trailer: Optional[str] = "", 
        image: Optional[str] = ""
    ):
        try:
            self.title = title
            self.director = director or []  # Ensures we always have a list
            self.year = year if year is not None else "Unknown"
            self.duration = duration if duration is not None else 0
            self.country = country or []  # Ensures we always have a list
            self.plot = plot
            self.plotoutline = plotoutline
            self.genre = genre or []  # Ensures we always have a list
            self.originaltitle = originaltitle
            self.rating = rating if rating is not None else 0.0
            self.votes = votes if votes is not None else 0
            self.castandrole = castandrole
            self.dateadded = dateadded
            self.trailer = trailer
            self.image = image
        except Exception as e:
            xbmc.log(f"Error initializing Metadata object: {e}", xbmc.LOGERROR)

    def __repr__(self):
        return (
            f"Metadata(title={self.title}, director={self.director}, year={self.year}, "
            f"duration={self.duration}, country={self.country}, rating={self.rating}, votes={self.votes})"
        )

    def as_dict(self) -> dict:
        """
        Convert metadata to a dictionary format.
        
        :return: Dictionary containing metadata fields.
        """
        try:
            return {
                'title': self.title,
                'director': self.director,
                'year': self.year,
                'duration': self.duration,
                'country': self.country,
                'plot': self.plot,
                'plotoutline': self.plotoutline,
                'genre': self.genre,
                'originaltitle': self.originaltitle,
                'rating': self.rating,
                'votes': self.votes,
                'castandrole': self.castandrole,
                'dateadded': self.dateadded,
                'trailer': self.trailer,
                'image': self.image
            }
        except Exception as e:
            xbmc.log(f"Error converting Metadata to dict: {e}", xbmc.LOGERROR)
            return {}

