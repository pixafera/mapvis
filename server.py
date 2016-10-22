
import json

from flask import Flask, request, redirect, url_for, jsonify, render_template
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlite3 import dbapi2 as sqlite

import model
from mapping import *


app = Flask('mapvis')
#app.config.from_object('mapvis')

app.config.update(dict(DATABASE='sqlite+pysqlite:///mapvis.db'))
app.config.from_envvar('MAPVIS_SETTINGS', silent=True)


engine = create_engine(app.config['DATABASE'], module=sqlite)
Session = sessionmaker(bind=engine)


@app.route('/')
def root():
    return render_template('start.html')


@app.route("/upload", methods=['GET'])
def cant_get_upload():
    return redirect(url_for('hello'))


@app.route("/upload", methods=['POST'])
def upload_file():
    # for form data -- no longer used
    # file_name = request.form['filename']
    # upload = request.files['data']

    file_name = request.args['filename']
    stream = io.BytesIO(request.data) # bytes

    name, ext = os.path.splitext(file_name)
    file_type = ext.lstrip(".")

    session = Session()

    return jsonify(
        name = name,
        **read_spreadsheet(file_type, stream, session)
    )

@app.route("/region/<int:osm_id>")
def region_json(osm_id):
    region = (Session()
        .query(model.Region)
        .filter(model.Region.osm_id == osm_id)
        .one_or_none())
    print(osm_id, region)
    if not region:
        return 404
    return jsonify(**json.loads(region.json))



@app.route("/create")
def create():
    return render_template('create.html')


if __name__ == '__main__':
    app.run(port=5001, debug=True)


