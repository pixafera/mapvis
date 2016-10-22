import pyexcel

from party import gather_regions

def read_spreadsheet(file_name, contents):
    sheet = pyexcel.get_sheet(file_type='xlsx', file_stream=contents, name_columns_by_row=0)
    headings = sheet.colnames
    records = sheet.to_records()

    # Assume first column is Country
    country_names = [record[headings[0]] for record in records]

    regions = gather_regions(country_names)

    not_found = [query for query, region in regions if region is None]
    # TODO complain about the ones we couldn't find

    return [r[0] for q, r in regions if r is not None]

    for record, region in zip(records, regions):
        # TODO party!
        pass