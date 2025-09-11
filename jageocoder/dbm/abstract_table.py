from abc import ABC
import json
import os
from pathlib import Path
from typing import Optional

from .base_table import BaseTable
from .base_index import BaseIndex


class AbstractTable(BaseTable, BaseIndex, ABC):
    """
    Class that represents an abstract table.

    Attributes
    ----------
    __tablename__: str
        The name of the table.
    __schema__: str
        The schema of the table.
        It must be defined in JSON format.
    __pos_field__: str
        The name of pos field.

    Parameters
    ----------
    db_dir: Path-like, optional
        Base directory where the schema and tables are placed.

    Notes
    -----
    - "db_dir" specifies the base directory where other tables will also be placed.
      Tables are placed in subdirectories with tablename in the base directory.
    """

    __tablename__: str = ""
    __schema__: str = ""
    __pos_field__: str = "_pos"

    def __init__(
        self,
        db_dir: Optional[os.PathLike] = None
    ):

        if db_dir is None:
            db_path = Path.cwd() / "db"
        else:
            db_path = Path(db_dir)

        schema_obj = json.loads(self.__class__.__schema__)
        if not isinstance(schema_obj, dict):
            raise RuntimeError("Schema must be defined as a dict.")

        pos_field = self.__class__.__pos_field__

        BaseTable.__init__(
            self,
            db_dir=db_path,
            tablename=self.__class__.__tablename__,
            schema_json=self.__class__.__schema__,
            pos_field=pos_field,
        )
        BaseIndex.__init__(self, self)

    def create(self):
        super().create()
