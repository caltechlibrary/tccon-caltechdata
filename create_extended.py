from caltechdata_api import caltechdata_write
from datacite import DataCiteRESTClient
import os, csv, json, argparse, subprocess, glob, datetime, requests, copy
from upload_files import upload_files


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
    data_folder = "3b-expt-public/"
    data_location = f"/data/tccon/{data_folder}"

    token = os.environ["RDMTOK"]
    password = os.environ["DATACITE"]

    # Get data file
    sitef = glob.glob(f"{data_location}{skey}*.nc")
    if len(sitef) != 1:
        print(f"Cannot find public file for site {skey} in {data_location}")
        exit()
    else:
        sitef = sitef[0]
    print(sitef)

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

    # Switch to the extended DOI
    site_doi = site_doi.replace("p1.","p1.extended.")

    # Get Metadata for DOI
    meta_file = open(f"{doi_metadata}{skey}_{site_name}.json", "r")
    metadata = json.load(meta_file)

    metadata["descriptions"] = [
        {
            "descriptionType": "Abstract",
            "description": f"""The Total Carbon Column Observing Network (TCCON) is
    a network of ground-based Fourier Transform Spectrometers that record direct
    solar absorption spectra of the atmosphere in the near-infrared. From these
    spectra, accurate and precise column-averaged abundances of atmospheric
    constituents including CO2, CH4, N2O, HF, CO, H2O, and HDO, are retrieved. This
    is the GGG2020.1 extended data release of observations from the TCCON station at
    {location}. 

    This dataset includes additional products retrieved from a secondary detector. These products
    are still under active development; users are highly encouraged to engage with the 
    site PI and TCCON algorithm team throughout their work to ensure these products are used correctly.
    """
        }
    ]
    
    metadata["titles"][0]["title"] = metadata["titles"][0]["title"] + ", extended"

    # Dates
    today = datetime.date.today().isoformat()
    sfname = sitef.split(data_folder)[1]
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
        {"dateType": "Created", "date": today},
        {"dateType": "Collected", "date": cred},
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
    related = []
    for related_id in metadata["relatedIdentifiers"]:
        if related_id['relationType'] == 'IsCitedBy':
            print('Dropping citations')
        elif related_id['relationType'] == 'IsNewVersionOf':
            related_id['relationType'] = 'IsVariantFormOf'
            related.append(related_id)
        else:
            related.append(related_id)
    metadata["relatedIdentifiers"] = related

    # Add contributor email
    contributors = metadata["contributors"]
    existing = False
    last_contact = contact_name.split(" ")[1]
    first_contact = contact_name.split(" ")[0]
    for c in contributors:
        last = c["name"].split(",")[0]
        if last == last_contact:
            existing = True
            c["contributorEmail"] = contact_email

    if not existing:
        contributors.append(
            {
                "contributorType": "ContactPerson",
                "contributorEmail": contact_email,
                "familyName": last_contact,
                "givenName": first_contact,
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
    cite = site_info["data_reference"].replace("p1.","p1.extended.")
    lic = lic + cite
    lic = lic + "\n\n" + lic_t.read()
    outf = open("LICENSE.txt", "w")
    outf.write(lic)
    outf.close()

    # Files to be uploaded
    files = ["README.txt", "LICENSE.txt", sitef]
    
    # Upload files
    file_links = upload_files(files, site_doi)

    print(json.dumps(metadata))

    community = "2dc56d1f-b31b-4b57-9e4a-835f751ae1e3"

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

    print(response)
    rec_id = response

    if production == False:
        doi = "10.33569/TCCON"
        url = "https://data.caltechlibrary.dev/records/"
        datacite = DataCiteRESTClient(
            username="CALTECH.LIBRARY",
            password=password,
            prefix="10.33569",
            test_mode=True,
        )
    else:
        doi = site_doi
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
