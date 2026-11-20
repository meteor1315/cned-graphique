import unittest

from moyennes import calculate_averages


def row(subject, score):
    return {
        "properties": {
            "Enseignement": {"title": [{"plain_text": subject}]},
            "Note obtenue": {"number": score},
        }
    }


class CalculateAveragesTests(unittest.TestCase):
    def test_missing_scores_are_excluded_and_zero_is_kept(self):
        subjects, overall = calculate_averages(
            [row("Maths", 0), row("Maths", None), row("Français", 12)]
        )
        self.assertEqual(subjects, {"Français": 12.0, "Maths": 0.0})
        self.assertEqual(overall, 6.0)

    def test_subjects_have_equal_weight_with_different_number_of_assignments(self):
        subjects, overall = calculate_averages(
            [row("Maths", 10), row("Maths", 20), row("Histoire", 5)]
        )
        self.assertEqual(subjects["Maths"], 15.0)
        self.assertEqual(overall, 10.0)

    def test_invalid_scores_and_empty_subjects_are_excluded(self):
        subjects, overall = calculate_averages(
            [row("Maths", 21), row("Physique", -1), row("SVT", float("nan")), row("", 10)]
        )
        self.assertEqual(subjects, {})
        self.assertIsNone(overall)


if __name__ == "__main__":
    unittest.main()
