import os,json

from caltechdata_api import get_metadata
from datacite import DataCiteRESTClient, schema43
import datetime

url = "https://data.caltech.edu/records/"

#password = os.environ["DATACITE"]

#d = DataCiteRESTClient(username="CALTECH.LIBRARY", password=password, prefix="10.14291")

metadata = get_metadata(293, schema="43",emails=True)

metadata["identifiers"] = [{"identifier":'10.14291/TCCON.GGG2020',"identifierType":"DOI"}]
metadata["version"] = "GGG2020"
metadata["titles"] = [{"title":"2020 TCCON Data Release"}]
metadata["descriptions"] = [{"descriptionType":"Other","description":"""The Total Carbon Column Observing Network (TCCON) is
a network of ground-based Fourier Transform Spectrometers that record direct
solar absorption spectra of the atmosphere in the near-infrared. From these
spectra, accurate and precise column-averaged abundances of atmospheric
constituents including CO2, CH4, N2O, HF, CO, H2O, and HDO, are retrieved. This
is the 220 data release."""}]
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
record_metadata = get_metadata(20093,schema="43")
for identifier in record_metadata["relatedIdentifiers"]:
    print(identifier)
metadata["relatedIdentifiers"] = identifiers

print(json.dumps(metadata))

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
    cite = site["data_reference"]
    lic = lic + cite
lic = lic + "\n\n" + lic_t.read()
print(lic)
#outf = open("LICENSE.txt", "w")
#outf.write(lic)
#outf.close()

#doi = d.public_doi(metadata, url + str(idv), doi=doi)

#print(doi)
