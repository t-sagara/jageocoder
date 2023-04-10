from logging import getLogger
from pathlib import Path

from PortableTab import BaseTable


logger = getLogger(__name__)


class Dataset(BaseTable):
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
    __schema__ = """
        struct Dataset {
            id @0 :UInt8;
            title @1 :Text;
            url @2 :Text;
        }
        """
    __record_type__ = "Dataset"

    def __init__(self, db_dir: Path) -> None:
        super().__init__(db_dir=db_dir)
        self._map = None

    def load_records(self):
        self._map = {}
        for i in range(self.count_records()):
            record = self.get_record(pos=i, as_dict=True)
            self._map[record["id"]] = record

        self.unload()

    def get(self, id: int) -> dict:
        if self._map is None:
            self.load_records()

        return self._map[id]
