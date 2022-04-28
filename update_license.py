import os, json, csv, glob
from caltechdata_api import caltechdata_edit
from caltechdata_api import caltechdata_write
from caltechdata_api import get_metadata
from datacite import DataCiteRESTClient, schema43
import datetime, requests, copy

data_url = "https://data.caltech.edu/records/"

token = os.environ["RDMTOK"]
password = os.environ["DATACITE"]

d = DataCiteRESTClient(username="CALTECH.LIBRARY", password=password, prefix="10.14291")

# Location where TCCON metadata application puts its files
metadata_path = "/var/www/tccon-metadata/"
# TCCON Site Info File Name
site_info_fname = "site_info.json"
# Data File Location
data_location = "/data/tccon/3a-std-public/"

# Read in site id file with CaltechDATA IDs
infile = open("/data/tccon/site_ids.csv")
site_ids = csv.reader(infile)
ids = {}
version = {}
for row in site_ids:
    long_name = row[0]
    record_id = row[1]
    version = row[2]

    # Prep metadata
    site_file = open(metadata_path + site_info_fname, "r")
    tccon_sites = json.load(site_file)
    for site in tccon_sites:
        if long_name == tccon_sites[site]["long_name"]:
            location = tccon_sites[site]["location"]
            citation = tccon_sites[site]["data_reference"]
            doi = tccon_sites[site]["data_doi"]

    metadata = get_metadata(record_id, schema="43", emails=True)

    metadata["descriptions"] = [
        {
            "descriptionType": "Other",
            "description": """The Total Carbon Column Observing Network (TCCON) is
    a network of ground-based Fourier Transform Spectrometers that record direct
    solar absorption spectra of the atmosphere in the near-infrared. From these
    spectra, accurate and precise column-averaged abundances of atmospheric
    constituents including CO2, CH4, N2O, HF, CO, H2O, and HDO, are retrieved. This
    is the GGG2020 data release of observations from the TCCON station at
    """
            + location,
        }
    ]

    # Dates
    today = datetime.date.today().isoformat()
    for date in metadata["dates"]:
        if date["dateType"] == "Updated":
            date["date"] = today

    # Generate new license
    lic_f = open("license-start.txt", "r")
    lic_t = open("license-end.txt", "r")
    lic = lic_f.read()
    lic = lic + citation
    lic = lic + "\n\n" + lic_t.read()
    outf = open("LICENSE.txt", "w")
    outf.write(lic)
    outf.close()

    # Files to be uploaded
    files = ["LICENSE.txt"]

    production = True

    response = caltechdata_edit(
        record_id, metadata, token, files, {}, production, schema="43"
    )
    print(response)

    # Get file url
    if production == False:
        api_url = "https://cd-sandbox.tind.io/api/record/"
    else:
        api_url = "https://data.caltech.edu/api/record/"
    response = requests.get(api_url + record_id)
    ex_metadata = response.json()["metadata"]
    for f in ex_metadata["electronic_location_and_access"]:
        if f["electronic_name"][0] == "LICENSE.txt":
            url = f["uniform_resource_identifier"]

    metadata["rightsList"] = [{"rightsUri": url, "rights": "TCCON Data License"}]

    response = caltechdata_edit(
        record_id, copy.deepcopy(metadata), token, {}, {}, production, schema="43"
    )
    print(response)

    # Strip contributor emails
    for c in metadata["contributors"]:
        if "contributorEmail" in c:
            c.pop("contributorEmail")
    if "publicationDate" in metadata:
        metadata.pop("publicationDate")

    doi = d.update_doi(doi, metadata)

    print(doi)
