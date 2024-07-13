# custom_storages.py

from storages.backends.s3boto3 import S3Boto3Storage

class UploadsStorage(S3Boto3Storage):
    location = 'uploads'
    file_overwrite = False

class JSONStorage(S3Boto3Storage):
    location = 'json'
    file_overwrite = False

class OutputsStorage(S3Boto3Storage):
    location = 'outputs'
    file_overwrite = False
