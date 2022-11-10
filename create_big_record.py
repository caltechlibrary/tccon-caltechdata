import os, json
from caltechdata_api import caltechdata_edit
from caltechdata_api import caltechdata_write
from caltechdata_api import get_metadata
from datacite import DataCiteRESTClient, schema43
import datetime, requests, copy
from upload_files import upload_files

data_url = "https://data.caltech.edu/records/"

token = os.environ["RDMTOK"]
password = os.environ["DATACITE"]

d = DataCiteRESTClient(username="CALTECH.LIBRARY", password=password, prefix="10.14291")

metadata = get_metadata("6nt42-tqn74", schema="43", emails=True)

doi = "10.14291/TCCON.GGG2020"

metadata["identifiers"] = [{"identifier": doi, "identifierType": "DOI"}]
metadata["version"] = "GGG2020"
metadata["titles"] = [{"title": "2020 TCCON Data Release"}]
# Dates
today = datetime.date.today().isoformat()
metadata["dates"] = [
    {"dateType": "Updated", "date": today},
    {"dateType": "Created", "date": today},
]
metadata["publicationDate"] = today
year = today.split("-")[0]
metadata["publicationYear"] = year

license_url = "https://renc.osn.xsede.org/ini210004tommorrell/{site_doi}/LICENSE.txt"
metadata["rightsList"] = [{"rightsUri": license_url, "rights": "TCCON Data License"}]

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
community = "2dc56d1f-b31b-4b57-9e4a-835f751ae1e3"

file_links = upload_files(files, doi)

response = caltechdata_write(
    metadata,
    token,
    [],
    production,
    schema="43",
    publish=True,
    file_links=file_links,
    community=community,
)

# Strip contributor emails
for c in metadata["contributors"]:
    if "contributorEmail" in c:
        c.pop("contributorEmail")
if "publicationDate" in metadata:
    metadata.pop("publicationDate")

doi = d.update_doi(doi, metadata, data_url + str(response))

print(doi)
