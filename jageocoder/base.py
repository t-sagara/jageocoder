import sqlalchemy
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


def get_session(obj: Base):
    inspector = sqlalchemy.inspect(obj)
    return inspector.session
