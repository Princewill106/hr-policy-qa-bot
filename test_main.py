import unittest

import main


class QaTests(unittest.TestCase):
    def setUp(self):
        self.index = main.Index(main.load_sections("handbook.md"))

    def test_retrieval(self):
        self.assertEqual(main.answer(self.index, "How many annual leave days?")["source"], "Annual leave")
        self.assertEqual(main.answer(self.index, "Who approves overtime?")["source"], "Overtime")
        r = main.answer(self.index, "transport allowance for client visits")
        self.assertIn("15,000", r["answer"])

    def test_refuses_unknown(self):
        self.assertIsNone(main.answer(self.index, "company stance on crypto investments")["source"])


if __name__ == "__main__":
    unittest.main()
