
from collections import Counter
import io
import itertools
import json
import os
import random
import string

import chardet
import pyexcel
import grequests
import sqlalchemy.orm
import svg.path

import model


#------------------------------------------------------------------------------
# query & cache OSM

class OsmBoundary(object):
    def __init__(self, **kwargs):
        self.osm_id = int(kwargs['osm_id'])
        self.name = kwargs['display_name']
        self.place_rank = kwargs['place_rank']
        self.simple_path = kwargs['svg']
        self.lat = kwargs['lat']
        self.lon = kwargs['lon']
        self.boundingbox = list(map(float, kwargs['boundingbox']))
        self.importance = kwargs['importance']

    def to_json(self):
        return json.dumps(dict(osm_id=self.osm_id,
                               name=self.name,
                               place_rank=self.place_rank,
                               simple_path=self.simple_path,
                               lat=self.lat,
                               lon=self.lon,
                               boundingbox=self.boundingbox))

def query_osm(queries):
    def set_meta(meta):
        def hook(r, **kwargs):
            r.meta = meta
            return r
        return hook

    reqs = [grequests.get("http://nominatim.openstreetmap.org/search",
                          params=dict(format = 'jsonv2',
                                      q = query,
                                      limit = 5,
                                      polygon_svg=1),
                          callback=set_meta(query))
            for query in queries]

    for r in grequests.imap(reqs, size=12):

        results = r.json()

        boundaries = [item for item in results if item['category'] == 'boundary']

        print("Found {} boundaries".format(len(boundaries)))

        # # Arbitrarily pick the first one -- OSM seems to sort them by importance?
        # boundary = boundaries[0]

        # Only keep a few fields
        reduced_boundaries = []
        for boundary in boundaries:
            boundary['svg'] = simplify_paths(boundary['svg'])
            reduced_boundaries.append(OsmBoundary(**boundary))
        yield r.meta, reduced_boundaries

def simplify_paths(paths):
    paths = svg.path.parse_path(paths)
    precision = 1
    new_path = svg.path.Path()
    for l in paths:
        x1 = round(l.start.real, precision)
        y1 = round(l.start.imag, precision)
        x2 = round(l.end.real, precision)
        y2 = round(l.end.imag, precision)
        if x1 == x2 and y1 == y2:
            continue
            
        new_path.append(svg.path.Line(start=complex(x1, y1), end=complex(x2, y2)))
    if len(new_path) == 0:
        return ''
    else:
        return new_path.d()

def simplify_segment(svg):
    words = svg.split(" ")

    # Keep first four items & last item
    assert words[0] == 'M'
    assert words[3] == 'L'
    assert words[-1] == 'Z'
    first = ['M', words[1], words[2], 'L']
    last = ['Z']

    assert len(words[4:-1]) % 2 == 0

    precision = 1
    pairs = [(round(float(words[i]), precision), round(float(words[i+1]), precision)) for i in range(4, len(words) - 2, 2)]

    # Keep N points
    last_point = (round(float(words[1]), precision), round(float(words[2]), precision))
    selected = [last_point]
    for point in pairs:
        if point == last_point:
            continue

        last_point = point
        selected.append(point)

    selected = " ".join("{} {}".format(p) for p in selected)

    return " ".join(first + selected + last)


def fetch_queries(queries, session):
    """Create a Query and associated Regions"""

    for query, boundary in query_osm(queries):
        regions = {r.osm_id: r for r in session.query(model.Region).filter(model.Region.osm_id.in_(b.osm_id for b in boundary))}

        # Make regions
        for b in boundary:
            if b.osm_id in regions:
                continue

            r = model.Region(osm_id=b.osm_id, place_rank=b.place_rank, json=b.to_json())
            regions[r.osm_id] = r
            session.add(r)
        session.commit()

        q = model.Query(search_string=query)
        for b in boundary:
            q.regions.append(model.QueryRegion(query=q, region=regions[b.osm_id], importance=b.importance))
        session.add(q)
        session.commit()

        yield q


def gather_regions(query_list, session):
    """Take a list of queries and return a set of similar Regions"""
    results = []
    db_queries = session.query(model.Query).filter(model.Query.search_string.in_(query_list)).options(sqlalchemy.orm.joinedload(model.Query.regions))
    db_query_lookup = {q.search_string: q for q in db_queries}

    queries_to_osm = [q for q in query_list if q not in db_query_lookup]
    print('{} queries to OSM'.format(len(queries_to_osm)))
    if len(queries_to_osm) > 0:
        for q in fetch_queries(queries_to_osm, session):
            db_query_lookup[q.search_string] = q

    # What place_rank are we looking for?
    place_rank_counter = Counter(itertools.chain(*(set(r.region.place_rank for r in q.regions) for q in db_query_lookup.values())))
    print(place_rank_counter)
    modal_place_rank = place_rank_counter.most_common(1)[0][0]

    def get_best_region_json(q):
        best_region = next(iter(sorted((r for r in q.regions if r.region.place_rank == modal_place_rank), key=lambda r:r.importance)), None)

        if best_region is None:
            best_region = next(iter(sorted(q.regions, key=lambda r:r.importance)), None)

        return json.loads(best_region.region.json) if best_region is not None else None

    # for now, return only the first Region
    results = {q: get_best_region_json(b) for q, b in db_query_lookup.items()}

    return results


#------------------------------------------------------------------------------
# read spreadsheet

def get_sheet(file_type, stream):
    if file_type in ('csv', 'tsv'):
        raw = stream.read()
        det = chardet.detect(raw)
        stream = io.StringIO(raw.decode(det['encoding']))
    return pyexcel.get_sheet(
        file_type=file_type,
        file_stream=stream,
        name_columns_by_row=0, # First row is headings
        auto_detect_int=False,   #- Excel ignores these :-(
        auto_detect_float=False, #
    )

def guess_kind(value):
    # TODO testcases for this!
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
    counter = Counter(guess_kind(v) for v in values)
    kind, _ = counter.most_common(1)[0]

    data = dict(
        heading = heading,
    )

    if kind == 'int' and 'float' in counter:
        kind = 'float'
    if kind == 'text':
        counter = Counter(values)
        if len(counter) / len(values) < 0.5:
            kind = 'enum'
            data['options'] = sorted(counter.keys())
    data['kind'] = kind

    if kind in ('int', 'float'):
        if kind == 'int':
            for i in range(len(values)):
                values[i] = int(str(values[i]).replace(",", ""))
            compare = values
        elif kind in ('float', 'percent'):
            compare = []
            for i in range(len(values)):
                try:
                    values[i] = float(str(values[i]).replace("%", ""))
                    compare.append(values[i])
                except ValueError:
                    pass #values[i] = float('NaN')
        data['min'] = min(compare)
        data['max'] = max(compare)
    return data


def read_spreadsheet(file_type, stream, session):
    sheet = get_sheet(file_type, stream)
    headings = sheet.colnames

    # TODO tag headings with what their data looks like
    columns = list(sheet.columns())
    headings = [inspect_column(h, c) for h, c in zip(headings, columns)]

    # Assume first column is Country
    # TODO pick first column of kind 'text'
    index = 0
    headings[index]['is_region'] = True
    country_names = columns[index]
    del columns
    print(country_names)

    regions = gather_regions(country_names, session)

    #not_found = [query for query, region in regions if region is None]
    # TODO complain about regions with zero search results

    out = []
    for row in sheet.rows():
        query = row[index]
        region = regions[query]
        out.append(dict(
            row = row,
            region_osm_id = region['osm_id'] if region else None,
            query = query, # redundant but oh well
        ))


    # normally bbox = left,bottom,right,top
    # but Nominatim gives south,north,west,east
    bboxes = [region['boundingbox'] for region in regions.values() if region]
    bot = min(bot for bot, top, left, right in bboxes)
    top = max(top for bot, top, left, right in bboxes)
    left = min(left for bot, top, left, right in bboxes)
    right = max(right for bot, top, left, right in bboxes)
    assert bot < top
    assert left < right
    print([bot, top, left, right])

    return dict(
        headings = headings,
        records = out,
        bbox = [bot, top, left, right],
    )


def generate_dataset_id():
    return ''.join(string.ascii_lowercase[random.randint(0, 24)] for i in range(6))


if __name__ == '__main__':
    from pprint import pprint
    out = query_osm("georgia")
    pprint(out)
    print(out['simple_path'])

