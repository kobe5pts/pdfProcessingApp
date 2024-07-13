
import boto3
import io

s3_client = boto3.client('s3')

def get_file_from_s3(bucket_name, object_name, as_text=False):
    try:
        print(f'Getting {object_name} from bucket {bucket_name}')  # Debug statement
        response = s3_client.get_object(Bucket=bucket_name, Key=object_name)
        file_content = response['Body'].read()
        print(f'Retrieved {object_name} from S3')  # Debug statement
        if as_text:
            return file_content.decode('utf-8')  # Decode to string if as_text is True
        return (file_content)
    except Exception as e:
        print(f"Error getting {object_name} from S3: {e}")
        return None

def save_file_to_s3(bucket_name, object_name, file_content):
    try:
        print(f'Saving {object_name} to bucket {bucket_name}')  # Debug statement
        if isinstance(file_content, str):
            file_content = file_content.encode('utf-8')
        s3_client.put_object(Bucket=bucket_name, Key=object_name, Body=file_content)
        print(f'Saved {object_name} to S3')  # Debug statement
        return True
    except Exception as e:
        print(f"Error saving {object_name} to S3: {e}")
        return False

def check_file_exists_in_s3(bucket_name, object_name):
    try:
        s3_client.head_object(Bucket=bucket_name, Key=object_name)
        return True
    except Exception as e:
        return False
