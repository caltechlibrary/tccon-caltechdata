#from mint_doi import mint_doi
from caltechdata_api import caltechdata_edit
from caltechdata_api import caltechdata_write
import os, json, argparse, subprocess, glob, datetime, requests, copy

#Switch for test or production
production = False
#Location where TCCON metadata application puts its files
metadata_path = '/var/www/tccon-metadata/'
#TCCON Site Info File Name
site_info_fname = 'site_info.json'
#DOI Metatata Location
doi_metadata = '/var/www/tccon-metadata/doi-metadata/'
#Data File Location
data_location = '/data/tccon/3a-std-public/'

token = os.environ['RDMTOK']
password = os.environ['DATACITE']

parser = argparse.ArgumentParser(description=\
        "Upload a new TCCON site to CaltechDATA")
parser.add_argument('sid', metavar='ID', type=str,nargs='+',\
                    help='The TCCON two letter Site ID (e.g. pa for park falls)')
args = parser.parse_args()

#For each new site release
for skey in args.sid:
    #Get data file
    sitef = glob.glob(f'{data_location}{skey}*.nc')
    if len(sitef) != 1:
        print(f"Cannot find public file for site {skey} in {data_location}")
        exit()
    else:
        sitef = sitef[0]

    #Prep metadata
    site_file = open(metadata_path + site_info_fname,'r')
    tccon_sites = json.load(site_file)
    site_info = tccon_sites[skey]
    site_name = site_info['long_name']
    site_doi = site_info['data_doi']
    #Get contact information from form "name <email>"
    site_contact = site_info['contact']
    split_contact = site_contact.split('<')
    contact_name = split_contact[0]
    contact_email = split_contact[1].split('>')[0]
    
    #Get Metadata for DOI
    meta_file = open(f'{doi_metadata}{skey}_{site_name}.json','r')
    metadata = json.load(meta_file)

    #Dates
    today = datetime.date.today().isoformat()
    sfname = sitef.split('3a-std-public/')[1]
    cred = sfname[2:6]+'-'+sfname[6:8]+'-'+sfname[8:10]+\
                    '/'+sfname[11:15]+'-'+sfname[15:17]+'-'+sfname[17:19]
    metadata['dates'] = [{'dateType':'Collected','date':cred},\
            {'dateType':'Updated','date':today},\
            {'dateType':'Created','date':today}]
    metadata['publicationDate'] = today

    #Standard cleanup
    metadata.pop("__last_modified__")
    metadata["fundingReferences"] = metadata.pop("FundingReference")
    metadata["identifiers"] = [
        {"identifierType": "DOI", "identifier":site_doi}
    ]
    metadata["publisher"] = "CaltechDATA"
    metadata["types"] = {"resourceTypeGeneral": "Dataset", "resourceType": "Datset"}
    metadata["schemaVersion"] = "http://datacite.org/schema/kernel-4"

    #Add contributor email
    contributors = metadata['contributors']
    contributors.append({'contributorType':'ContactPerson',\
            'contributorEmail':contact_email,'name':contact_name})

    #Generate README file
    outf = open('README.txt','w')
    subprocess.run(['./create_readme_contents_tccon-data',sitef],check=True,stdout=outf)

    #Generate new license
    lic_f = open("license-start.txt","r")
    lic_t = open("license-end.txt","r")
    lic = lic_f.read()
    cite = site_info['data_reference']
    lic = lic + cite
    lic = lic + '\n\n' + lic_t.read()
    outf = open('LICENSE.txt','w')
    outf.write(lic)
    outf.close()

    #Files to be uploaded
    files = ['README.txt','LICENSE.txt',sitef]

    doi = metadata['identifiers'][0]['identifier']

    response = caltechdata_write(metadata,token,files,production,schema="43")
    print(response)
    rec_id = response.split('/')[4].split('.')[0]
    print(rec_id)

    #Get file url
    if production == False:
        api_url = 'https://cd-sandbox.tind.io/api/record/'
    else:
        api_url = 'https://data.caltech.edu/api/record/'
    response = requests.get(api_url+rec_id)
    ex_metadata = response.json()['metadata']
    for f in ex_metadata['electronic_location_and_access']:
        if f['electronic_name'][0]=='LICENSE.txt':
            url = f['uniform_resource_identifier']

    metadata['rightsList'] = [{'rightsURI':url,'rights':'TCCON Data License'}]

    response = caltechdata_edit(rec_id,copy.deepcopy(metadata),token,{},{},production,schema="43")
    print(response)

    if production == False:
        doi='10.33569/TCCON'
        url = 'https://cd-sandbox.tind.io'
        datacite = DataCiteRESTClient(username="CALTECH.LIBRARY", password=password,
                prefix="10.33569",test_mode=True)
    else:
        url = 'https://data.caltech.edu'
        datacite = DataCiteRESTClient(username="CALTECH.LIBRARY", password=password,
                prefix="10.14291")

    #Strip contributor emails
    for c in metadata['contributors']:
            if 'contributorEmail' in c:
                c.pop('contributorEmail')
    if 'publicationDate' in metadata:
        metadata.pop('publicationDate')

    doi = d.public_doi(metadata, url + str(idv), doi=doi)
    print(doi)

