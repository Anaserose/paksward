"""Start-up behavior of main.py."""
import os
import subprocess
import sys
import unittest

from tests.helpers import ROOT, DataDirTest, read_text


class TestStartup(DataDirTest):
    def run_main(self, *args):
        env = dict(os.environ, PAKSWARD_DATA_DIR=self.tmp)
        return subprocess.run([sys.executable, os.path.join(ROOT, "main.py"), *args], cwd=ROOT, env=env,
                              capture_output=True, text=True, timeout=30)

    def test_damaged_users_file_stops_start_up_and_is_left_alone(self):
        path = os.path.join(self.tmp, "users.json")
        with open(path, "w") as f:
            f.write("{bad json")
        r = self.run_main("--no-browser")
        self.assertEqual(r.returncode, 1)
        self.assertIn("could not read", r.stderr)
        self.assertEqual(read_text(path), "{bad json")          # nothing overwritten
        self.assertNotIn("Traceback", r.stderr)

    def test_help_works(self):
        r = self.run_main("--help")
        self.assertEqual(r.returncode, 0)
        self.assertIn("--no-browser", r.stdout)


if __name__ == "__main__":
    unittest.main()
