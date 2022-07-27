from caltechdata_api import caltechdata_edit
from caltechdata_api import caltechdata_write
from caltechdata_api import decustomize_schema
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

    # Get existing metadata
    rec_id = ids[site_name]
    if production == False:
        api_url = "https://cd-sandbox.tind.io/api/record/"
    else:
        api_url = "https://data.caltech.edu/api/record/"
    response = requests.get(api_url + rec_id)
    ex_metadata = response.json()["metadata"]
    for f in ex_metadata["electronic_location_and_access"]:
        if f["electronic_name"][0] == "LICENSE.txt":
            url = f["uniform_resource_identifier"]
        if f["electronic_name"][0] == "README.txt":
            r = requests.get(f["uniform_resource_identifier"])
            readme = r.text

    metadata = decustomize_schema(ex_metadata, pass_emails=True, schema="43")

    meta = {
        "relatedIdentifier": new_identifier,
        "relationType": "IsPreviousVersionOf",
        "relatedIdentifierType": "DOI",
    }
    metadata["relatedIdentifiers"].append(meta)

    metadata["descriptions"].append(
        {
            "description": f"""These data are now obsolete
    and should be replaced by the most recent data:<br><br>
    https://doi.org/{site_doi}""",
            "descriptionType": "Other",
        }
    )

    # Update the README file
    readme = f"""This file is obsolete.  An updated version is available at 
                https://doi.org/{site_doi}\n\n"""
    readme += check_output(["./create_readme_contents_tccon-data", sitef])
    outfile = open("README.txt", "w")
    outfile.write(readme)
    outfile.close()

    response = caltechdata_edit(
        token, rec_id, copy.deepcopy(metadata), ["README.txt"], [], production
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

    datacite.update_doi(doi, metadata)

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
    metadata["types"] = {"resourceTypeGeneral": "Dataset", "resourceType": "Datset"}
    metadata["schemaVersion"] = "http://datacite.org/schema/kernel-4"
    metadata["version"] = version
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

    # Add contributor email
    contributors = metadata["contributors"]
    contributors.append(
        {
            "contributorType": "ContactPerson",
            "contributorEmail": contact_email,
            "name": contact_name,
        }
    )

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

    doi = metadata["identifiers"][0]["identifier"]

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

    doi = datacite.public_doi(metadata, url + str(rec_id), doi=doi)
    print(doi)

    # Update sites file
    infile = open("/data/tccon/site_ids.csv")
    site_ids = csv.reader(infile)
    for row in site_ids:
        if row[0] == site_name:
            outstr = site_name + "," + rec_id + "," + version + "\n"
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
