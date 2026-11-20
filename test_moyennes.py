import unittest

from moyennes import calculate_averages, valid_grade


def page(subject, grade):
    return {
        "properties": {
            "Enseignement": {"title": [{"plain_text": subject}]},
            "Note obtenue": {"number": grade},
        }
    }


class AverageTests(unittest.TestCase):
    def test_missing_grades_are_ignored(self):
        rows = [
            page("Maths", 12),
            page("Maths", None),
            page("Maths", 16),
            page("Français", None),
        ]
        subject, general = calculate_averages(rows)
        self.assertEqual(subject, {"Maths": 14.0})
        self.assertEqual(general, 14.0)

    def test_true_zero_is_preserved(self):
        subject, general = calculate_averages([page("Maths", 0), page("Maths", 20)])
        self.assertEqual(subject["Maths"], 10.0)
        self.assertEqual(general, 10.0)

    def test_general_average_weights_subjects_equally(self):
        rows = [
            page("Maths", 10),
            page("Maths", 14),
            page("Français", 18),
        ]
        subject, general = calculate_averages(rows)
        self.assertEqual(subject, {"Français": 18.0, "Maths": 12.0})
        self.assertEqual(general, 15.0)

    def test_invalid_grades_are_rejected(self):
        for grade in (-1, 20.1, float("inf"), float("nan"), "15", True):
            with self.subTest(grade=grade):
                self.assertIsNone(valid_grade(grade))

        subject, general = calculate_averages([
            page("Maths", -1),
            page("Maths", 20.1),
            page("Maths", 12),
        ])
        self.assertEqual(subject["Maths"], 12.0)
        self.assertEqual(general, 12.0)

    def test_no_valid_notes(self):
        self.assertIsNone(calculate_averages([
            page("Maths", None),
            page("Français", -2),
        ]))


if __name__ == "__main__":
    unittest.main()
