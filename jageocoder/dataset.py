from logging import getLogger

from sqlalchemy import Column, SmallInteger, String

from jageocoder.base import Base

logger = getLogger(__name__)


class Dataset(Base):
    """
    Dataset metadata.

    Attributes
    ----------
    id : int
        The unique identifier.
        This value also indicates priority assigned to this dataset.
        Smaller value indicates higher priority.
    title : str
        The title of this dataset.
    url : str
        The URL where the dataset is distributed.
    """

    __tablename__ = 'dataset'

    id = Column(SmallInteger, primary_key=True)
    title = Column(String, nullable=False, default='')
    url = Column(String)
