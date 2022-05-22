from logging import getLogger

from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from jageocoder.base import Base

logger = getLogger(__name__)


class NoteNode(Base):
    """
    The search table of Node.note and Node.id. Stored in 'notenode' table.

    Attributes
    ----------
    id : int
        The key identifier that is automatically sequentially numbered.
    node_id : int
        Node id that corresponds one-to-one to a note expression.
    note : str
        The note in the node.

    Note
    ----
    The note field of each node contains multiple notes separated by '/'.
    In order to search them quickly, the ID of the node corresponding to
    a single note is managed in this table.
    """

    __tablename__ = 'notenode'

    id = Column(Integer, primary_key=True)
    node_id = Column(Integer, ForeignKey('node.id'), nullable=False)
    note = Column(String, nullable=False)

    node = relationship("AddressNode")
