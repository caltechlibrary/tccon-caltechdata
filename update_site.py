from caltechdata_api import caltechdata_edit
from caltechdata_api import caltechdata_write
from datacite import DataCiteRESTClient
import os, csv, json, argparse, subprocess, glob, datetime, requests, copy


def update_site(skey):
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

    # Get data file
    sitef = glob.glob(f"{data_location}{skey}*.nc")
    if len(sitef) != 1:
        print(f"Cannot find public file for site {skey} in {data_location}")
        exit()
    else:
        sitef = sitef[0]

    # Prep metadata
    site_file = open(metadata_path + site_info_fname, "r")
    tccon_sites = json.load(site_file)
    site_info = tccon_sites[skey]
    site_name = site_info["long_name"]
    site_doi = site_info["data_doi"]
    version = site_info["data_revision"]
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
    for date in ex_metadata["relevantDates"]:
        if date["relevantDateType"] == "Created":
            created = ex_metadata["relevantDateValue"]
    descriptions = ex_metadata["descriptions"]
    for d in descriptions:
        d["description"] = d.pop("descriptionValue")

    # Get Metadata for DOI
    meta_file = open(f"{doi_metadata}{skey}_{site_name}.json", "r")
    metadata = json.load(meta_file)

    # Retain CaltechDATA Descriptions
    metadata["descriptions"] = descriptions

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
        {"dateType": "Created", "date": created},
        {"dateType": "Collected", "date": cred},
        {"dateType": "Updated", "date": today},
    ]

    # Standard cleanup
    metadata.pop("__last_modified__")
    metadata["fundingReferences"] = metadata.pop("FundingReference")
    metadata["identifiers"] = [{"identifierType": "DOI", "identifier": site_doi}]
    metadata["publisher"] = "CaltechDATA"
    metadata["types"] = {"resourceTypeGeneral": "Dataset", "resourceType": "Datset"}
    metadata["schemaVersion"] = "http://datacite.org/schema/kernel-4"
    metadata["version"] = version
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

    # Files to be uploaded
    files = ["README.txt", sitef]

    doi = metadata["identifiers"][0]["identifier"]

    metadata["rightsList"] = [{"rightsUri": url, "rights": "TCCON Data License"}]

    response = caltechdata_edit(
        rec_id, metadata, token, files, {}, production, schema="43"
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

    # Update site list

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
        if title.startswith(row[0]):
            outstr = outstr + outsites
        else:
            outstr = outstr + ",".join(row) + "\n"
    os.rename("/data/tccon/sites.csv", "/data/tccon/old_sites.csv")
    outsites = open("/data/tccon/sites.csv", "w")
    outsites.write(outstr)
    outsites.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Update TCCON site in CaltechDATA")
    parser.add_argument(
        "sid",
        metavar="ID",
        type=str,
        nargs="+",
        help="The TCCON two letter Site ID (e.g. pa for park falls)",
    )
    args = parser.parse_args()

    # For each site to update
    for skey in args.sid:
        update_site(skey)
