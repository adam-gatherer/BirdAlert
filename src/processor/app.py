import hashlib
import json
import os
import re
from datetime import UTC, datetime, timedelta
from urllib.parse import unquote_plus
from zoneinfo import ZoneInfo

import boto3


s3 = boto3.client("s3")
dynamodb = boto3.client("dynamodb")

UK_TIMEZONE = ZoneInfo("Europe/London")
RAW_KEY_PATTERN = re.compile(
    r"^(?P<region>[^/]+)/(?P<timestamp>\d{8}T\d{6}\.\d{6}Z)-[^/]+\.json$"
)
OBSERVATION_TIME_FORMAT = "%Y-%m-%d %H:%M"


class InvalidRecord(ValueError):
    """Raised when an eBird record cannot enter the internal model."""


def raw_object_context(object_key):
    match = RAW_KEY_PATTERN.fullmatch(object_key)
    if not match:
        raise ValueError(f"Raw object key has an unexpected format: {object_key}")

    ingested_at = datetime.strptime(
        match.group("timestamp"), "%Y%m%dT%H%M%S.%fZ"
    ).replace(tzinfo=UTC)
    return match.group("region"), ingested_at


def processing_window(ingested_at):
    if ingested_at.tzinfo is None:
        raise ValueError("Ingestion timestamp must be timezone-aware")

    ingested_at = ingested_at.astimezone(UTC)
    boundary = ingested_at.replace(
        minute=(ingested_at.minute // 15) * 15,
        second=0,
        microsecond=0,
    )
    return boundary - timedelta(minutes=15), boundary


def observation_time_utc(value):
    if not isinstance(value, str) or not value.strip():
        raise InvalidRecord("obsDt must be a non-empty timestamp")

    try:
        local_time = datetime.strptime(value, OBSERVATION_TIME_FORMAT)
    except ValueError as error:
        raise InvalidRecord("obsDt must use YYYY-MM-DD HH:MM") from error

    candidates = set()
    for fold in (0, 1):
        aware_time = local_time.replace(tzinfo=UK_TIMEZONE, fold=fold)
        utc_time = aware_time.astimezone(UTC)
        round_trip = utc_time.astimezone(UK_TIMEZONE).replace(tzinfo=None)
        if round_trip == local_time:
            candidates.add(utc_time)

    if len(candidates) != 1:
        raise InvalidRecord("obsDt is ambiguous or invalid in Europe/London")

    return candidates.pop()


def required_string(record, field):
    value = record.get(field)
    if not isinstance(value, str) or not value.strip():
        raise InvalidRecord(f"{field} must be a non-empty string")
    return value.strip()


def required_coordinate(record, field, minimum, maximum):
    value = record.get(field)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise InvalidRecord(f"{field} must be numeric")
    if not minimum <= value <= maximum:
        raise InvalidRecord(f"{field} must be between {minimum} and {maximum}")
    return value


def transform_record(record, source_region):
    if not isinstance(record, dict):
        raise InvalidRecord("record must be a JSON object")

    if not isinstance(record.get("obsValid"), bool) or not record["obsValid"]:
        raise InvalidRecord("obsValid must be true")
    if not isinstance(record.get("locationPrivate"), bool):
        raise InvalidRecord("locationPrivate must be a boolean")
    if record["locationPrivate"]:
        raise InvalidRecord("private-location sightings are excluded by policy")

    observed_at = observation_time_utc(record.get("obsDt"))
    transformed = {
        "species_code": required_string(record, "speciesCode"),
        "common_name": required_string(record, "comName"),
        "scientific_name": required_string(record, "sciName"),
        "observed_at": observed_at.isoformat().replace("+00:00", "Z"),
        "location_id": required_string(record, "locId"),
        "location_name": required_string(record, "locName"),
        "latitude": required_coordinate(record, "lat", -90, 90),
        "longitude": required_coordinate(record, "lng", -180, 180),
        "location_private": record["locationPrivate"],
        "submission_id": required_string(record, "subId"),
        "source_region": source_region,
    }

    if "howMany" in record:
        count = record["howMany"]
        if isinstance(count, bool) or not isinstance(count, int) or count < 1:
            raise InvalidRecord("howMany must be a positive integer when present")
        transformed["count"] = count

    return transformed, observed_at


def sighting_id(record):
    identity = f"{record['submission_id']}\x1f{record['species_code']}"
    return hashlib.sha256(identity.encode("utf-8")).hexdigest()


def dynamodb_item(record):
    if record["location_private"] is not False:
        raise InvalidRecord("private-location sightings cannot be persisted")

    item = {
        "sighting_id": {"S": sighting_id(record)},
        "species_code": {"S": record["species_code"]},
        "common_name": {"S": record["common_name"]},
        "scientific_name": {"S": record["scientific_name"]},
        "observed_at": {"S": record["observed_at"]},
        "submission_id": {"S": record["submission_id"]},
        "location_private": {"BOOL": record["location_private"]},
        "source_regions": {"SS": [record["source_region"]]},
        "location_id": {"S": record["location_id"]},
        "location_name": {"S": record["location_name"]},
        "latitude": {"N": str(record["latitude"])},
        "longitude": {"N": str(record["longitude"])},
    }

    if "count" in record:
        item["count"] = {"N": str(record["count"])}

    return item


def is_duplicate_error(error):
    return (
        getattr(error, "response", {})
        .get("Error", {})
        .get("Code")
        == "ConditionalCheckFailedException"
    )


def persist_sighting(record, table_name):
    try:
        dynamodb.put_item(
            TableName=table_name,
            Item=dynamodb_item(record),
            ConditionExpression="attribute_not_exists(sighting_id)",
        )
    except Exception as error:
        if is_duplicate_error(error):
            dynamodb.update_item(
                TableName=table_name,
                Key={"sighting_id": {"S": sighting_id(record)}},
                UpdateExpression="ADD source_regions :source_region",
                ExpressionAttributeValues={
                    ":source_region": {"SS": [record["source_region"]]}
                },
            )
            return False
        raise
    return True


def sightings_table_name():
    table_name = os.environ.get("SIGHTINGS_TABLE", "").strip()
    if not table_name:
        raise ValueError("SIGHTINGS_TABLE must be configured")
    return table_name


def process_payload(payload, source_region, ingested_at):
    if not isinstance(payload, list):
        raise ValueError("Raw eBird response must be a JSON array")
    if not isinstance(source_region, str) or not source_region:
        raise ValueError("Source region must be a non-empty string")

    window_start, window_end = processing_window(ingested_at)
    accepted = []
    rejected = []

    for index, record in enumerate(payload):
        try:
            transformed, observed_at = transform_record(record, source_region)
            if window_start <= observed_at < window_end:
                accepted.append(transformed)
        except InvalidRecord as error:
            rejected.append({"index": index, "reason": str(error)})

    return {
        "window_start": window_start.isoformat().replace("+00:00", "Z"),
        "window_end": window_end.isoformat().replace("+00:00", "Z"),
        "accepted": accepted,
        "rejected": rejected,
    }


def process_s3_record(event_record):
    bucket_name = event_record["s3"]["bucket"]["name"]
    object_key = unquote_plus(event_record["s3"]["object"]["key"])
    source_region, ingested_at = raw_object_context(object_key)

    response = s3.get_object(Bucket=bucket_name, Key=object_key)
    try:
        payload = json.loads(response["Body"].read().decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(f"Raw object is not valid UTF-8 JSON: {object_key}") from error

    result = process_payload(payload, source_region, ingested_at)
    table_name = sightings_table_name()
    persisted_records = 0
    duplicate_records = 0
    for record in result["accepted"]:
        if persist_sighting(record, table_name):
            persisted_records += 1
        else:
            duplicate_records += 1

    result["persisted_records"] = persisted_records
    result["duplicate_records"] = duplicate_records
    print(
        json.dumps(
            {
                "event": "processing_completed",
                "bucket": bucket_name,
                "object": object_key,
                "window_start": result["window_start"],
                "window_end": result["window_end"],
                "accepted_records": len(result["accepted"]),
                "rejected_records": len(result["rejected"]),
                "persisted_records": persisted_records,
                "duplicate_records": duplicate_records,
            }
        )
    )
    return result


def lambda_handler(event, context):
    event_records = event.get("Records") if isinstance(event, dict) else None
    if not isinstance(event_records, list) or not event_records:
        raise ValueError("S3 event must contain at least one record")

    results = [process_s3_record(record) for record in event_records]
    return {
        "processed_objects": len(results),
        "accepted_records": sum(len(result["accepted"]) for result in results),
        "rejected_records": sum(len(result["rejected"]) for result in results),
        "persisted_records": sum(result["persisted_records"] for result in results),
        "duplicate_records": sum(result["duplicate_records"] for result in results),
    }
