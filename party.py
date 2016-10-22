
import random

import requests


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
        return dict(
            # Key cached objects based on OSM id
            # -- make sure we don't cache 'em more than once
            osm_id = boundary['osm_id'],

            # Can display in the UI
            name = boundary['display_name'],

            # default SVG paths are too detailed to store/render!
            simple_path = simplify_path(boundary['svg']),

            # Might want to keep the centre
            lat = boundary['lat'],
            lon = boundary['lon'],
        )

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


def fetch_query(query):
    """Create a Query and associated Regions"""

    regions = []
    results = list()
    for boundary in query_osm(query):
        regions.append(...) # create Region object

    query = ... # create Query object
    # link 'em via the M2M

    return boundaries


def gather_regions(query_list):
    """Take a list of queries and return a set of similar Regions"""
    results = []
    for query in query_list:
        #if "Query object exists in DB":
            # get all related Regions via the M2M.
        #    boundaries = ... # db lookup
        #else:
        boundaries = query_osm(query)  #fetch_query(query)
        results.append((query, boundaries))

    # decide the most popular place_rank from the results
    # return a list of results with equal place_rank (as far as possible)


if __name__ == '__main__':
    from pprint import pprint
    out = query_osm("georgia")
    pprint(out)
    print(out['simple_path'])

