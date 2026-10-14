import base64
import importlib.util
import json
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import Mock, patch


READ_PATH = Path(__file__).resolve().parents[1] / "src" / "read"


def event(path, parameters=None, method="GET"):
    return {
        "rawPath": path,
        "queryStringParameters": parameters,
        "requestContext": {"http": {"method": method}},
    }


def query_item():
    return {
        "canonical_sighting_id": {"S": "sighting-123"},
        "species_code": {"S": "eurrob"},
        "common_name": {"S": "European Robin"},
        "scientific_name": {"S": "Erithacus rubecula"},
        "observed_at": {"S": "2026-10-14T10:30:00Z"},
        "location_id": {"S": "L123"},
        "location_name": {"S": "Example reserve"},
        "latitude": {"N": "51.5"},
        "longitude": {"N": "-0.1"},
        "count": {"N": "2"},
    }


class ReadTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        boto3_stub = types.ModuleType("boto3")
        boto3_stub.client = Mock()
        with patch.dict(sys.modules, {"boto3": boto3_stub}):
            spec = importlib.util.spec_from_file_location("read_app", READ_PATH / "app.py")
            cls.app = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(cls.app)

    def setUp(self):
        self.app.dynamodb = Mock()

    def call(self, request):
        with patch.dict(sys.modules, {}, clear=False):
            with patch.dict("os.environ", {"SIGHTINGS_TABLE": "birdalert-sightings"}, clear=True):
                result = self.app.lambda_handler(request, None)
        return result["statusCode"], json.loads(result["body"])

    def test_latest_sightings_use_bounded_descending_query(self):
        self.app.dynamodb.query.return_value = {"Items": [query_item()]}

        status, body = self.call(event("/sightings"))

        self.assertEqual(status, 200)
        self.assertEqual(body["next_cursor"], None)
        self.assertEqual(body["sightings"][0]["species"]["code"], "eurrob")
        self.assertEqual(body["sightings"][0]["location"]["latitude"], 51.5)
        request = self.app.dynamodb.query.call_args.kwargs
        self.assertEqual(request["IndexName"], "query-by-key")
        self.assertEqual(request["ExpressionAttributeValues"][":query_key"], {"S": "LATEST"})
        self.assertEqual(request["Limit"], 10)
        self.assertFalse(request["ScanIndexForward"])

    def test_combined_filter_uses_uk_date_boundaries_and_cursor(self):
        cursor_key = {
            "sighting_id": {"S": "QUERY#REGION#GB-ENG#SPECIES#eurrob#sighting-123"},
            "query_key": {"S": "REGION#GB-ENG#SPECIES#eurrob"},
            "query_sort": {"S": "2026-10-14T10:30:00Z#sighting-123"},
        }
        cursor = base64.urlsafe_b64encode(json.dumps(cursor_key).encode()).decode().rstrip("=")
        self.app.dynamodb.query.return_value = {"Items": []}

        status, body = self.call(
            event(
                "/sightings",
                {"region": "GB-ENG", "species": "eurrob", "date": "2026-10-14", "limit": "50", "cursor": cursor},
            )
        )

        self.assertEqual(status, 200)
        self.assertEqual(body["sightings"], [])
        request = self.app.dynamodb.query.call_args.kwargs
        self.assertEqual(request["Limit"], 50)
        self.assertEqual(request["ExclusiveStartKey"], cursor_key)
        self.assertEqual(
            request["ExpressionAttributeValues"][":query_key"],
            {"S": "REGION#GB-ENG#SPECIES#eurrob"},
        )
        self.assertEqual(request["ExpressionAttributeValues"][":start"], {"S": "2026-10-13T23:00:00Z#"})
        self.assertEqual(request["ExpressionAttributeValues"][":end"], {"S": "2026-10-14T23:00:00Z#"})

    def test_invalid_query_parameters_are_rejected(self):
        for parameters in (
            {"limit": "51"},
            {"limit": "0"},
            {"date": "14/10/2026"},
            {"region": "gb-eng"},
            {"species": "European Robin"},
            {"cursor": "not-a-cursor"},
            {"unexpected": "value"},
        ):
            with self.subTest(parameters=parameters):
                status, _ = self.call(event("/sightings", parameters))
                self.assertEqual(status, 400)
        self.app.dynamodb.query.assert_not_called()

    def test_cursor_is_returned_when_dynamodb_has_more_results(self):
        key = {
            "sighting_id": {"S": "QUERY#LATEST#sighting-123"},
            "query_key": {"S": "LATEST"},
            "query_sort": {"S": "2026-10-14T10:30:00Z#sighting-123"},
        }
        self.app.dynamodb.query.return_value = {"Items": [], "LastEvaluatedKey": key}

        status, body = self.call(event("/sightings"))

        self.assertEqual(status, 200)
        self.assertEqual(
            json.loads(base64.urlsafe_b64decode(body["next_cursor"] + "==")), key
        )

    def test_health_checks_database_connectivity(self):
        status, body = self.call(event("/health"))

        self.assertEqual(status, 200)
        self.assertEqual(body, {"status": "ok", "database": "reachable"})
        self.app.dynamodb.get_item.assert_called_once()

        self.app.dynamodb.reset_mock()
        self.app.dynamodb.get_item.side_effect = RuntimeError("unavailable")
        status, body = self.call(event("/health"))
        self.assertEqual(status, 503)
        self.assertEqual(body, {"status": "unavailable", "database": "unreachable"})

    def test_unknown_route_and_method_return_not_found(self):
        self.assertEqual(self.call(event("/missing"))[0], 404)
        self.assertEqual(self.call(event("/sightings", method="POST"))[0], 404)


if __name__ == "__main__":
    unittest.main()
