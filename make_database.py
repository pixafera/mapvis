import model
import os

from sqlalchemy import create_engine
from sqlite3 import dbapi2 as sqlite

os.remove('mapvis.db')
e = create_engine('sqlite+pysqlite:///mapvis.db', module=sqlite)
model.Base.metadata.create_all(e)