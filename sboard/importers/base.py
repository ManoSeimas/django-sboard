from sqlalchemy import MetaData
from sqlalchemy.engine import create_engine
from sqlalchemy.orm import sessionmaker

metadata = MetaData()


class MigrationBase(object):
    def __init__(self, dbi, params=None):
        self.params = params or {}
        engine = create_engine(dbi, echo=False)
        metadata.bind = engine
        Session = sessionmaker(bind=engine)
        self.session = Session()
