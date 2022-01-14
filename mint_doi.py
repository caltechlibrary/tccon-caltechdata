import os, argparse

from caltechdata_api import get_metadata
from datacite import DataCiteRESTClient, schema43

parser = argparse.ArgumentParser(
    description="Mint a DOI for a TCCON record in CaltechDATA"
)

parser.add_argument(
    "ids",
    metavar="ID",
    type=int,
    nargs="+",
    help="The CaltechDATA ID for each record",
)

args = parser.parse_args()

url = "https://data.caltech.edu/records/"

password = os.environ["DATACITE"]

d = DataCiteRESTClient(username="CALTECH.LIBRARY", password=password, prefix="10.14291")

for idv in args.ids:

    metadata = get_metadata(idv, schema="43")

    doi = metadata["identifiers"][0]["identifier"]

    doi = d.public_doi(metadata, url + str(idv), doi=doi)

    print(doi)
