"""Exercise the public CLI without executing any discovered project scripts."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


class CliTests(unittest.TestCase):
    def test_workspace_list_and_explicit_inspect(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'package.json').write_text('{}')
            child = root / 'app'
            child.mkdir()
            marker = root / 'must-not-exist'
            (child / 'package.json').write_text(json.dumps({
                'name': 'example', 'scripts': {'test': f'touch {marker}'},
            }))
            env = {**os.environ, 'PYTHONPATH': str(Path(__file__).resolve().parents[1] / 'src')}
            def invoke(*args):
                result = subprocess.run([sys.executable, '-m', 'project_doctor', *args],
                                        cwd=root, env=env, capture_output=True, text=True)
                self.assertEqual(0, result.returncode, result.stderr)
                return json.loads(result.stdout)
            listing = invoke('list', '--root', str(root), '--json')
            self.assertEqual(1, listing['count'])
            self.assertEqual(str(child.resolve()), listing['projects'][0]['path'])
            inspected = invoke('inspect', '.', '--root', str(root), '--json')
            self.assertEqual(str(root.resolve()), inspected['path'])
            self.assertFalse(marker.exists())
