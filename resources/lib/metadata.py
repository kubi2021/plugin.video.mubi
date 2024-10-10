# metadata.py

class Metadata:
    def __init__(self, title, director, year, duration, country, plot, plotoutline, genre, originaltitle, rating, votes, castandrole, dateadded, trailer, image):
        self.title = title
        self.director = director
        self.year = year
        self.duration = duration
        self.country = country
        self.plot = plot
        self.plotoutline = plotoutline
        self.genre = genre
        self.originaltitle = originaltitle
        self.rating = rating
        self.votes = votes
        self.castandrole = castandrole
        self.dateadded = dateadded
        self.trailer = trailer
        self.image = image

    def __repr__(self):
        return f"Metadata(title={self.title}, director={self.director}, year={self.year}, duration={self.duration}, country={self.country})"

    def as_dict(self):
        """
        Convert metadata to a dictionary format, if needed.
        """
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
