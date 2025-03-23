# -*- coding: utf-8 -*-
"""
Ingests location data to GCS bucket
"""
import argparse
import io
import logging
import zipfile

import pyarrow.csv
import pyarrow.parquet
import requests

from google.cloud import storage

LOCATION_DATA_URL = "https://download.geonames.org/export/zip/US.zip"
LOCATION_DATA_FILENAME = "US.txt"
COLUMN_NAMES = ['Country Code', 'Postal Code', 'City', 'State', 'State Code',
                'Borough/County', 'Borough/County Code','NA','NA','lat','long','acc']

def main(args):
    logger = logging.getLogger(__name__)
    logger.info("Arguments received: " + args.__repr__())

    # download zip file
    r = requests.get(LOCATION_DATA_URL)
    r.raise_for_status()
    logger.info("File downloaded from " + LOCATION_DATA_URL)
    
    # extract and convert file to parquet, then upload
    z = zipfile.ZipFile(io.BytesIO(r.content))
    with z.open(LOCATION_DATA_FILENAME) as f:
        f = convert_to_parquet(f, b"\t", COLUMN_NAMES, COLUMN_NAMES[:7])
        upload_to_gcs(args.bucket_name, f, args.outfile_name)
    logger.info(f"Saved location_file to gs://{args.bucket_name}/{args.outfile_name}")

def upload_to_gcs(bucket_name, source_file, destination_blob_name):
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(destination_blob_name)
    blob.upload_from_file(source_file)

def convert_to_parquet(f, delimiter, column_names, include_columns):
    parse_options = pyarrow.csv.ParseOptions(delimiter=delimiter)
    read_options = pyarrow.csv.ReadOptions(column_names=column_names)
    convert_options = pyarrow.csv.ConvertOptions(include_columns=include_columns)
    tbl = pyarrow.csv.read_csv(f, parse_options=parse_options, read_options=read_options,
                                convert_options=convert_options)
    result = io.BytesIO()
    pyarrow.parquet.write_table(tbl, result)
    result.seek(0)
    return result

if __name__ == '__main__':
    
    parser = argparse.ArgumentParser(description='Ingest location data into GCS bucket')

    parser.add_argument('bucket-name', required=True, help='name of gcs bucket to save to')
    parser.add_argument('destination-file-name', required=True,
                        help='name of file to be saved on gcs; note this can include folders and should include extension e.g. myfolder/xyz.csv')

    main(parser.parse_args())