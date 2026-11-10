import unittest

from evaluation.text_matching import contains_term, evaluate_q04_answer


class TextMatchingTests(unittest.TestCase):
    def test_q04_direct_answer_with_split_pdf_term_passes(self):
        answer = (
            "The variables are mis fit strain between the thin film and "
            "substrate, defect dipoles doping, and film thickness."
        )
        result = evaluate_q04_answer(answer)
        self.assertTrue(result["passed"])
        self.assertTrue(result["checks"]["misfit_strain"])

    def test_case_whitespace_ligature_and_hyphen_variants(self):
        variants = (
            "MIS   FIT strain",
            "mis ﬁt strain",
            "mis-fit strain",
            "mis‐fit strain",
            "misfit strain",
        )
        for variant in variants:
            with self.subTest(variant=variant):
                self.assertTrue(contains_term(variant, "misfit strain"))

    def test_tensile_strain_is_not_misfit_strain(self):
        self.assertFalse(contains_term("tensile strain", "misfit strain"))
        self.assertFalse(
            evaluate_q04_answer(
                "Tensile strain, defect dipole doping, and film thickness."
            )["checks"]["misfit_strain"]
        )

    def test_phrase_hyphen_can_match_space(self):
        self.assertTrue(contains_term("phase-field simulation", "phase field"))

    def test_hyphenated_line_break_is_rejoined(self):
        self.assertTrue(contains_term("Fou-\nrier-space", "Fourier space"))

    def test_no_fuzzy_or_partial_token_matching(self):
        self.assertFalse(contains_term("misfitted strain", "misfit strain"))
        self.assertFalse(contains_term("film thicknesses", "film thickness"))


if __name__ == "__main__":
    unittest.main()
