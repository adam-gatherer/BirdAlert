import json
import os
import time
import uuid
from datetime import UTC, datetime

import boto3
import requests

ssm = boto3.client("ssm")
s3 = boto3.client("s3")

MAX_EBIRD_RETRIES = 3
MAX_EBIRD_ATTEMPTS = 1 + MAX_EBIRD_RETRIES
RETRY_DELAYS_SECONDS = (1, 2, 4)


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


def is_transient_ebird_error(error):
    response = getattr(error, "response", None)
    status_code = getattr(response, "status_code", None)
    if isinstance(status_code, int):
        return status_code == 429 or 500 <= status_code < 600

    return error.__class__.__module__.startswith("requests")


def eBird_response(region, api_key):
    url = f"https://api.ebird.org/v2/data/obs/{region}/recent/notable"
    for attempt in range(1, MAX_EBIRD_ATTEMPTS + 1):
        try:
            response = requests.get(
                url,
                headers={"X-eBirdApiToken": api_key},
                params={"back": 1},
                timeout=30,
            )
            response.raise_for_status()
            return response
        except Exception as error:
            if not is_transient_ebird_error(error) or attempt == MAX_EBIRD_ATTEMPTS:
                raise

            retry_delay = RETRY_DELAYS_SECONDS[attempt - 1]
            print(
                json.dumps(
                    {
                        "event": "poll_retry",
                        "region": region,
                        "attempt": attempt,
                        "retry_delay_seconds": retry_delay,
                        "error_type": type(error).__name__,
                    }
                )
            )
            time.sleep(retry_delay)


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
            response = eBird_response(region, api_key)
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
