import importlib.util
import sys
import unittest
from pathlib import Path
from unittest.mock import call, patch


BUILD_ALL_PATH = Path(__file__).resolve().parents[1] / "build_lambdas.py"


class BuildLambdasTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location("build_lambdas", BUILD_ALL_PATH)
        cls.app = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.app)

    def test_builds_every_lambda_with_the_current_python(self):
        with patch.object(self.app.subprocess, "run") as run:
            self.app.main()

        self.assertEqual(
            run.call_args_list,
            [
                call(
                    [sys.executable, str(self.app.ROOT / "scripts" / script_name)],
                    check=True,
                )
                for script_name in self.app.BUILD_SCRIPTS
            ],
        )


if __name__ == "__main__":
    unittest.main()
