import model
import os

from sqlalchemy import create_engine
from sqlite3 import dbapi2 as sqlite

try:
	os.remove('mapvis.db')
except FileNotFoundError:
	pass
	
e = create_engine('sqlite+pysqlite:///mapvis.db', module=sqlite)
model.Base.metadata.create_all(e)