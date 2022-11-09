import os
import boto3
import urllib.request
from progressbar import ProgressBar, FileTransferSpeed, Bar, Percentage, ETA, Timer

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
    for objectn in response['Contents']:
        if '.nc' in objectn['Key']:
            print('Deleting', objectn['Key'])
            s3_client.delete_object(Bucket=BUCKET, Key=objectn['Key'])

    for file in files:
        with f as open(file,'r'):
            bar = ProgressBar(
            max_value=size,
            widgets=[FileTransferSpeed(), Bar(), Percentage(), Timer(), ETA()],
            )
            config = boto3.s3.transfer.TransferConfig(
            multipart_chunksize=80 * MB
            )
            s3.upload_fileobj(f, bucket, Prefix=filder, f"{file}", Callback=Progress(bar), Config=config)

            link = f'{endpoint}/{bucket}/{folder}/{file}'
            file_links.append(link)

    return file_links
