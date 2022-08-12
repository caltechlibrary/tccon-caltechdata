import json, csv
from update_site import update_site

# Location where TCCON metadata application puts its files
metadata_path = "/var/www/tccon-metadata/"
# TCCON Site Info File Name
site_info_fname = "site_info.json"

# Read in site id file with CaltechDATA IDs
infile = open("/data/tccon/site_ids.csv")
site_ids = csv.reader(infile)
for row in site_ids:
    long_name = row[0]
    record_id = row[1]
    version = row[2]
    short_name = None

    # Get short name
    site_file = open(metadata_path + site_info_fname, "r")
    tccon_sites = json.load(site_file)
    for site in tccon_sites:
        if long_name == tccon_sites[site]["long_name"]:
            short_name = site

    update_site(short_name)
