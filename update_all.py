import os, json, csv, glob
from caltechdata_api import caltechdata_edit
from caltechdata_api import caltechdata_write
from caltechdata_api import get_metadata
from datacite import DataCiteRESTClient, schema43
import datetime, requests, copy
import update_site

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
            short_name = site
            location = tccon_sites[site]["location"]
            citation = tccon_sites[site]["data_reference"]
            doi = tccon_sites[site]["data_doi"]

    update_site(short_name)
