import os, json
from caltechdata_api import caltechdata_edit
from caltechdata_api import caltechdata_write
from caltechdata_api import get_metadata
from datacite import DataCiteRESTClient, schema43
import datetime, requests, copy

data_url = "https://data.caltech.edu/records/"

token = os.environ["RDMTOK"]
password = os.environ["DATACITE"]

d = DataCiteRESTClient(username="CALTECH.LIBRARY", password=password, prefix="10.14291")

metadata = get_metadata(293, schema="43", emails=True)

doi = "10.14291/TCCON.GGG2020"

metadata["identifiers"] = [{"identifier": doi, "identifierType": "DOI"}]
metadata["version"] = "GGG2020"
metadata["titles"] = [{"title": "2020 TCCON Data Release"}]
metadata["descriptions"] = [
    {
        "descriptionType": "Other",
        "description": """The Total Carbon Column Observing Network (TCCON) is
a network of ground-based Fourier Transform Spectrometers that record direct
solar absorption spectra of the atmosphere in the near-infrared. From these
spectra, accurate and precise column-averaged abundances of atmospheric
constituents including CO2, CH4, N2O, HF, CO, H2O, and HDO, are retrieved. This
is the 220 data release.""",
    }
]
# Dates
today = datetime.date.today().isoformat()
metadata["dates"] = [
    {"dateType": "Updated", "date": today},
    {"dateType": "Created", "date": today},
]
metadata["publicationDate"] = today
year = today.split("-")[0]
metadata["publicationYear"] = year

identifiers = []
record_metadata = get_metadata(20093, schema="43")
for identifier in record_metadata["relatedIdentifiers"]:
    if identifier['relationType'] != 'IsPartOf':
        identifiers.append(identifier)
metadata["relatedIdentifiers"] = identifiers

# Generate new license
lic_f = open("license-start.txt", "r")
lic_t = open("license-end.txt", "r")
lic = lic_f.read()

# Location where TCCON metadata application puts its files
metadata_path = "/var/www/tccon-metadata/"
# TCCON Site Info File Name
site_info_fname = "site_info.json"
site_file = open(metadata_path + site_info_fname, "r")
tccon_sites = json.load(site_file)

for site in tccon_sites:
    cite = tccon_sites[site]["data_reference"] + "\n\n"
    lic = lic + cite
lic = lic + lic_t.read()

outf = open("LICENSE.txt", "w")
outf.write(lic)
outf.close()

# Files to be uploaded
files = ["LICENSE.txt", "/data/tccon/3a-std-public/tccon.latest.public.tgz"]
production = True

response = caltechdata_write(metadata, token, files, production, schema="43")
print(response)
rec_id = response.split("/")[4].split(".")[0]
print(rec_id)

# Get file url
if production == False:
    api_url = "https://cd-sandbox.tind.io/api/record/"
else:
    api_url = "https://data.caltech.edu/api/record/"
response = requests.get(api_url + rec_id)
ex_metadata = response.json()["metadata"]
for f in ex_metadata["electronic_location_and_access"]:
    if f["electronic_name"][0] == "LICENSE.txt":
        url = f["uniform_resource_identifier"]

metadata["rightsList"] = [{"rightsUri": url, "rights": "TCCON Data License"}]

response = caltechdata_edit(
    rec_id, copy.deepcopy(metadata), token, {}, {}, production, schema="43"
)
print(response)

# Strip contributor emails
for c in metadata["contributors"]:
    if "contributorEmail" in c:
        c.pop("contributorEmail")
if "publicationDate" in metadata:
    metadata.pop("publicationDate")

doi = d.public_doi(metadata, data_url + str(rec_id), doi=doi)

print(doi)
