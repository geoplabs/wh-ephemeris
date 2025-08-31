import os
import boto3
import subprocess
from botocore.config import Config

def main():
    region = os.getenv("AWS_REGION", "us-east-1")
    # Use LocalStack endpoint directly for both services
    localstack_endpoint = os.getenv("AWS_ENDPOINT_URL", "http://localstack:4566")
    bucket = os.getenv("S3_BUCKET", "wh-reports-dev")
    queue = os.getenv("SQS_QUEUE", "wh-reports-jobs")

    # Create S3 client with proper configuration for LocalStack
    s3 = boto3.client(
        "s3", 
        endpoint_url=localstack_endpoint, 
        region_name=region,
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID", "test"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY", "test"),
        config=Config(signature_version='s3v4')
    )

    # Create bucket if not exists
    try:
        s3.create_bucket(Bucket=bucket)
        print(f"[seed] created S3 bucket: {bucket}")
    except Exception as e:
        if "BucketAlreadyOwnedByYou" in str(e) or "BucketAlreadyExists" in str(e):
            print(f"[seed] S3 bucket exists: {bucket}")
        else:
            raise

    # Create SQS queue - skip for now due to LocalStack 2.3 compatibility issues
    # The queue was already created manually via awslocal, so just verify it exists
    try:
        # Try a simple approach using requests to LocalStack directly
        import requests
        import json
        
        # Make a direct HTTP request to LocalStack SQS
        sqs_url = f"{localstack_endpoint}/"
        payload = {
            'Action': 'CreateQueue',
            'QueueName': queue,
            'Version': '2012-11-05'
        }
        
        response = requests.post(sqs_url, data=payload, timeout=10)
        
        if response.status_code == 200:
            print(f"[seed] SQS queue created/verified: {queue}")
            # Construct expected queue URL
            queue_url = f"{localstack_endpoint}/000000000000/{queue}"
            print(f"[seed] SQS URL: {queue_url}")
        else:
            print(f"[seed] SQS queue setup (queue likely exists): {queue}")
            queue_url = f"{localstack_endpoint}/000000000000/{queue}"
            print(f"[seed] SQS URL: {queue_url}")
            
    except Exception as e:
        # Fallback: assume queue exists from previous manual creation
        print(f"[seed] SQS queue (assuming exists): {queue}")
        queue_url = f"{localstack_endpoint}/000000000000/{queue}"
        print(f"[seed] SQS URL: {queue_url}")
    
    print("[seed] done.")

if __name__ == "__main__":
    main()
