import csv
import model
import party
import party2

from flask import Flask, request
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlite3 import dbapi2 as sqlite

app = Flask('mapvis')
#app.config.from_object('mapvis')

app.config.update(dict(DATABASE='sqlite+pysqlite:///mapvis.db'))
app.config.from_envvar('MAPVIS_SETTINGS', silent=True)


engine = create_engine(app.config['DATABASE'], module=sqlite)
Session = sessionmaker(bind=engine)

@app.route("/")
def hello():
	return "<html><body><form method='POST' action='upload' enctype='multipart/form-data'><input type='file' name='data'/><input type='submit' value='submit'/></form></body></html>"

@app.route("/upload", methods=['POST'])
def upload_file():
	data_file = request.files['data']
	print(data_file.filename, data_file)
	return str(party2.read_spreadsheet(data_file.filename, data_file))

if __name__ == '__main__':
	app.run(debug=True)