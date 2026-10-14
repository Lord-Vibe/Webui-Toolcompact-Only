import importlib.util
from pathlib import Path
import unittest
spec = importlib.util.spec_from_file_location('tcm', Path(__file__).resolve().parents[1] / 'tool_context_manager.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
class Tests(unittest.TestCase):
    def setUp(self):
        self.messages = [
            {'role':'assistant','tool_calls':[{'id':'a','function':{'name':'shell','arguments':'ls'}}]},
            {'role':'tool','tool_call_id':'a','content':'x'*4000},
            {'role':'assistant','tool_calls':[{'id':'b','function':{'name':'shell','arguments':'pwd'}}]},
            {'role':'tool','tool_call_id':'b','content':'y'*4000}]
    def test_threshold(self):
        self.assertIsNone(mod.compact({'messages':self.messages}, 100000, 1)[1])
    def test_manual_and_retention(self):
        out, stats = mod.compact({'messages':self.messages}, 100000, 1, True)
        self.assertIsNotNone(stats)
        self.assertEqual(len(out['messages']), 3)
        self.assertEqual(out['messages'][-2:], self.messages[-2:])
        self.assertEqual(len(self.messages), 4)
    def test_incomplete(self):
        self.assertEqual(mod.tool_groups(self.messages[:1]), [])
    def test_idempotence(self):
        out, _ = mod.compact({'messages':self.messages}, 100, 0)
        self.assertEqual(mod.tool_groups(out['messages']), [])
if __name__ == '__main__': unittest.main()
