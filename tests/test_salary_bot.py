import os
import tempfile
import unittest

from salary_bot import normalize_phone, build_month_keyboard, decode_salary_message, load_environment


class SalaryBotTests(unittest.TestCase):
    def test_normalize_phone_adds_plus_prefix(self):
        self.assertEqual(normalize_phone("998901234567"), "+998901234567")
        self.assertEqual(normalize_phone("+998901234567"), "+998901234567")

    def test_build_month_keyboard_groups_in_rows_of_three(self):
        months = ["2024-01", "2024-02", "2024-03", "2024-04"]
        keyboard = build_month_keyboard(months)
        self.assertEqual(keyboard[0], [{"text": "2024-01"}, {"text": "2024-02"}, {"text": "2024-03"}])
        self.assertEqual(keyboard[1], [{"text": "2024-04"}])

    def test_decode_salary_message_uses_table_number_offset(self):
        encoded = "72:101:108:108:111:108"
        decoded = decode_salary_message(encoded, 0)
        self.assertEqual(decoded, "Hello")

    def test_load_environment_reads_from_project_directory(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            env_path = os.path.join(temp_dir, ".env")
            with open(env_path, "w", encoding="utf-8") as handle:
                handle.write("TG_BOT_TOKEN=test-token\n")

            os.environ.pop("TG_BOT_TOKEN", None)
            load_environment(base_dir=temp_dir)
            self.assertEqual(os.environ.get("TG_BOT_TOKEN"), "test-token")
            os.environ.pop("TG_BOT_TOKEN", None)


if __name__ == "__main__":
    unittest.main()
