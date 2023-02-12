import sqlalchemy
from sqlalchemy.orm import registry


mapper_registry = registry()


Base = mapper_registry.generate_base()

""" 1.4
import sqlalchemy
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()
"""


def get_session(obj: Base):
    inspector = sqlalchemy.inspect(obj)
    return inspector.session
