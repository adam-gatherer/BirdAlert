import importlib
import json
import sys
import types
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, call, patch


POLLERS_PATH = Path(__file__).resolve().parents[1] / "src" / "poller"
sys.path.insert(0, str(POLLERS_PATH))


class FakeResponse:
    def __init__(self, content, data, status_error=None):
        self.content = content
        self.data = data
        self.status_error = status_error

    def raise_for_status(self):
        if self.status_error:
            raise self.status_error
        return None

    def json(self):
        if isinstance(self.data, Exception):
            raise self.data
        return self.data


class PollerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        boto3_stub = types.ModuleType("boto3")
        boto3_stub.client = Mock()
        requests_stub = types.ModuleType("requests")
        requests_stub.get = Mock()
        with patch.dict(
            sys.modules,
            {"boto3": boto3_stub, "requests": requests_stub},
        ):
            cls.app = importlib.import_module("app")

    def setUp(self):
        self.app.ssm = Mock()
        self.app.ssm.get_parameter.return_value = {
            "Parameter": {"Value": "test-api-key"}
        }
        self.app.s3 = Mock()

    def test_configured_regions_are_trimmed_and_validated(self):
        self.assertEqual(
            self.app.configured_regions(" GB-ENG, GB-SCT "),
            ["GB-ENG", "GB-SCT"],
        )

        for value in ("", "  ", "GB-ENG,", "GB-ENG,,GB-SCT", "GB-ENG,GB-ENG"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.app.configured_regions(value)

    def test_keys_for_same_timestamp_are_unique_and_region_prefixed(self):
        uuid_values = [SimpleNamespace(hex="first"), SimpleNamespace(hex="second")]
        with patch.object(self.app.uuid, "uuid4", side_effect=uuid_values):
            first = self.app.raw_object_key("GB-ENG", timestamp="20260929T120000.000000Z")
            second = self.app.raw_object_key("GB-ENG", timestamp="20260929T120000.000000Z")

        self.assertTrue(first.startswith("GB-ENG/"))
        self.assertNotEqual(first, second)

    @patch.dict(
        "os.environ",
        {
            "EBIRD_REGIONS": "GB-ENG,GB-SCT",
            "PARAMETER_NAME": "/birdalert/dev/ebird/api-key",
            "RAW_BUCKET": "birdalert-raw",
        },
        clear=True,
    )
    def test_polls_each_region_and_stores_complete_response_bytes(self):
        responses = [
            FakeResponse(b'[{"name":"Robin"}]', [{"name": "Robin"}]),
            FakeResponse(b'[{"name":"Wren"}]', [{"name": "Wren"}]),
        ]
        with patch.object(self.app.requests, "get", side_effect=responses) as get:
            result = self.app.lambda_handler({}, None)

        get.assert_has_calls(
            [
                call(
                    "https://api.ebird.org/v2/data/obs/GB-ENG/recent/notable",
                    headers={"X-eBirdApiToken": "test-api-key"},
                    timeout=30,
                ),
                call(
                    "https://api.ebird.org/v2/data/obs/GB-SCT/recent/notable",
                    headers={"X-eBirdApiToken": "test-api-key"},
                    timeout=30,
                ),
            ]
        )
        self.assertEqual(
            self.app.ssm.get_parameter.call_args.kwargs["Name"],
            "/birdalert/dev/ebird/api-key",
        )
        self.assertTrue(
            all(
                mock_call.kwargs["WithDecryption"]
                for mock_call in self.app.ssm.get_parameter.mock_calls
            )
        )
        self.assertEqual(
            [put.kwargs["Body"] for put in self.app.s3.put_object.call_args_list],
            [response.content for response in responses],
        )
        self.assertEqual(
            [put.kwargs["Key"].split("/", 1)[0] for put in self.app.s3.put_object.call_args_list],
            ["GB-ENG", "GB-SCT"],
        )
        body = json.loads(result["body"])
        self.assertEqual(body["records"], 2)
        self.assertEqual([item["region"] for item in body["regions"]], ["GB-ENG", "GB-SCT"])

    @patch.dict(
        "os.environ",
        {
            "EBIRD_REGIONS": "GB-ENG,GB-SCT",
            "PARAMETER_NAME": "/birdalert/dev/ebird/api-key",
            "RAW_BUCKET": "birdalert-raw",
        },
        clear=True,
    )
    def test_region_failure_is_logged_and_fails_invocation(self):
        with patch.object(
            self.app.requests,
            "get",
            side_effect=[FakeResponse(b"[]", []), RuntimeError("network down")],
        ):
            with self.assertRaisesRegex(RuntimeError, "GB-SCT"):
                self.app.lambda_handler({}, None)

        self.assertEqual(self.app.s3.put_object.call_count, 1)

    @patch.dict(
        "os.environ",
        {
            "EBIRD_REGIONS": "GB-ENG",
            "PARAMETER_NAME": "/birdalert/dev/ebird/api-key",
            "RAW_BUCKET": "birdalert-raw",
        },
        clear=True,
    )
    def test_invalid_json_fails_without_writing_raw_object(self):
        with patch.object(
            self.app.requests,
            "get",
            return_value=FakeResponse(b"not json", ValueError("invalid json")),
        ):
            with self.assertRaisesRegex(RuntimeError, "GB-ENG"):
                self.app.lambda_handler({}, None)

        self.app.s3.put_object.assert_not_called()

    @patch.dict(
        "os.environ",
        {
            "EBIRD_REGIONS": "GB-ENG",
            "PARAMETER_NAME": "/birdalert/dev/ebird/api-key",
            "RAW_BUCKET": "birdalert-raw",
        },
        clear=True,
    )
    def test_non_array_json_is_preserved_but_region_fails(self):
        response = FakeResponse(b'{"message":"unexpected shape"}', {"message": "unexpected shape"})
        with patch.object(self.app.requests, "get", return_value=response):
            with self.assertRaisesRegex(RuntimeError, "GB-ENG"):
                self.app.lambda_handler({}, None)

        self.app.s3.put_object.assert_called_once()
        self.assertEqual(self.app.s3.put_object.call_args.kwargs["Body"], response.content)

    @patch.dict(
        "os.environ",
        {
            "EBIRD_REGIONS": "GB-ENG",
            "PARAMETER_NAME": "/birdalert/dev/ebird/api-key",
            "RAW_BUCKET": "birdalert-raw",
        },
        clear=True,
    )
    def test_http_error_fails_without_writing_raw_object(self):
        with patch.object(
            self.app.requests,
            "get",
            return_value=FakeResponse(
                b"error", None, status_error=RuntimeError("HTTP 500")
            ),
        ):
            with self.assertRaisesRegex(RuntimeError, "GB-ENG"):
                self.app.lambda_handler({}, None)

        self.app.s3.put_object.assert_not_called()

    @patch.dict(
        "os.environ",
        {
            "EBIRD_REGIONS": "GB-ENG",
            "PARAMETER_NAME": "/birdalert/dev/ebird/api-key",
            "RAW_BUCKET": "birdalert-raw",
        },
        clear=True,
    )
    def test_s3_write_failure_fails_invocation(self):
        self.app.s3.put_object.side_effect = RuntimeError("write failed")
        with patch.object(
            self.app.requests,
            "get",
            return_value=FakeResponse(b"[]", []),
        ):
            with self.assertRaisesRegex(RuntimeError, "GB-ENG"):
                self.app.lambda_handler({}, None)


if __name__ == "__main__":
    unittest.main()
