
from collections import Counter
import io
import json
import os
import random

import chardet
import pyexcel
import requests
import sqlalchemy.orm

import model


#------------------------------------------------------------------------------
# query & cache OSM


def query_osm(query):
    r = requests.get("http://nominatim.openstreetmap.org/search", params=dict(
        format = 'jsonv2',
        q = query,
        limit = 5,
        polygon_svg=1,
    ))

    results = r.json()

    boundaries = [item for item in results if item['category'] == 'boundary']

    print("Found {} boundaries".format(len(boundaries)))

    # # Arbitrarily pick the first one -- OSM seems to sort them by importance?
    # boundary = boundaries[0]

    # Only keep a few fields
    for boundary in boundaries:
        d = dict(
            # Key cached objects based on OSM id
            # -- make sure we don't cache 'em more than once
            osm_id = int(boundary['osm_id']),

            # Can display in the UI
            name = boundary['display_name'],

            place_rank = boundary['place_rank'],

            # default SVG paths are too detailed to store/render!
            simple_path = simplify_path(boundary['svg']),

            # Might want to keep the centre
            lat = boundary['lat'],
            lon = boundary['lon'],
        )
        yield d

def simplify_path(svg):
    segments = svg.split("M ")
    assert segments.pop(0) == ""

    # TODO only keep the largest segments
    segments.sort(key=len, reverse=True)
    segments = segments[:3]

    segments = [simplify_segment("M " + s.rstrip(" ")) for s in segments]
    return " ".join(segments)

def simplify_segment(svg):
    words = svg.split(" ")

    # Keep first four items & last item
    assert words[0] == 'M'
    assert words[3] == 'L'
    assert words[-1] == 'Z'
    first = ['M', words[1], words[2], 'L']
    last = ['Z']

    pairs = [(words[i], words[i+1]) for i in range(4, len(words) - 1, 2)]

    # Keep N points
    limit = 150 # TODO tweak this
    try:
        indexes = random.sample(list(range(len(pairs))), limit)
        indexes.sort()
        selected = [" ".join(pairs[i]) for i in indexes]
    except ValueError:
        selected = [" ".join(p) for p in pairs]

    return " ".join(first + selected + last)


def fetch_query(query, session):
    """Create a Query and associated Regions"""

    q = model.Query(search_string=query)
    boundary = list(query_osm(query))
    regions = {r.osm_id: r for r in session.query(model.Region).filter(model.Region.osm_id.in_(b['osm_id'] for b in boundary))}

    # Make regions
    for b in boundary:
        if b['osm_id'] in regions:
            continue

        r = model.Region(osm_id=b['osm_id'], place_rank=b['place_rank'], json=json.dumps(b))
        regions[r.osm_id] = r
        session.add(r)
    session.commit()

    q.regions.extend(regions.values())

    return q


def gather_regions(query_list, session):
    """Take a list of queries and return a set of similar Regions"""
    results = []
    db_queries = session.query(model.Query).filter(model.Query.search_string.in_(query_list)).options(sqlalchemy.orm.joinedload(model.Query.regions))
    db_query_lookup = {q.search_string: q for q in db_queries}
    for query in query_list:
        q = db_query_lookup.get(query)
        if q is None:
            print("cache miss: {}".format(query))
            q = fetch_query(query, session)

            if q is not None:
                print("cache insert")
                session.add(q)
                session.commit()
        else:
            print("cache hit")
        results.append((query, q))

    # TODO decide the most popular place_rank from the results
    # TODO return a list of results with equal place_rank (as far as possible)

    # for now, return only the first Region
    return [(q, (None if len(b.regions) == 0 else json.loads(b.regions[0].json))) for q, b in results]


#------------------------------------------------------------------------------
# read spreadsheet

def get_sheet(file_type, stream):
    if file_type == 'csv':
        raw = stream.read()
        det = chardet.detect(raw)
        stream = io.StringIO(raw.decode(det['encoding']))
    return pyexcel.get_sheet(
        file_type=file_type,
        file_stream=stream,
        name_columns_by_row=0, # First row is headings
        auto_detect_int=False, # TODO do these do anything?
        auto_detect_float=False, # TODO do these do anything?
    )

def guess_kind(value):
    if isinstance(value, int):
        return 'int'
    elif isinstance(value, float):
        return 'float'
    elif isinstance(value, str):
        if value.strip() == '':
            return 'empty'

        value = value.strip()
        num = value.replace("%", "").replace(",", "")
        is_num = num.replace(".", "").isdigit()

        if "%" in value and is_num:
            return 'percent'
        elif is_num:
            return 'float' if "." in value else 'int'
        return 'text'
    print(type(value))
    return 'other'

def inspect_column(heading, values):
    assert len(values) > 0
    kind, _ = Counter(guess_kind(v) for v in values).most_common(1)[0]

    data = dict(
        heading = heading,
    )

    if kind == 'text':
        counter = Counter(values)
        if len(counter) / len(values) < 0.5:
            kind = 'enum'
            data['options'] = sorted(counter.keys())
    data['kind'] = kind

    if kind == 'int':
        for i in range(len(values)):
            values[i] = int(str(values[i]).replace(",", ""))
    elif kind in ('float', 'percent'):
        for i in range(len(values)):
            try:
                values[i] = float(str(values[i]).replace("%", ""))
            except ValueError:
                values[i] = float('NaN')
    if kind in ('int', 'float'):
        data['min'] = min(values)
        data['max'] = max(values)
    return data


def read_spreadsheet(file_type, stream, session):
    sheet = get_sheet(file_type, stream)
    headings = sheet.colnames
    records = sheet.to_records()

    # TODO tag headings with what their data looks like
    columns = list(sheet.columns())
    headings = [inspect_column(h, c) for h, c in zip(headings, columns)]

    # Assume first column is Country
    # TODO pick first TEXT column
    index = 0
    headings[index]['is_region'] = True
    country_names = columns[index]
    del columns
    print(country_names)

    regions = gather_regions(country_names, session)

    not_found = [query for query, region in regions if region is None]
    # TODO complain about the ones we couldn't find

    out = []
    for row, region in zip(sheet.rows(), regions):
        query, region = region
        out.append(dict(
            row = row,
            query = query,
            region = region,
        ))

    return dict(
        headings = headings,
        records = out,
    )




if __name__ == '__main__':
    from pprint import pprint
    out = query_osm("georgia")
    pprint(out)
    print(out['simple_path'])

