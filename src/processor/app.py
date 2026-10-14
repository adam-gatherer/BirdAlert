import hashlib
import json
import os
import re
from datetime import UTC, datetime
from urllib.parse import unquote_plus
from zoneinfo import ZoneInfo

import boto3


s3 = boto3.client("s3")
dynamodb = boto3.client("dynamodb")

UK_TIMEZONE = ZoneInfo("Europe/London")
RAW_KEY_PATTERN = re.compile(
    r"^(?P<region>[^/]+)/(?P<timestamp>\d{8}T\d{6}\.\d{6}Z)-[^/]+\.json$"
)
OBSERVATION_TIME_FORMATS = ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M")
MAX_BATCH_GET_ATTEMPTS = 3
PROCESSING_STATUS_ID = "__processing_status__"


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


def first_seen_at(ingested_at):
    if ingested_at.tzinfo is None:
        raise ValueError("Ingestion timestamp must be timezone-aware")

    return ingested_at.astimezone(UTC).isoformat().replace("+00:00", "Z")


def observation_time_utc(value):
    if not isinstance(value, str) or not value.strip():
        raise InvalidRecord("obsDt must be a non-empty timestamp")

    for time_format in OBSERVATION_TIME_FORMATS:
        try:
            local_time = datetime.strptime(value, time_format)
            break
        except ValueError:
            continue
    else:
        raise InvalidRecord("obsDt must use YYYY-MM-DD HH:MM or YYYY-MM-DD HH:MM:SS")

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

    if not isinstance(record.get("obsValid"), bool):
        raise InvalidRecord("obsValid must be a boolean")
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
        "validation_status": "validated" if record["obsValid"] else "provisional",
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
        "validation_status": {"S": record["validation_status"]},
        "first_seen_at": {"S": record["first_seen_at"]},
        "source_regions": {"SS": [record["source_region"]]},
        "location_id": {"S": record["location_id"]},
        "location_name": {"S": record["location_name"]},
        "latitude": {"N": str(record["latitude"])},
        "longitude": {"N": str(record["longitude"])},
    }

    if "count" in record:
        item["count"] = {"N": str(record["count"])}

    return item


def query_keys(record):
    region = record["source_region"]
    species = record["species_code"]
    return [
        "LATEST",
        f"REGION#{region}",
        f"SPECIES#{species}",
        f"REGION#{region}#SPECIES#{species}",
    ]


def query_item(record, query_key):
    canonical_id = sighting_id(record)
    canonical = dynamodb_item(record)
    item = {
        "sighting_id": {"S": f"QUERY#{query_key}#{canonical_id}"},
        "query_key": {"S": query_key},
        "query_sort": {"S": f"{record['observed_at']}#{canonical_id}"},
        "canonical_sighting_id": {"S": canonical_id},
    }
    for field in (
        "species_code",
        "common_name",
        "scientific_name",
        "observed_at",
        "validation_status",
        "location_id",
        "location_name",
        "latitude",
        "longitude",
        "count",
    ):
        if field in canonical:
            item[field] = canonical[field]
    return item


def is_duplicate_error(error):
    response = getattr(error, "response", {})
    error_code = response.get("Error", {}).get("Code")
    if error_code == "ConditionalCheckFailedException":
        return True
    if error_code != "TransactionCanceledException":
        return False
    return any(
        reason.get("Code") == "ConditionalCheckFailed"
        for reason in response.get("CancellationReasons", [])
    )


def persist_sighting(record, table_name):
    canonical_item = dynamodb_item(record)
    query_items = [query_item(record, key) for key in query_keys(record)]
    try:
        dynamodb.transact_write_items(
            TransactItems=[
                {
                    "Put": {
                        "TableName": table_name,
                        "Item": canonical_item,
                        "ConditionExpression": "attribute_not_exists(sighting_id)",
                    }
                },
                *[
                    {"Put": {"TableName": table_name, "Item": item}}
                    for item in query_items
                ],
            ]
        )
    except Exception as error:
        if is_duplicate_error(error):
            return False
        raise
    return True


def persist_source_region(record, table_name):
    region_query_items = [
        query_item(record, query_key)
        for query_key in query_keys(record)
        if query_key.startswith("REGION#")
    ]
    dynamodb.transact_write_items(
        TransactItems=[
            {
                "Update": {
                    "TableName": table_name,
                    "Key": {"sighting_id": {"S": sighting_id(record)}},
                    "ConditionExpression": "attribute_exists(sighting_id)",
                    "UpdateExpression": "ADD source_regions :source_region",
                    "ExpressionAttributeValues": {
                        ":source_region": {"SS": [record["source_region"]]}
                    },
                }
            },
            *[
                {"Put": {"TableName": table_name, "Item": item}}
                for item in region_query_items
            ],
        ]
    )


def existing_source_regions(records, table_name):
    record_ids = list(dict.fromkeys(sighting_id(record) for record in records))
    existing = {}

    for start in range(0, len(record_ids), 100):
        request_items = {
            table_name: {
                "Keys": [
                    {"sighting_id": {"S": record_id}}
                    for record_id in record_ids[start : start + 100]
                ],
                "ProjectionExpression": "sighting_id, source_regions",
            }
        }
        for _ in range(MAX_BATCH_GET_ATTEMPTS):
            response = dynamodb.batch_get_item(RequestItems=request_items)
            for item in response.get("Responses", {}).get(table_name, []):
                record_id = item.get("sighting_id", {}).get("S")
                if record_id:
                    existing[record_id] = set(
                        item.get("source_regions", {}).get("SS", [])
                    )

            request_items = response.get("UnprocessedKeys", {})
            if not request_items:
                break
        else:
            raise RuntimeError("DynamoDB did not process all requested sighting keys")

    return existing


def sightings_table_name():
    table_name = os.environ.get("SIGHTINGS_TABLE", "").strip()
    if not table_name:
        raise ValueError("SIGHTINGS_TABLE must be configured")
    return table_name


def persist_processing_status(table_name, processed_at):
    if processed_at.tzinfo is None:
        raise ValueError("Processing timestamp must be timezone-aware")

    dynamodb.put_item(
        TableName=table_name,
        Item={
            "sighting_id": {"S": PROCESSING_STATUS_ID},
            "last_successful_processing_at": {
                "S": processed_at.astimezone(UTC).isoformat().replace("+00:00", "Z")
            },
        },
    )


def process_payload(payload, source_region, ingested_at):
    if not isinstance(payload, list):
        raise ValueError("Raw eBird response must be a JSON array")
    if not isinstance(source_region, str) or not source_region:
        raise ValueError("Source region must be a non-empty string")

    first_seen = first_seen_at(ingested_at)
    accepted = []
    rejected = []

    for index, record in enumerate(payload):
        try:
            transformed, _ = transform_record(record, source_region)
            transformed["first_seen_at"] = first_seen
            accepted.append(transformed)
        except InvalidRecord as error:
            rejected.append({"index": index, "reason": str(error)})

    return {
        "first_seen_at": first_seen,
        "accepted": accepted,
        "rejected": rejected,
    }


def rejection_reason_counts(rejected):
    counts = {}
    for rejection in rejected:
        reason = rejection["reason"]
        counts[reason] = counts.get(reason, 0) + 1
    return dict(sorted(counts.items()))


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
    existing_records = 0
    provenance_updated_records = 0
    existing_regions_by_id = existing_source_regions(result["accepted"], table_name)
    for record in result["accepted"]:
        record_id = sighting_id(record)
        source_regions = existing_regions_by_id.get(record_id)
        if source_regions is None and persist_sighting(record, table_name):
            persisted_records += 1
        elif source_regions is None:
            persist_source_region(record, table_name)
            provenance_updated_records += 1
        elif record["source_region"] in source_regions:
            existing_records += 1
        else:
            persist_source_region(record, table_name)
            provenance_updated_records += 1

    result["persisted_records"] = persisted_records
    result["existing_records"] = existing_records
    result["provenance_updated_records"] = provenance_updated_records
    processed_at = datetime.now(UTC)
    persist_processing_status(table_name, processed_at)
    result["last_successful_processing_at"] = processed_at.isoformat().replace(
        "+00:00", "Z"
    )
    print(
        json.dumps(
            {
                "event": "processing_completed",
                "bucket": bucket_name,
                "object": object_key,
                "first_seen_at": result["first_seen_at"],
                "last_successful_processing_at": result["last_successful_processing_at"],
                "accepted_records": len(result["accepted"]),
                "rejected_records": len(result["rejected"]),
                "rejection_reason_counts": rejection_reason_counts(result["rejected"]),
                "persisted_records": persisted_records,
                "existing_records": existing_records,
                "provenance_updated_records": provenance_updated_records,
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
        "existing_records": sum(result["existing_records"] for result in results),
        "provenance_updated_records": sum(
            result["provenance_updated_records"] for result in results
        ),
    }
