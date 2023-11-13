from caltechdata_api import caltechdata_edit
from caltechdata_api import caltechdata_write
from upload_files import upload_files
from datacite import DataCiteRESTClient
from subprocess import check_output
import os, csv, json, subprocess, argparse, glob, datetime, requests, copy

# Switch for test or production
production = True
# Location where TCCON metadata application puts its files
metadata_path = "/var/www/tccon-metadata/"
# TCCON Site Info File Name
site_info_fname = "site_info.json"
# DOI Metatata Location
doi_metadata = "/var/www/tccon-metadata/doi-metadata/"
# Data File Location
data_location = "/data/tccon/3a-std-public/"

token = os.environ["RDMTOK"]
password = os.environ["DATACITE"]

# Read in site id file with CaltechDATA IDs
infile = open("/data/tccon/site_ids.csv")
site_ids = csv.reader(infile)
ids = {}
version = {}
for row in site_ids:
    ids[row[0]] = row[1]
    version[row[0]] = row[2]

parser = argparse.ArgumentParser(description="Upload a new TCCON site to CaltechDATA")
parser.add_argument(
    "sid",
    metavar="ID",
    type=str,
    nargs="+",
    help="The TCCON two letter Site ID (e.g. pa for park falls)",
)
args = parser.parse_args()

# For each new site release
for skey in args.sid:

    # Prep metadata
    site_file = open(metadata_path + site_info_fname, "r")
    tccon_sites = json.load(site_file)
    site_info = tccon_sites[skey]
    site_name = site_info["long_name"]
    site_doi = site_info["data_doi"]
    version = site_info["data_revision"]
    location = tccon_sites[skey]["location"]
    # Get contact information from form "name <email>"
    site_contact = site_info["contact"]
    split_contact = site_contact.split("<")
    contact_name = split_contact[0]
    contact_email = split_contact[1].split(">")[0]

    # Existing record
    rec_id = ids[site_name]

    # Create new site record
    # Get data file
    sitef = glob.glob(f"{data_location}{skey}*.nc")
    if len(sitef) != 1:
        print(f"Cannot find public file for site {skey} in {data_location}")
        exit()
    else:
        sitef = sitef[0]

    # Get Metadata for DOI
    meta_file = open(f"{doi_metadata}{skey}_{site_name}.json", "r")
    metadata = json.load(meta_file)

    # Dates
    today = datetime.date.today().isoformat()
    sfname = sitef.split("3a-std-public/")[1]
    cred = (
        sfname[2:6]
        + "-"
        + sfname[6:8]
        + "-"
        + sfname[8:10]
        + "/"
        + sfname[11:15]
        + "-"
        + sfname[15:17]
        + "-"
        + sfname[17:19]
    )
    metadata["dates"] = [
        {"dateType": "Collected", "date": cred},
        {"dateType": "Updated", "date": today},
        {"dateType": "Created", "date": today},
    ]
    metadata["publicationDate"] = today
    year = today.split("-")[0]
    metadata["publicationYear"] = year

    # Standard cleanup
    metadata.pop("__last_modified__")
    metadata["fundingReferences"] = metadata.pop("FundingReference")
    metadata["identifiers"] = [{"identifierType": "DOI", "identifier": site_doi}]
    metadata["publisher"] = "CaltechDATA"
    metadata["types"] = {"resourceTypeGeneral": "Dataset", "resourceType": "Dataset"}
    metadata["schemaVersion"] = "http://datacite.org/schema/kernel-4"
    metadata["version"] = version
    metadata["descriptions"] = [
        {
            "descriptionType": "Abstract",
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
    metadata["subjects"] = [
        {"subject": "atmospheric trace gases"},
        {"subject": "CO2"},
        {"subject": "CH4"},
        {"subject": "CO"},
        {"subject": "N2O"},
        {"subject": "column-averaged dry-air mole fractions"},
        {"subject": "remote sensing"},
        {"subject": "FTIR spectroscopy"},
        {"subject": "TCCON"},
    ]

    for cont in metadata["contributors"]:
        if cont["contributorType"] == "HostingInstitution":
            cont["nameType"] = "Organizational"
        if cont["contributorType"] == "ResearchGroup":
            cont["nameType"] = "Organizational"
        if cont["contributorType"] == "ContactPerson":
            cont["contributorEmail"] = contact_email

    license_url = (
        f"https://renc.osn.xsede.org/ini210004tommorrell/{site_doi}/LICENSE.txt"
    )
    metadata["rightsList"] = [
        {"rightsUri": license_url, "rights": "TCCON Data License"}
    ]

    # Generate README file
    outf = open("README.txt", "w")
    subprocess.run(
        ["./create_readme_contents_tccon-data", sitef], check=True, stdout=outf
    )

    # Generate new license
    lic_f = open("license-start.txt", "r")
    lic_t = open("license-end.txt", "r")
    lic = lic_f.read()
    cite = site_info["data_reference"]
    lic = lic + cite
    lic = lic + "\n\n" + lic_t.read()
    outf = open("LICENSE.txt", "w")
    outf.write(lic)
    outf.close()

    # Files to be uploaded
    files = ["README.txt", "LICENSE.txt", sitef]

    community = "2dc56d1f-b31b-4b57-9e4a-835f751ae1e3"

    file_links = upload_files(files, site_doi)

    response = caltechdata_edit(
        rec_id,
        metadata,
        token,
        [],
        production,
        schema="43",
        publish=True,
        file_links=file_links,
        new_version=True,
    )
    print(response)

    if production == False:
        doi = "10.33569/TCCON"
        url = "https://cd-sandbox.tind.io/records/"
        datacite = DataCiteRESTClient(
            username="CALTECH.LIBRARY",
            password=password,
            prefix="10.33569",
            test_mode=True,
        )
    else:
        url = "https://data.caltech.edu/records/"
        datacite = DataCiteRESTClient(
            username="CALTECH.LIBRARY", password=password, prefix="10.14291"
        )

    # Strip contributor emails
    for c in metadata["contributors"]:
        if "contributorEmail" in c:
            c.pop("contributorEmail")
    if "publicationDate" in metadata:
        metadata.pop("publicationDate")

    doi = datacite.public_doi(metadata, url + str(rec_id), doi=site_doi)
    print(doi)

    # Update sites file
    infile = open("/data/tccon/site_ids.csv")
    site_ids = csv.reader(infile)
    outstr = ""
    for row in site_ids:
        if row[0] == site_name:
            outstr = outstr + site_name + "," + rec_id + "," + version + "\n"
        else:
            outstr = outstr + ",".join(row) + "\n"
    infile.close()

    if production == True:
        os.rename("/data/tccon/site_ids.csv", "/data/tccon/old_site_ids.csv")
        out_id = open("/data/tccon/site_ids.csv", "w")
        out_id.write(outstr)
        out_id.close()

    # Update site list - assumes new sites are in alphabetical order

    # Generate site text
    for t in metadata["titles"]:
        if "titleType" not in t:
            title = t["title"].split("from")[1].split(",")[0].strip()
    split = cred.split("/")
    first = split[0]
    second = split[1]
    outsites = f"{title} [{site_name}],https://doi.org/{doi},{first},{second}\n"

    existing = open("/data/tccon/sites.csv", "r")
    sites = csv.reader(existing)
    outstr = ""
    for row in sites:
        if row[0] == f"{title} [{site_name}]":
            outstr = outstr + outsites
        else:
            outstr = outstr + ",".join(row) + "\n"
    os.rename("/data/tccon/sites.csv", "/data/tccon/old_sites.csv")
    outsites = open("/data/tccon/sites.csv", "w")
    outsites.write(outstr)
    outsites.close()
