import base64
import json
import os
import re
from datetime import UTC, date, datetime, time
from zoneinfo import ZoneInfo

import boto3


dynamodb = boto3.client("dynamodb")

DEFAULT_LIMIT = 10
MAX_LIMIT = 50
QUERY_INDEX = "query-by-key"
UK_TIMEZONE = ZoneInfo("Europe/London")
REGION_PATTERN = re.compile(r"^[A-Z]{2,3}(?:-[A-Z0-9]+)*$")
SPECIES_PATTERN = re.compile(r"^[a-z0-9]{1,32}$")
DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")
ALLOWED_PARAMETERS = {"region", "species", "date", "limit", "cursor"}


class APIError(ValueError):
    def __init__(self, status_code, message):
        super().__init__(message)
        self.status_code = status_code
        self.message = message


def table_name():
    value = os.environ.get("SIGHTINGS_TABLE", "").strip()
    if not value:
        raise RuntimeError("SIGHTINGS_TABLE must be configured")
    return value


def response(status_code, payload):
    return {
        "statusCode": status_code,
        "headers": {"content-type": "application/json"},
        "body": json.dumps(payload, separators=(",", ":")),
    }


def query_parameters(event):
    parameters = event.get("queryStringParameters") or {}
    if not isinstance(parameters, dict):
        raise APIError(400, "query parameters must be valid")
    unknown = set(parameters) - ALLOWED_PARAMETERS
    if unknown:
        raise APIError(400, "unsupported query parameter")
    return parameters


def parse_limit(value):
    if value is None:
        return DEFAULT_LIMIT
    if not isinstance(value, str) or not value.isascii() or not value.isdecimal():
        raise APIError(400, "limit must be a whole number")
    limit = int(value)
    if not 1 <= limit <= MAX_LIMIT:
        raise APIError(400, "limit must be between 1 and 50")
    return limit


def parse_date_bounds(value):
    if value is None:
        return None
    if not isinstance(value, str) or not DATE_PATTERN.fullmatch(value):
        raise APIError(400, "date must use YYYY-MM-DD")
    try:
        requested_day = date.fromisoformat(value)
    except ValueError as error:
        raise APIError(400, "date must use YYYY-MM-DD") from error

    start = datetime.combine(requested_day, time.min, tzinfo=UK_TIMEZONE)
    end = datetime.combine(
        date.fromordinal(requested_day.toordinal() + 1), time.min, tzinfo=UK_TIMEZONE
    )
    return (
        start.astimezone(UTC).isoformat().replace("+00:00", "Z"),
        end.astimezone(UTC).isoformat().replace("+00:00", "Z"),
    )


def query_key(region, species):
    if region is not None and (
        not isinstance(region, str) or not REGION_PATTERN.fullmatch(region)
    ):
        raise APIError(400, "region must be an eBird region code")
    if species is not None and (
        not isinstance(species, str) or not SPECIES_PATTERN.fullmatch(species)
    ):
        raise APIError(400, "species must be an eBird species code")
    if region and species:
        return f"REGION#{region}#SPECIES#{species}"
    if region:
        return f"REGION#{region}"
    if species:
        return f"SPECIES#{species}"
    return "LATEST"


def encode_cursor(last_evaluated_key):
    if not last_evaluated_key:
        return None
    encoded = json.dumps(last_evaluated_key, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(encoded).decode("ascii").rstrip("=")


def decode_cursor(value, expected_query_key):
    if value is None:
        return None
    if not isinstance(value, str) or not value:
        raise APIError(400, "cursor is invalid")
    try:
        padding = "=" * (-len(value) % 4)
        key = json.loads(base64.urlsafe_b64decode(value + padding))
        if (
            not isinstance(key, dict)
            or key.get("query_key", {}).get("S") != expected_query_key
            or not isinstance(key.get("sighting_id", {}).get("S"), str)
            or not isinstance(key.get("query_sort", {}).get("S"), str)
        ):
            raise ValueError("invalid cursor key")
    except (ValueError, TypeError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise APIError(400, "cursor is invalid") from error
    return key


def attribute_text(item, name):
    return item[name]["S"]


def sighting_response(item):
    result = {
        "id": attribute_text(item, "canonical_sighting_id"),
        "species": {
            "code": attribute_text(item, "species_code"),
            "common_name": attribute_text(item, "common_name"),
            "scientific_name": attribute_text(item, "scientific_name"),
        },
        "observed_at": attribute_text(item, "observed_at"),
        "location": {
            "id": attribute_text(item, "location_id"),
            "name": attribute_text(item, "location_name"),
            "latitude": float(item["latitude"]["N"]),
            "longitude": float(item["longitude"]["N"]),
        },
    }
    if "count" in item:
        result["count"] = int(item["count"]["N"])
    return result


def get_sightings(parameters):
    region = parameters.get("region")
    species = parameters.get("species")
    key = query_key(region, species)
    bounds = parse_date_bounds(parameters.get("date"))
    values = {":query_key": {"S": key}}
    request = {
        "TableName": table_name(),
        "IndexName": QUERY_INDEX,
        "KeyConditionExpression": "#query_key = :query_key",
        "ExpressionAttributeNames": {"#query_key": "query_key"},
        "ExpressionAttributeValues": values,
        "ScanIndexForward": False,
        "Limit": parse_limit(parameters.get("limit")),
    }
    if bounds:
        request["KeyConditionExpression"] += " AND #query_sort >= :start AND #query_sort < :end"
        request["ExpressionAttributeNames"]["#query_sort"] = "query_sort"
        values[":start"] = {"S": f"{bounds[0]}#"}
        values[":end"] = {"S": f"{bounds[1]}#"}
    cursor = decode_cursor(parameters.get("cursor"), key)
    if cursor:
        request["ExclusiveStartKey"] = cursor

    result = dynamodb.query(**request)
    return {
        "sightings": [sighting_response(item) for item in result.get("Items", [])],
        "next_cursor": encode_cursor(result.get("LastEvaluatedKey")),
    }


def health():
    try:
        dynamodb.get_item(
            TableName=table_name(),
            Key={"sighting_id": {"S": "__health_check__"}},
            ProjectionExpression="sighting_id",
        )
    except Exception as error:
        print(json.dumps({"event": "health_database_unavailable", "error_type": type(error).__name__}))
        return response(503, {"status": "unavailable", "database": "unreachable"})
    return response(200, {"status": "ok", "database": "reachable"})


def lambda_handler(event, context):
    try:
        if not isinstance(event, dict) or event.get("requestContext", {}).get("http", {}).get("method") != "GET":
            return response(404, {"message": "not found"})
        path = event.get("rawPath") or event.get("requestContext", {}).get("http", {}).get("path")
        if path == "/health":
            return health()
        if path != "/sightings":
            return response(404, {"message": "not found"})
        return response(200, get_sightings(query_parameters(event)))
    except APIError as error:
        return response(error.status_code, {"message": error.message})
    except Exception as error:
        print(json.dumps({"event": "sightings_query_failed", "error_type": type(error).__name__}))
        return response(503, {"message": "service unavailable"})
