"""Health checks must reject HTTP-success-shaped but invalid results."""
import copy
import json
from pathlib import Path
import runpy
import unittest
probe=runpy.run_path(str(Path(__file__).resolve().parents[3]/"scripts/checks/public_health.py"))

class PublicHealthContractTests(unittest.TestCase):
 def test_missing_progress_error_terminal_and_duplicate_result_cannot_pass(self):
  invalid=['', 'event: result\ndata: {}\n\n', 'event: stage\ndata: {}\n\nevent: problem\ndata: {}\n\n', 'event: stage\ndata: {}\n\nevent: result\ndata: {}\n\nevent: result\ndata: {}\n\n']
  for value in invalid:
   with self.subTest(value=value),self.assertRaises(probe['ProbeFailed']):probe['terminal_result'](value)
 def test_live_or_unchecked_or_wrong_domain_result_cannot_pass(self):
  project=probe['PROJECT']
  for value in [{}, {'project':project,'live_ai':True}, {'project':project,'live_ai':False,'checks':{}}, {'project':project,'live_ai':False,'checks':{'independent':False}}, {'project':project,'live_ai':False,'checks':{'independent':True},'summary':{}}]:
   with self.subTest(value=value),self.assertRaises(probe['ProbeFailed']):probe['validate_result'](value)
 def test_probe_refuses_credentials_paths_and_unrelated_origins(self):
  for origin in ['https://outside.example','https://user:secret@x.vercel.app','https://x.vercel.app/private','https://x.vercel.app?secret=value','file:///etc/passwd']:
   with self.subTest(origin=origin),self.assertRaises((probe['ProbeFailed'],AttributeError)):probe['Probe'](origin)
 def test_valid_terminal_and_progress_are_required_together(self):
  body='event: stage\ndata: {"stage":"source","state":"complete"}\n\nevent: result\ndata: {"value":3}\n\n'
  self.assertEqual(probe['terminal_result'](body),{'value':3})
