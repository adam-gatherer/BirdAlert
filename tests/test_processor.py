import importlib.util
import io
import json
import os
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
        "locationPrivate": False,
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
        self.app.dynamodb = Mock()
        self.app.dynamodb.batch_get_item.return_value = {
            "Responses": {},
            "UnprocessedKeys": {},
        }

    def test_first_seen_ingestion_accepts_well_formed_records_outside_heartbeat_interval(self):
        payload = [
            valid_record(obsDt="2026-09-30 08:00", speciesCode="earlier"),
            valid_record(obsDt="2026-09-30 11:14", speciesCode="recent"),
        ]

        result = self.app.process_payload(
            payload,
            "GB-ENG",
            datetime(2026, 9, 30, 10, 17, tzinfo=UTC),
        )

        self.assertEqual(
            [record["species_code"] for record in result["accepted"]],
            ["earlier", "recent"],
        )
        self.assertEqual(result["accepted"][0]["observed_at"], "2026-09-30T07:00:00Z")
        self.assertEqual(result["accepted"][0]["first_seen_at"], "2026-09-30T10:17:00Z")
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
        self.assertFalse(transformed["location_private"])
        self.assertEqual(transformed["validation_status"], "validated")
        self.assertNotIn("unneeded", transformed)
        self.assertNotIn("obsReviewed", transformed)

    def test_provisional_records_and_second_precision_are_accepted(self):
        record, observed_at = self.app.transform_record(
            valid_record(obsValid=False, obsDt="2026-09-30 11:05:42"), "GB-ENG"
        )

        self.assertEqual(record["validation_status"], "provisional")
        self.assertEqual(observed_at, datetime(2026, 9, 30, 10, 5, 42, tzinfo=UTC))

    def test_sighting_identity_is_independent_of_source_region(self):
        record, _ = self.app.transform_record(valid_record(), "GB-ENG")
        other_region_record, _ = self.app.transform_record(valid_record(), "GB-SCT")
        record["first_seen_at"] = "2026-09-30T10:17:00Z"
        other_region_record["first_seen_at"] = "2026-09-30T10:17:00Z"

        item = self.app.dynamodb_item(record)

        self.assertEqual(
            item["sighting_id"],
            self.app.dynamodb_item(other_region_record)["sighting_id"],
        )
        self.assertEqual(item["source_regions"], {"SS": ["GB-ENG"]})

    def test_query_records_cover_every_supported_lookup(self):
        record, _ = self.app.transform_record(valid_record(), "GB-ENG")
        record["first_seen_at"] = "2026-09-30T10:17:00Z"
        canonical_id = self.app.sighting_id(record)

        self.assertEqual(
            self.app.query_keys(record),
            [
                "LATEST",
                "REGION#GB-ENG",
                "SPECIES#rebwoo",
                "REGION#GB-ENG#SPECIES#rebwoo",
            ],
        )
        item = self.app.query_item(record, "REGION#GB-ENG#SPECIES#rebwoo")
        self.assertEqual(
            item["sighting_id"],
            {"S": f"QUERY#REGION#GB-ENG#SPECIES#rebwoo#{canonical_id}"},
        )
        self.assertEqual(
            item["query_sort"],
            {"S": f"2026-09-30T10:05:00Z#{canonical_id}"},
        )
        self.assertNotIn("submission_id", item)
        self.assertNotIn("source_regions", item)
        self.assertNotIn("first_seen_at", item)
        self.assertEqual(item["validation_status"], {"S": "validated"})

    @patch.dict(os.environ, {"SIGHTINGS_TABLE": "birdalert-sightings"}, clear=True)
    def test_handler_excludes_private_records_before_dynamodb_writes(self):
        payload = [valid_record(locationPrivate=True), valid_record()]
        raw_body = json.dumps(payload).encode("utf-8")
        self.app.s3.get_object.return_value = {"Body": io.BytesIO(raw_body)}
        event = {
            "Records": [
                {
                    "s3": {
                        "bucket": {"name": "birdalert-raw"},
                        "object": {
                            "key": "GB-ENG/20260930T101700.000000Z-test.json"
                        },
                    }
                }
            ]
        }

        result = self.app.lambda_handler(event, None)

        self.assertEqual(result["accepted_records"], 1)
        self.assertEqual(result["rejected_records"], 1)
        self.assertEqual(result["persisted_records"], 1)
        self.app.dynamodb.transact_write_items.assert_called_once()
        item = self.app.dynamodb.transact_write_items.call_args.kwargs["TransactItems"][0]["Put"]["Item"]
        self.assertEqual(item["location_private"], {"BOOL": False})
        self.app.s3.put_object.assert_not_called()

    @patch.dict(os.environ, {"SIGHTINGS_TABLE": "birdalert-sightings"}, clear=True)
    def test_completion_log_aggregates_rejection_reasons_without_records(self):
        payload = [
            valid_record(),
            valid_record(locationPrivate=True),
            valid_record(obsDt="not-a-time"),
        ]
        self.app.s3.get_object.return_value = {
            "Body": io.BytesIO(json.dumps(payload).encode("utf-8"))
        }
        event_record = {
            "s3": {
                "bucket": {"name": "birdalert-raw"},
                "object": {"key": "GB-ENG/20260930T101700.000000Z-test.json"},
            }
        }

        with patch("builtins.print") as output:
            self.app.process_s3_record(event_record)

        log_entry = json.loads(output.call_args.args[0])
        self.assertEqual(
            log_entry["rejection_reason_counts"],
            {
                "obsDt must use YYYY-MM-DD HH:MM or YYYY-MM-DD HH:MM:SS": 1,
                "private-location sightings are excluded by policy": 1,
            },
        )
        self.assertNotIn("accepted", log_entry)
        self.assertNotIn("rejected", log_entry)
        self.assertNotIn("S397765667", output.call_args.args[0])

    def test_persistence_guard_prevents_private_location_writes(self):
        record, _ = self.app.transform_record(valid_record(), "GB-ENG")

        for privacy_flag in (True, None, "false", 0):
            with self.subTest(privacy_flag=privacy_flag):
                record["location_private"] = privacy_flag
                with self.assertRaisesRegex(self.app.InvalidRecord, "cannot be persisted"):
                    self.app.persist_sighting(record, "birdalert-sightings")

        self.app.dynamodb.transact_write_items.assert_not_called()

    def test_dynamodb_item_keeps_non_private_location(self):
        record, _ = self.app.transform_record(
            valid_record(locationPrivate=False), "GB-ENG"
        )
        record["first_seen_at"] = "2026-09-30T10:17:00Z"

        item = self.app.dynamodb_item(record)

        self.assertEqual(item["location_id"], {"S": "L27886431"})
        self.assertEqual(item["latitude"], {"N": "41.8958333"})
        self.assertEqual(item["longitude"], {"N": "-76.21875"})
        self.assertEqual(item["first_seen_at"], {"S": "2026-09-30T10:17:00Z"})

    def test_duplicate_write_is_an_idempotent_success(self):
        class DuplicateError(Exception):
            response = {
                "Error": {"Code": "TransactionCanceledException"},
                "CancellationReasons": [{"Code": "ConditionalCheckFailed"}],
            }

        record, _ = self.app.transform_record(valid_record(), "GB-ENG")
        record["first_seen_at"] = "2026-09-30T10:17:00Z"
        self.app.dynamodb.transact_write_items.side_effect = DuplicateError()

        persisted = self.app.persist_sighting(record, "birdalert-sightings")

        self.assertFalse(persisted)
        first_transaction = self.app.dynamodb.transact_write_items.call_args_list[0]
        self.assertEqual(
            first_transaction.kwargs["TransactItems"][0]["Put"]["ConditionExpression"],
            "attribute_not_exists(sighting_id)",
        )
        self.app.dynamodb.transact_write_items.assert_called_once()

    @patch.dict(os.environ, {"SIGHTINGS_TABLE": "birdalert-sightings"}, clear=True)
    def test_existing_sighting_is_not_written_again_for_the_same_source_region(self):
        record = valid_record()
        transformed = self.app.process_payload(
            [record], "GB-ENG", datetime(2026, 9, 30, 10, 17, tzinfo=UTC)
        )["accepted"][0]
        record_id = self.app.sighting_id(transformed)
        self.app.s3.get_object.return_value = {
            "Body": io.BytesIO(json.dumps([record]).encode("utf-8"))
        }
        self.app.dynamodb.batch_get_item.return_value = {
            "Responses": {
                "birdalert-sightings": [
                    {
                        "sighting_id": {"S": record_id},
                        "source_regions": {"SS": ["GB-ENG"]},
                    }
                ]
            },
            "UnprocessedKeys": {},
        }

        result = self.app.process_s3_record(
            {
                "s3": {
                    "bucket": {"name": "birdalert-raw"},
                    "object": {"key": "GB-ENG/20260930T101700.000000Z-test.json"},
                }
            }
        )

        self.assertEqual(result["existing_records"], 1)
        self.assertEqual(result["persisted_records"], 0)
        self.app.dynamodb.transact_write_items.assert_not_called()

    @patch.dict(os.environ, {"SIGHTINGS_TABLE": "birdalert-sightings"}, clear=True)
    def test_new_source_region_updates_provenance_and_region_query_records(self):
        record = valid_record()
        transformed = self.app.process_payload(
            [record], "GB-SCT", datetime(2026, 9, 30, 10, 17, tzinfo=UTC)
        )["accepted"][0]
        record_id = self.app.sighting_id(transformed)
        self.app.s3.get_object.return_value = {
            "Body": io.BytesIO(json.dumps([record]).encode("utf-8"))
        }
        self.app.dynamodb.batch_get_item.return_value = {
            "Responses": {
                "birdalert-sightings": [
                    {
                        "sighting_id": {"S": record_id},
                        "source_regions": {"SS": ["GB-ENG"]},
                    }
                ]
            },
            "UnprocessedKeys": {},
        }

        with patch.object(self.app, "raw_object_context", return_value=("GB-SCT", datetime(2026, 9, 30, 10, 17, tzinfo=UTC))):
            result = self.app.process_s3_record(
                {
                    "s3": {
                        "bucket": {"name": "birdalert-raw"},
                        "object": {"key": "GB-ENG/20260930T101700.000000Z-test.json"},
                    }
                }
            )

        self.assertEqual(result["provenance_updated_records"], 1)
        transaction = self.app.dynamodb.transact_write_items.call_args.kwargs["TransactItems"]
        self.assertEqual(transaction[0]["Update"]["ConditionExpression"], "attribute_exists(sighting_id)")
        self.assertEqual(len(transaction), 3)

    def test_incomplete_and_invalid_records_are_rejected(self):
        missing_privacy_record = valid_record()
        del missing_privacy_record["locationPrivate"]
        invalid_records = [
            valid_record(comName=""),
            valid_record(obsDt="not-a-time"),
            valid_record(obsDt="2026-09-30"),
            valid_record(lat=91),
            valid_record(lng=-181),
            valid_record(obsValid="yes"),
            valid_record(locationPrivate="yes"),
            missing_privacy_record,
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

    @patch.dict(os.environ, {"SIGHTINGS_TABLE": "birdalert-sightings"}, clear=True)
    def test_handler_reads_url_encoded_s3_object_and_persists_records(self):
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
        self.app.dynamodb.transact_write_items.assert_called_once()
        self.app.dynamodb.put_item.assert_called_once()
        processing_status = self.app.dynamodb.put_item.call_args.kwargs
        self.assertEqual(
            processing_status["Item"]["sighting_id"],
            {"S": self.app.PROCESSING_STATUS_ID},
        )
        self.assertIn(
            "last_successful_processing_at", processing_status["Item"]
        )
        self.assertEqual(
            result,
            {
                "processed_objects": 1,
                "accepted_records": 1,
                "rejected_records": 0,
                "persisted_records": 1,
                "existing_records": 0,
                "provenance_updated_records": 0,
            },
        )

    @patch.dict(os.environ, {"SIGHTINGS_TABLE": "birdalert-sightings"}, clear=True)
    def test_processing_status_is_written_after_a_successful_empty_snapshot(self):
        self.app.s3.get_object.return_value = {
            "Body": io.BytesIO(json.dumps([]).encode("utf-8"))
        }

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

        self.app.dynamodb.put_item.assert_called_once_with(
            TableName="birdalert-sightings",
            Item={
                "sighting_id": {"S": self.app.PROCESSING_STATUS_ID},
                "last_successful_processing_at": unittest.mock.ANY,
            },
        )

    def test_persistence_failure_fails_processing(self):
        self.app.s3.get_object.return_value = {
            "Body": io.BytesIO(json.dumps([valid_record()]).encode("utf-8"))
        }
        self.app.dynamodb.transact_write_items.side_effect = RuntimeError("DynamoDB unavailable")

        with patch.dict(os.environ, {"SIGHTINGS_TABLE": "birdalert-sightings"}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "DynamoDB unavailable"):
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
