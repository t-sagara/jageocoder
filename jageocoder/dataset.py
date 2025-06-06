from logging import getLogger
from pathlib import Path
from typing import Dict

from PortableTab import AbstractTable

from .exceptions import JageocoderError


logger = getLogger(__name__)


class Dataset(AbstractTable):
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
    __schema__ = """{
            "id": 0,
            "title": "",
            "url": ""
        }"""
    __id_field__ = "_pos"

    def __init__(self, db_dir: Path) -> None:
        super().__init__(db_dir=db_dir)
        self._map = None

    def load_records(self):
        self._map = {}
        for record in self.get_records_by_pos(0, self.count_records()):
            self._map[record["id"]] = record

    def get(self, id: int) -> dict:
        if self._map is None:
            self.load_records()

        if not isinstance(self._map, dict):
            raise JageocoderError("Can't initialize dataset metadata.")

        return self._map[id]

    def get_all(self) -> Dict[int, dict]:
        if self._map is None:
            self.load_records()

        if not isinstance(self._map, dict):
            raise JageocoderError("Can't initialize dataset metadata.")

        return self._map
