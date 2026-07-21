import json
import os

import boto3
import requests

ssm = boto3.client("ssm")

PARAMETER_NAME = "/birdalert/dev/ebird/api-key"


def lambda_handler(event, context):

    api_key = ssm.get_parameter(
        Name=PARAMETER_NAME,
        WithDecryption=True,
    )["Parameter"]["Value"]

    headers = {
        "X-eBirdApiToken": api_key,
    }

    response = requests.get(
        "https://api.ebird.org/v2/data/obs/GB-ENG/recent/notable",
        headers=headers,
        timeout=30,
    )

    print(json.dumps(response.json(), indent=2))

    return {
        "statusCode": response.status_code,
        "body": json.dumps(
            {
                "records": len(response.json())
            }
        ),
    }