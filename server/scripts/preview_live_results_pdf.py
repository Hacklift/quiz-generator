"""Synthetic manual review fixtures. Run with PYTHONPATH=. from the repo root.

Requires PyMuPDF for PNG rendering; it is not a runtime dependency.
"""

import argparse
from pathlib import Path

import pymupdf

from server.app.quiz.utils.live_results_export import generate_live_results_pdf


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    for label, count, questions, long in (
        ("small", 2, 3, False),
        ("many", 35, 8, False),
        ("long", 2, 8, True),
        ("multipage", 2, 80, False),
    ):
        payload = {
            "title": "Évaluation — Sciences & société"
            + (" / Comprendre notre monde" * 12 if long else ""),
            "question_count": questions,
            "participants": [
                {
                    "participant_name": f"Éloïse Müller {index + 1}"
                    + (" de Saint-Exupéry" * 12 if long else ""),
                    "score": 1,
                    "total_questions": questions,
                    "percentage": round(100 / questions, 2),
                    "graded_answers": [
                        {
                            "question_index": 0,
                            "selected_answer": "A",
                            "is_correct": True,
                        },
                        {
                            "question_index": 1,
                            "selected_answer": "B",
                            "is_correct": False,
                        },
                    ],
                }
                for index in range(count)
            ],
        }
        path = args.output / f"{label}.pdf"
        path.write_bytes(generate_live_results_pdf(payload).getvalue())
        pdf = pymupdf.open(path)
        for index in sorted({0, min(1, len(pdf) - 1), len(pdf) - 1}):
            pdf[index].get_pixmap(matrix=pymupdf.Matrix(1.3, 1.3)).save(
                args.output / f"{label}-{index + 1}.png"
            )
        print(f"{path}: {len(pdf)} pages")


if __name__ == "__main__":
    main()
