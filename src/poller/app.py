import json
import os
import uuid
from datetime import UTC, datetime

import boto3
import requests

ssm = boto3.client("ssm")
s3 = boto3.client("s3")


def configured_regions(value):
    if not value or not value.strip():
        raise ValueError("EBIRD_REGIONS must contain at least one region code")

    regions = [region.strip() for region in value.split(",")]
    if any(not region for region in regions):
        raise ValueError("EBIRD_REGIONS must not contain empty region codes")
    if len(set(regions)) != len(regions):
        raise ValueError("EBIRD_REGIONS must not contain duplicate region codes")

    return regions


def raw_object_key(region, timestamp=None, unique_id=None):
    timestamp = timestamp or datetime.now(UTC).strftime("%Y%m%dT%H%M%S.%fZ")
    unique_id = unique_id or uuid.uuid4().hex
    return f"{region}/{timestamp}-{unique_id}.json"


def lambda_handler(event, context):
    regions = configured_regions(os.environ["EBIRD_REGIONS"])
    parameter_name = os.environ["PARAMETER_NAME"]
    bucket_name = os.environ["RAW_BUCKET"]

    api_key = ssm.get_parameter(
        Name=parameter_name,
        WithDecryption=True,
    )["Parameter"]["Value"]

    succeeded = []
    failed_regions = []

    for region in regions:
        try:
            response = requests.get(
                f"https://api.ebird.org/v2/data/obs/{region}/recent/notable",
                headers={"X-eBirdApiToken": api_key},
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()

            object_key = raw_object_key(region)
            s3.put_object(
                Bucket=bucket_name,
                Key=object_key,
                Body=response.content,
                ContentType="application/json",
            )

            if not isinstance(data, list):
                raise ValueError("eBird response must be a JSON array")

            result = {
                "region": region,
                "records": len(data),
                "object": object_key,
            }
            succeeded.append(result)
            print(json.dumps({"event": "poll_succeeded", **result}))
        except Exception as error:
            failed_regions.append(region)
            print(
                json.dumps(
                    {
                        "event": "poll_failed",
                        "region": region,
                        "error_type": type(error).__name__,
                    }
                )
            )

    if failed_regions:
        raise RuntimeError(
            "Polling failed for region(s): " + ", ".join(failed_regions)
        )

    return {
        "statusCode": 200,
        "body": json.dumps(
            {
                "records": sum(result["records"] for result in succeeded),
                "regions": succeeded,
            }
        ),
    }
