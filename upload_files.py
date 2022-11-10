import os
import boto3
import urllib.request

KB = 1024
MB = KB * KB

def upload_files(files, folder):

    key = os.environ["OSN_KEY"]
    secret = os.environ["OSN_SECRET"]

    file_links = []

    path = "caltechdata"
    endpoint = "https://renc.osn.xsede.org/"
    s3 = boto3.client("s3", endpoint_url=endpoint,aws_access_key_id=key,aws_secret_access_key=secret)
    bucket = "ini210004tommorrell"

    #Delete existing .nc files
    response = s3.list_objects_v2(Bucket=bucket, Prefix=folder)
    if 'Contents' in response:
        for objectn in response['Contents']:
            if '.nc' in objectn['Key']:
                print('Deleting', objectn['Key'])
                s3_client.delete_object(Bucket=BUCKET, Key=objectn['Key'])

    print(files)
    for filen in files:
        if '/' in filen:
            file_name = filen.split('/')[-1]
        else:
            file_name = filen
        print(filen)
        s3.upload_file(filen, bucket, f"{folder}/{file_name}")
        link = f'{endpoint}{bucket}/{folder}/{file_name}'
        file_links.append(link)

    print(file_links)
    return file_links
