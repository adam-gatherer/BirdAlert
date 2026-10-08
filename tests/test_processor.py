import importlib.util
import io
import json
import sys
import types
import unittest
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import Mock, patch


PROCESSOR_PATH = Path(__file__).resolve().parents[1] / "src" / "processor"


def valid_record(**overrides):
    record = {
        "speciesCode": "rebwoo",
        "comName": "Red-bellied Woodpecker",
        "sciName": "Melanerpes carolinus",
        "locId": "L27886431",
        "locName": "Little Meadows SW",
        "obsDt": "2026-09-30 11:05",
        "howMany": 1,
        "lat": 41.8958333,
        "lng": -76.21875,
        "obsValid": True,
        "obsReviewed": False,
        "locationPrivate": True,
        "subId": "S397765667",
    }
    record.update(overrides)
    return record


class ProcessorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        boto3_stub = types.ModuleType("boto3")
        boto3_stub.client = Mock()
        with patch.dict(sys.modules, {"boto3": boto3_stub}):
            spec = importlib.util.spec_from_file_location(
                "processor_app", PROCESSOR_PATH / "app.py"
            )
            cls.app = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(cls.app)

    def setUp(self):
        self.app.s3 = Mock()

    def test_processing_window_uses_previous_utc_quarter_hour(self):
        start, end = self.app.processing_window(
            datetime(2026, 9, 30, 10, 17, 42, tzinfo=UTC)
        )

        self.assertEqual(start, datetime(2026, 9, 30, 10, 0, tzinfo=UTC))
        self.assertEqual(end, datetime(2026, 9, 30, 10, 15, tzinfo=UTC))

    def test_window_is_start_inclusive_and_end_exclusive(self):
        payload = [
            valid_record(obsDt="2026-09-30 11:00", speciesCode="start"),
            valid_record(obsDt="2026-09-30 11:14", speciesCode="inside"),
            valid_record(obsDt="2026-09-30 11:15", speciesCode="end"),
            valid_record(obsDt="2026-09-30 10:59", speciesCode="before"),
        ]

        result = self.app.process_payload(
            payload,
            "GB-ENG",
            datetime(2026, 9, 30, 10, 17, tzinfo=UTC),
        )

        self.assertEqual(
            [record["species_code"] for record in result["accepted"]],
            ["start", "inside"],
        )
        self.assertEqual(result["accepted"][0]["observed_at"], "2026-09-30T10:00:00Z")
        self.assertEqual(result["rejected"], [])

    def test_transformation_keeps_only_internal_fields(self):
        result = self.app.process_payload(
            [valid_record(unneeded="raw value")],
            "GB-ENG",
            datetime(2026, 9, 30, 10, 17, tzinfo=UTC),
        )

        transformed = result["accepted"][0]
        self.assertEqual(transformed["source_region"], "GB-ENG")
        self.assertEqual(transformed["count"], 1)
        self.assertTrue(transformed["location_private"])
        self.assertNotIn("unneeded", transformed)
        self.assertNotIn("obsReviewed", transformed)

    def test_incomplete_and_invalid_records_are_rejected(self):
        invalid_records = [
            valid_record(comName=""),
            valid_record(obsDt="not-a-time"),
            valid_record(lat=91),
            valid_record(lng=-181),
            valid_record(obsValid=False),
            valid_record(locationPrivate="yes"),
            valid_record(howMany=0),
            ["not", "an", "object"],
        ]

        result = self.app.process_payload(
            invalid_records,
            "GB-ENG",
            datetime(2026, 9, 30, 10, 17, tzinfo=UTC),
        )

        self.assertEqual(result["accepted"], [])
        self.assertEqual(len(result["rejected"]), len(invalid_records))
        self.assertEqual(
            [rejection["index"] for rejection in result["rejected"]],
            list(range(len(invalid_records))),
        )

    def test_dst_ambiguous_and_nonexistent_times_are_rejected(self):
        payload = [
            valid_record(obsDt="2026-10-25 01:30"),
            valid_record(obsDt="2026-03-29 01:30"),
        ]

        result = self.app.process_payload(
            payload,
            "GB-ENG",
            datetime(2026, 10, 25, 2, 17, tzinfo=UTC),
        )

        self.assertEqual(result["accepted"], [])
        self.assertEqual(len(result["rejected"]), 2)

    def test_non_array_payload_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "JSON array"):
            self.app.process_payload(
                {"unexpected": "shape"},
                "GB-ENG",
                datetime(2026, 9, 30, 10, 17, tzinfo=UTC),
            )

    def test_handler_reads_url_encoded_s3_object_and_reports_counts(self):
        object_key = "GB-ENG/20260930T101700.000000Z-test id.json"
        self.app.s3.get_object.return_value = {
            "Body": io.BytesIO(json.dumps([valid_record()]).encode("utf-8"))
        }
        event = {
            "Records": [
                {
                    "s3": {
                        "bucket": {"name": "birdalert-raw"},
                        "object": {
                            "key": "GB-ENG%2F20260930T101700.000000Z-test+id.json"
                        },
                    }
                }
            ]
        }

        result = self.app.lambda_handler(event, None)

        self.app.s3.get_object.assert_called_once_with(
            Bucket="birdalert-raw", Key=object_key
        )
        self.assertEqual(
            result,
            {"processed_objects": 1, "accepted_records": 1, "rejected_records": 0},
        )

    def test_malformed_key_json_and_event_fail_visibly(self):
        with self.assertRaisesRegex(ValueError, "unexpected format"):
            self.app.raw_object_context("wrong-key.json")

        self.app.s3.get_object.return_value = {"Body": io.BytesIO(b"not json")}
        with self.assertRaisesRegex(ValueError, "not valid UTF-8 JSON"):
            self.app.process_s3_record(
                {
                    "s3": {
                        "bucket": {"name": "birdalert-raw"},
                        "object": {
                            "key": "GB-ENG/20260930T101700.000000Z-test.json"
                        },
                    }
                }
            )

        with self.assertRaisesRegex(ValueError, "at least one record"):
            self.app.lambda_handler({}, None)


if __name__ == "__main__":
    unittest.main()
