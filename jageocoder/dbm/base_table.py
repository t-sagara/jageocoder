from functools import lru_cache

import json
from logging import getLogger
import os
from pathlib import Path
import sqlite3
from typing import (
    Any, Dict, Generator, Iterator, Iterable, Optional, Tuple, Union)

from .types import Record

logger = getLogger(__name__)


class NotInitializedError(RuntimeError):
    pass


class BaseTable(object):
    """
    Class that represents a table assigned schema.

    Attributes
    ----------

    Parameters
    ----------
    db_dir: Path-like, optional
        Base directory where the schema and tables are placed.

    Notes
    -----
    - "db_dir" specifies the base directory where other tables will also be placed.
      Tables are placed in subdirectories with tablename in the base directory.
    """

    PAGE_SIZE = 100000

    def _check_initialized(self) -> None:
        if not self.is_defined:
            raise RuntimeError("Table is not initialized.")

    @classmethod
    def createFromData(
        cls,
        tablename: str,
        data: Iterable[Record],
        db_dir: Optional[os.PathLike] = None,
    ):
        """
        Create table from data.

        Parameters
        ----------
        tablename: str
            The tablename to be created
        data: Iterable[Record]
            The data to be stored
        db_dir: Path-like, optional
            Base directory where the schema and tables are placed.

        """
        table = None
        schema_json = json.dumps(next(iter(data)))
        table = cls(
            db_dir=db_dir if db_dir is not None else Path.cwd(),
            tablename=tablename,
            schema_json=schema_json,
        )
        table.create()
        table.append_records(data)
        return table

    def __init__(
        self,
        tablename: str,
        schema_json: Optional[str] = None,
        db_dir: Optional[os.PathLike] = None,
        pos_field: str = "_pos",
    ) -> None:
        self.tablename = tablename
        _db_dir = Path(db_dir) if db_dir is not None else Path.cwd()
        self.db_dir = _db_dir
        self.pos_field = pos_field
        self.conn = None
        self.config = None

        if schema_json:
            schema = json.loads(schema_json)
            if not isinstance(schema, dict):
                raise ValueError("'schema_json' must be a JSON object.")
            self.schema: dict = schema
        else:
            # Read from existing config
            try:
                self.config = self.get_config()
                self.schema = self.config.get("schema", {})
                self.pos_field = self.config.get("pos_field")
            except NotInitializedError:
                # Not configured yet
                pass

    @property
    def is_defined(self) -> bool:
        return self.schema != {}

    def _get_sql_fields(
        self,
        include_pos_field: bool = False,
    ) -> Tuple[str, str]:
        """
        Get 'columns' and 'parameters' strings from schema.

        Parameters
        ----------
        include_pos_field: bool (False)
            If True, the return strings include pos field.

        Returns
        -------
        Tuple[str, str]
            The first string is the list of field names.
            The second string is the list of slots.
        """
        if include_pos_field:
            cols = [self.get_pos_field()]
            pars = ["?"]
        else:
            cols = []
            pars = []

        for k in self.schema.keys():
            cols.append(f'"{k}"')
            pars.append("?")

        return (",".join(cols), ",".join(pars))

    def __del__(self) -> None:
        if self.conn:
            self.conn.close()

    def get_pos_field(self) -> str:
        if isinstance(self.pos_field, str):
            return self.pos_field

        raise RuntimeError("'pos_field' is not set.")

    def get_conn(self) -> sqlite3.Connection:
        # self._check_initialized()
        if self.conn:
            return self.conn

        path = self.get_sqlite_path()
        if not path.parent.exists():
            path.parent.mkdir(parents=False, exist_ok=False)

        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row

        cur = self.conn.cursor()
        cur.execute(
            "CREATE TABLE IF NOT EXISTS _config_ (schema JSON, pos_field VARCHAR, table_name VARCHAR, count INTEGER)")
        cur.close()
        self.conn.commit()
        return self.conn

    def commit(self) -> None:
        self._check_initialized()
        self.get_conn().commit()

    @lru_cache(maxsize=128)
    def get_dir(self) -> Path:
        """
        Get the directory where the table are placed.
        """
        if self.db_dir is None:
            raise NotInitializedError("'db_dir' is not set.")

        return self.db_dir

    @lru_cache(maxsize=128)
    def get_config(self) -> dict:
        """
        Get the contents of the config file of the table.
        """
        if self.config is not None:
            return self.config

        conn = self.get_conn()
        conn.row_factory = sqlite3.Row
        res = conn.execute("SELECT * FROM _config_")
        row = res.fetchone()
        if row is None:
            raise NotInitializedError("No configs.")

        _config = {}
        for k in row.keys():
            if k in ("schema"):
                _config[k] = json.loads(row[k])
            else:
                _config[k] = row[k]

        self.config = _config
        return self.config

    def set_config(self, config: dict) -> None:
        """
        Set the contents of the config file of the table.

        Notes
        -----
        - This method overwrite the config file completery.
        """
        self.config = config
        self.get_config.cache_clear()
        _config = {k: json.dumps(v) if k in (
            'schema') else v for k, v in config.items()}

        cols = ",".join(_config.keys())
        pars = ",".join(["?" for _ in _config.values()])
        vals = tuple(_config.values())
        cur = self.get_conn().cursor()
        cur.execute("DELETE FROM _config_")
        cur.execute(
            f"INSERT INTO _config_ ({cols}) VALUES ({pars})",
            vals,)
        cur.close()
        self.get_conn().commit()

    def _get_create_table_statement(self) -> str:

        def _infer_type(value):
            if isinstance(value, int):
                return 'INTEGER'
            elif isinstance(value, float):
                return 'REAL'
            elif isinstance(value, str):
                return 'TEXT'
            elif isinstance(value, bool):
                return 'INTEGER'  # SQLite では BOOLEAN = INTEGER
            elif value is None:
                return 'NULL'
            elif isinstance(value, (dict, list)):
                return 'JSON'  # JSON 文字列として保存
            else:
                return 'TEXT'  # その他は文字列扱い

        self._check_initialized()
        pos_field = self.get_pos_field()
        columns = [f"{pos_field} INTEGER PRIMARY KEY"]
        for key, value in self.schema.items():
            col_type = _infer_type(value)
            sanitized_key = key.replace('"', '""')
            columns.append(f'"{sanitized_key}" {col_type}')

        sql = ', '.join(columns)
        create_statement = f'CREATE TABLE records ({sql})'
        return create_statement

    def count_records(self) -> int:
        """
        Count the number of records in the table.

        Returns
        -------
        int
            The number of records.

        Notes
        -----
        - This method actually just reads the configuration file.
        """
        self._check_initialized()
        config = self.get_config()
        return config["count"]

    def get_sqlite_path(self) -> Path:
        """
        Get the path to the sqlite file.

        Returns
        -------
        Path
            Path to the page file.
        """
        table_dir = self.get_dir()
        return table_dir / f"{self.tablename}.sqlite"

    def dict2tuple(self, record: Record) -> tuple:
        vals = []
        for k, v in self.schema.items():
            val = record[k] if k in record else self.schema[k]
            if isinstance(v, (dict, list)):
                val = json.dumps(val, ensure_ascii=False)

            vals.append(val)

        return tuple(vals)

    def dicts2tuples(self, records: Iterable[Record]) -> Generator[tuple, None, None]:
        for record in records:
            vals = self.dict2tuple(record)
            yield tuple(vals)

    def _write_records(
            self,
            records: Iterable[Record]) -> None:
        """
        Write whole records.

        Parameters
        ----------
        records: list
            List of records to be output.

        """
        conn = self.get_conn()
        cur = conn.cursor()
        # cur.execute("TRUNCATE records")
        cols, pars = self._get_sql_fields()
        cur.executemany(
            f"INSERT INTO records ({cols}) VALUES ({pars})", self.dicts2tuples(records))
        conn.commit()

    def _write_rows(
            self,
            rows: Iterable[Any]) -> None:
        """
        Write whole records.

        Parameters
        ----------
        rows: Collection
            List of rows to be registered.

        """
        conn = self.get_conn()
        cur = conn.cursor()
        # cur.execute("TRUNCATE records")
        cols = ",".join([f'"{k}"' for k in self.schema.keys()])
        pars = ",".join(["?" for _ in self.schema.values()])
        cur.executemany(
            f"INSERT INTO records ({cols}) VALUES ({pars})", rows)
        conn.commit()

    def delete(self) -> None:
        """
        Delete the sqlite3 file containing this table.
        """
        path = self.get_sqlite_path()
        if path.exists():
            path.unlink()

    def create(
        self,
        schema_obj: Optional[dict] = None,
        pos_field: Optional[str] = None,
    ) -> None:
        """
        Create table.

        Parameters
        ----------
        schema_obj: dict
            An row object with the schema.
        pos_field: str
            Specify position field.

        Returns
        -------
        Path
            Directory path where the created tables and schema will be stored.

        """
        if schema_obj is None:
            _schema = self.schema
        else:
            _schema = schema_obj

        if pos_field is None:
            _pos_field = self.pos_field

        if _pos_field in _schema:
            raise RuntimeError(
                f"The field '{_pos_field}' is used for managing the position.")

        # Write schema
        self.set_config({
            "schema": _schema,
            "pos_field": _pos_field,
            "table_name": self.tablename,
            "count": 0
        })
        self.schema = _schema
        self.pos_field = _pos_field

        # Create empty table
        cur = self.get_conn().cursor()
        cur.execute(f"DROP TABLE IF EXISTS records")
        cur.execute(self._get_create_table_statement())
        self.commit()

        return

    def get_record(
        self,
        pos: int,
        with_pos: bool = False,
    ) -> Record:
        """
        Get a record from the table by pos.

        Parameters
        ----------
        pos: int
            Target record's pos.

        Returns
        -------
        Record
        """
        conn = self.get_conn()
        conn.row_factory = sqlite3.Row
        pos_field = self.get_pos_field()
        res = conn.execute(
            f"SELECT * FROM records WHERE {pos_field}=?", (pos,))
        row = res.fetchone()
        if row is None:
            raise ValueError("No record.")

        record: Record = {pos_field: row[pos_field]} if with_pos else {}
        for k, v in self.schema.items():
            if isinstance(v, (list, dict)):
                val = json.loads(row[k])
            else:
                val = (type(v))(row[k]) if row[k] is not None else None

            record[k] = val

        return record

    def get_row(
            self,
            pos: int,
            with_pos: bool = False,
    ) -> tuple:
        """
        Get a record from the table by pos.

        Parameters
        ----------
        pos: int
            Target record's pos.

        Returns
        -------
        tuple
        """
        conn = self.get_conn()
        conn.row_factory = None
        pos_field = self.get_pos_field()
        cols, _ = self._get_sql_fields(include_pos_field=with_pos)
        res = conn.execute(
            f"SELECT {cols} FROM records WHERE {pos_field}=?", (pos,))
        row = res.fetchone()
        if row is None:
            raise ValueError("No record.")

        return row

    def get_records_by_pos(
        self,
        from_pos: int,
        to_pos: int,
        with_pos: bool = False,
    ) -> Iterator[Record]:
        """
        Get records from the table at the specified positions.

        Parameters
        ----------
        from_pos: int
            The start position of the target record.
        to_pos: int
            The end position of the target record.
            The 'to_pos'th record are not included.

        Returns
        -------
        Iterator[Record]
        """
        if from_pos < 0 or to_pos > self.count_records():
            raise ValueError("Out of range.")

        limits = to_pos - from_pos
        conn = self.get_conn()
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        pos_field = self.get_pos_field()
        cols, _ = self._get_sql_fields(include_pos_field=with_pos)
        _ = cur.execute((
            f"SELECT {cols} FROM records "
            f"WHERE {pos_field} >= ? AND {pos_field} < ? ORDER BY {pos_field}"),
            (from_pos, to_pos))

        for row in cur:
            record: Record = {pos_field: row[pos_field]} if with_pos else {}
            for k, v in self.schema.items():
                if isinstance(v, (list, dict)):
                    val = json.loads(row[k])
                else:
                    val = (type(v))(row[k]) if row[k] is not None else None

                record[k] = val

            yield record

    def get_rows_by_pos(
            self,
            from_pos: int,
            to_pos: int,
            with_pos: bool = False,
    ) -> Iterator[tuple]:
        """
        Get rows from the table at the specified positions.

        Parameters
        ----------
        from_pos: int
            The start position of the target record.
        to_pos: int
            The end position of the target record.
            The 'to_pos'th record are not included.

        Returns
        -------
        Iterator[tuple]
        """
        if from_pos < 0 or to_pos > self.count_records():
            raise ValueError("Out of range.")

        limits = to_pos - from_pos
        conn = self.get_conn()
        conn.row_factory = None
        cur = conn.cursor()
        pos_field = self.get_pos_field()
        cols, _ = self._get_sql_fields(include_pos_field=with_pos)
        _ = cur.execute(
            f"SELECT {cols} FROM records ORDER BY {pos_field} LIMIT ? OFFSET ?",
            (limits, from_pos,))

        for row in cur:
            yield row

    def retrieve_records(
        self,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        cond_clause: Optional[str] = None,
        cond_params: Optional[tuple] = None,
    ) -> Iterator[Record]:
        """
        Get a iterator that retrieves records from the table.

        Paramaters
        ----------
        limit: int, optional
            Max number of records to be retrieved.
            If omitted, all records are retrieved.
        offset: int, optional
            Specifies the number of records to be retrieved from.
            If omitted, the retrieval is performed from the beginning.

        Returns
        -------
        Iterator[Record]
        """
        if limit is None:
            limit = self.count_records()

        offset = 0 if offset is None else offset

        conn = self.get_conn()
        pos_field = self.get_pos_field()
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        if cond_clause:
            params = list(cond_params) if cond_params else []
            params += [limit, offset]
            cur.execute(
                f"SELECT * FROM records WHERE {cond_clause} ORDER BY {pos_field} LIMIT ? OFFSET ?",
                params)
        else:
            cur.execute(
                f"SELECT * FROM records ORDER BY {pos_field} LIMIT ? OFFSET ?",
                (limit, offset))

        for row in cur:
            record: Record = {pos_field: row[pos_field]}
            for k, v in self.schema.items():
                if isinstance(v, (list, dict)):
                    val = json.loads(row[k])
                else:
                    val = (type(v))(row[k])

                record[k] = val

            yield record

    def retrieve_rows(
        self,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        cond_clause: Optional[str] = None,
        cond_params: Optional[tuple] = None,
    ) -> Iterator[tuple]:
        """
        Get a iterator that retrieves rows from the table.

        Paramaters
        ----------
        limit: int, optional
            Max number of records to be retrieved.
            If omitted, all records are retrieved.
        offset: int, optional
            Specifies the number of records to be retrieved from.
            If omitted, the retrieval is performed from the beginning.

        Returns
        -------
        Iterator[tuple]
        """
        if limit is None:
            limit = self.count_records()

        offset = 0 if offset is None else offset

        conn = self.get_conn()
        conn.row_factory = None
        pos_field = self.get_pos_field()

        cur = conn.cursor()
        if cond_clause:
            params = list(cond_params) if cond_params else []
            params += [limit, offset]
            cur.execute(
                f"SELECT * FROM records WHERE {cond_clause} ORDER BY {pos_field} LIMIT ? OFFSET ?",
                params)
        else:
            cur.execute(
                f"SELECT * FROM records ORDER BY {pos_field} LIMIT ? OFFSET ?",
                (limit, offset))

        for row in cur:
            yield row

    def append_records(
            self,
            records: Iterable[Record]) -> None:
        """
        Appends a set of record to the end of the table.

        Paramaters
        ----------
        records: Iterable[Record]
            Iterable that returns the records in order.
        """
        cur_pos = self.count_records()
        buf = []
        for i, record in enumerate(records):
            if cur_pos == 0:
                cols, pars = self._get_sql_fields(include_pos_field=True)
                conn = self.get_conn()
                vals = [0] + list(self.dict2tuple(record))
                conn.execute(
                    f"INSERT INTO records ({cols}) VALUES ({pars})",
                    vals,
                )
            else:
                buf.append(record)

            i += 1
            cur_pos += 1
            if i == self.PAGE_SIZE:
                self._write_records(buf)
                buf.clear()
                i = 0

        if len(buf) > 0:
            self._write_records(buf)

        # Adjust record count.
        config = self.get_config()
        config["count"] = cur_pos
        self.set_config(config)

    def append_rows(
            self,
            rows: Iterable[tuple]) -> None:
        """
        Appends a set of tuples to the end of the table.

        Paramaters
        ----------
        rows: Iterable[tuple]
            Iterable that returns the tuples in order.
        """
        cur_pos = self.count_records()
        if cur_pos == 0:
            # Set pos=0 to the first record
            try:
                row: tuple = next(iter(rows))
                cols, pars = self._get_sql_fields(include_pos_field=True)
                conn = self.get_conn()
                vals = [0] + list(row)
                conn.execute(
                    f"INSERT INTO records ({cols}) VALUES ({pars})",
                    vals,
                )
            except StopIteration:
                pass

        buf = []
        for i, row in enumerate(rows):
            buf.append(row)
            i += 1
            cur_pos += 1
            if i == 10000:
                self._write_rows(buf)
                buf.clear()
                i = 0

        if len(buf) > 0:
            self._write_rows(buf)

        # Adjust record count.
        config = self.get_config()
        config["count"] = cur_pos
        self.set_config(config)

    def update_record(
        self,
        pos: int,
        record: Record,
    ) -> None:
        """
        Updates records in the table that has already been output to a file.

        Paramaters
        ----------
        pos: int
            The posison of records to be updated.
        record: Record
            The record contents to be updated.
        """
        cur = self.get_conn().cursor()
        fields = []
        vals = []
        for k, v in record.items():
            if k not in self.schema:
                raise ValueError(f"Field '{k}' is not in this table.")
            elif k == self.pos_field:
                raise ValueError(
                    f"The value of the pos field can not modified.")

            fields.append(k)
            if isinstance(self.schema[k], (dict, list)):
                vals.append(json.dumps(v, ensure_ascii=False))
            else:
                vals.append(v)

            cols = ",".join([f"{k}=?" for k in fields])
            vals.append(pos)
            cur.execute(
                f"UPDATE records SET {cols} WHERE {self.pos_field}=?", vals)

        cur.close()
        self.commit()

    def update_row(
        self,
        pos: int,
        row: tuple,
    ) -> None:
        """
        Updates records in the table that has already been output to a file.

        Paramaters
        ----------
        pos: int
            The posison of records to be updated.
        row: tuple
            The values to be updated.
        """
        cur = self.get_conn().cursor()
        cols, pars = self._get_sql_fields(include_pos_field=False)
        vals = list(row)
        vals.append(pos)
        cur.execute(
            f"UPDATE records SET {cols} WHERE {self.pos_field}=?", tuple(vals))

        cur.close()
        self.commit()

    def update_records(
            self,
            updates: Dict[int, Record]) -> None:
        """
        Updates records in the table that has already been output to a file.

        Paramaters
        ----------
        updates: Dict[int, Record]
            A dict whose keys are the pos of records to be updated and
            whose values are the Record contents to be updated.

            The format of the values are a dict of field name/value pairs
            to be updated.
        """
        updates = dict(sorted(updates.items()))
        pos_field = self.get_pos_field()

        cur = self.get_conn().cursor()
        for pos, new_value in updates.items():
            cols = []
            vals = []
            for k, v in new_value.items():
                if k not in self.schema:
                    raise ValueError(f"Field '{k}' is not in this table.")
                elif k == pos_field:
                    raise ValueError(
                        f"The value of the pos field can not modified.")

                cols.append(k)
                if isinstance(self.schema[k], (dict, list)):
                    vals.append(json.dumps(v, ensure_ascii=False))
                else:
                    vals.append(v)

            cols = ",".join([f"{k}=?" for k in cols])
            vals.append(pos)
            cur.execute(
                f"UPDATE records SET {cols} WHERE {pos_field}=?", vals)

        cur.close()
        self.commit()

    def __len__(self):
        return self.count_records()

    def __getitem__(self, sub: Union[int, Iterable[int], slice]):
        nrecords = len(self)
        if isinstance(sub, int):
            if sub >= nrecords or sub < -nrecords:
                raise IndexError(f"Position {sub} out of range")

            if sub < 0:
                sub = nrecords + sub

            return self.get_record(sub)

        if isinstance(sub, Iterable):
            positions = []
            for x in sub:
                if x >= nrecords or x < -nrecords:
                    raise IndexError("Position {x} out of range")

                if x < 0:
                    x = nrecords + x

                positions.append(x)

            return tuple([self.get_record(x) for x in positions])

        if isinstance(sub, slice):
            _start = sub.start if sub.start is not None else 0
            _stop = sub.stop if sub.stop is not None else nrecords
            _step = sub.step if sub.step is not None else 1
            if _start >= nrecords or _start < -nrecords:
                raise IndexError(f"Start position {_start} out of range")
            if _start < 0:
                _start = nrecords + _start

            if _stop - 1 >= nrecords or _stop - 1 < -nrecords:
                raise IndexError(f"Stop position {_stop} out of range")
            if _stop < 0:
                _stop = nrecords + _stop

            return tuple([self.get_record(x) for x in range(
                _start, _stop, _step)])

        raise TypeError(f"Invalid subscription type '{type(sub)}'")
