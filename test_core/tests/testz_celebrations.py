"""Script to explicitly test all grade-based celebrations."""

from test_core.celebrations import celebrate_grade
import time

def test_all_celebrations():
    test_grades = ["A+", "A", "A-", "B+", "B", "B-", "C+", "C", "C-", "D+", "D", "D-", "F"]
    for grade in test_grades:
        print(f"\n--- Testing celebration for grade: {grade} ---")
        celebrate_grade(grade)
        print(f"--- Finished celebration for grade: {grade} ---\n")
        time.sleep(2)  # Pause between each test for clarity


if __name__ == "__main__":
    test_all_celebrations()
