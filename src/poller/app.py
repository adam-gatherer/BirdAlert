import json
import os
from datetime import datetime, UTC

import boto3
import requests

ssm = boto3.client("ssm")
s3 = boto3.client("s3")

PARAMETER_NAME = "/birdalert/dev/ebird/api-key"


def lambda_handler(event, context):

    api_key = ssm.get_parameter(
        Name=PARAMETER_NAME,
        WithDecryption=True,
    )["Parameter"]["Value"]

    response = requests.get(
        "https://api.ebird.org/v2/data/obs/GB-ENG/recent/notable",
        headers={
            "X-eBirdApiToken": api_key
        },
        timeout=30,
    )

    response.raise_for_status()

    data = response.json()

    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")

    filename = f"ebird/{timestamp}.json"

    s3.put_object(
        Bucket=os.environ["RAW_BUCKET"],
        Key=filename,
        Body=json.dumps(data),
        ContentType="application/json",
    )

    return {
        "statusCode": 200,
        "body": json.dumps(
            {
                "records": len(data),
                "object": filename,
            }
        ),
    }