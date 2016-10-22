
import io
import json
import os
import random

import chardet
import pyexcel
import grequests
import sqlalchemy.orm

import model


#------------------------------------------------------------------------------
# query & cache OSM


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
            reduced_boundaries.append(d)
        yield r.meta, reduced_boundaries

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

    #from collections import Counter
    #pprint(Counter(svg))

    # Keep N points
    limit = 150 # TODO tweak this
    try:
        indexes = random.sample(list(range(len(pairs))), limit)
        indexes.sort()
        selected = [" ".join(pairs[i]) for i in indexes]
    except ValueError:
        selected = [" ".join(p) for p in pairs]

    return " ".join(first + selected + last)


def fetch_queries(queries, session):
    """Create a Query and associated Regions"""

    for query, boundary in query_osm(queries):
        regions = {r.osm_id: r for r in session.query(model.Region).filter(model.Region.osm_id.in_(b['osm_id'] for b in boundary))}

        # Make regions
        for b in boundary:
            if b['osm_id'] in regions:
                continue

            r = model.Region(osm_id=b['osm_id'], place_rank=b['place_rank'], json=json.dumps(b))
            regions[r.osm_id] = r
            session.add(r)
        session.commit()

        q = model.Query(search_string=query)
        q.regions.extend(regions.values())
        session.commit()

        yield q


def gather_regions(query_list, session):
    """Take a list of queries and return a set of similar Regions"""
    results = []
    db_queries = session.query(model.Query).filter(model.Query.search_string.in_(query_list)).options(sqlalchemy.orm.joinedload(model.Query.regions))
    db_query_lookup = {q.search_string: q for q in db_queries}

    queries_to_osm = [q for q in query_list if q not in db_query_lookup]
    if len(queries_to_osm) > 0:
        for q in fetch_queries(queries_to_osm, session):
            db_query_lookup[q.search_string] = q

    # TODO decide the most popular place_rank from the results
    # TODO return a list of results with equal place_rank (as far as possible)

    # for now, return only the first Region
    results = {q: (None if len(b.regions) == 0 else json.loads(b.regions[0].json)) for q, b in db_query_lookup.items()}

    return results


#------------------------------------------------------------------------------
# read spreadsheet

def get_sheet(file_type, stream):
    if file_type == 'csv':
        raw = stream.read()
        det = chardet.detect(raw)
        stream = io.StringIO(raw.decode(det['encoding']))
    return pyexcel.get_sheet(file_type=file_type, file_stream=stream, name_columns_by_row=0)

def read_spreadsheet(file_type, stream, session):
    sheet = get_sheet(file_type, stream)
    headings = sheet.colnames
    records = sheet.to_records()

    # Assume first column is Country
    country_names = [record[headings[0]] for record in records]

    regions = gather_regions(country_names, session)

    #not_found = [query for query, region in regions if region is None]
    # TODO complain about the ones we couldn't find

    output = []
    for record in records:
        query = record[headings[0]]
        region = regions[record[headings[0]]]
        output.append(dict(
            row = record, # TODO actually don't use to_records()
            query = query,
            region = region,
        ))
    return dict(
        headings = headings,
        rows = output,
    )




if __name__ == '__main__':
    from pprint import pprint
    out = query_osm("georgia")
    pprint(out)
    print(out['simple_path'])

