# -*- coding: utf-8 -*-
"""Corrections to the Math and English lessons imported from Omar's workbook.

The workbook lessons live only in backend/content/{math,english}.json, which
scripts/import_content.py rewrites from the spreadsheets. Editing the JSON by
hand would be lost on the next import, so the corrections live here and
build_practice.py applies them on every build.

Keyed by lesson number (math-lesson-12 -> 12). Each value sets lesson fields:

    'title', 'formula', 'example', 'tip'  replace that field
    'steps', 'sub', 'answer'             replace the "Steps:", "Numeric substitution:"
                                         or "Answer:" line of the explanation

Why each one is here: the imported lesson was wrong (percent increase taught
turning a percent into a decimal; percent decrease used an example that went
up; the SOH CAH TOA working was a spreadsheet date, 46086), or its answer line
gave a label ("Answer: expected value") or a different quantity ("Answer: 3",
the common difference, for "Find: next term") instead of the answer.
"""

import re
import sys

MATH = {
    11: {'answer': '25%'},
    12: {'formula': '(new − old)/old × 100',
         'steps': 'Subtract the old value from the new one → divide by the old value → multiply by 100.',
         'sub': '(50 − 40)/40 × 100 → 10/40 × 100 → 25%',
         'answer': '25%',
         'example': 'Given: old=40, new=50. Find: percent increase'},
    13: {'formula': '(old − new)/old × 100',
         'steps': 'Subtract the new value from the old one → divide by the old value → multiply by 100.',
         'sub': '(50 − 35)/50 × 100 → 15/50 × 100 → 30%',
         'answer': '30%',
         'example': 'Given: original=50, new=35. Find: percent decrease'},
    17: {'answer': '(4, 8)'},
    18: {'answer': 'No solution: the lines are parallel'},
    19: {'answer': 'Infinitely many solutions'},
    22: {'answer': '−16, so there are no real roots'},
    23: {'answer': '(3, 2)'},
    30: {'title': 'Exponential Model', 'topicTitle': 'Exponential Model',
         'steps': 'Identify the starting value a and the growth factor b → raise b to the power x → multiply by a.',
         'sub': '100(1.05)² → 100(1.1025) → 110.25',
         'example': 'Given: a=100, b=1.05, x=2. Find: y=a(b)^x'},
    53: {'steps': 'Absolute value is the distance from zero → |x| = a has two solutions, x = a and x = −a, when a > 0.',
         'sub': '|x| = 7 → x = 7 or x = −7',
         'answer': 'x = 7 or x = −7',
         'example': 'Given: |x| = 7. Find: x'},
    54: {'sub': '2, 5, 8 → difference = 3 → next term = 8 + 3 = 11', 'answer': '11'},
    55: {'sub': '3, 6, 12 → ratio = 2 → next term = 12 × 2 = 24', 'answer': '24'},
    59: {'answer': '(4, 4)'},
    60: {'answer': '15'},
    61: {'answer': '4'},
    62: {'example': 'Given: rates 1/2 and 1/3 of a tank per hour. Find: time to fill it together'},
    66: {'steps': 'Convert percentages to decimals → multiply by each quantity → add the pure amounts → divide by the total volume.',
         'sub': '0.3(10) + 0.5(20) = 3 + 10 = 13 → 13/30 ≈ 0.433',
         'answer': 'about 43.3%',
         'example': 'Given: 10 L of a 30% solution and 20 L of a 50% solution. Find: concentration of the mixture'},
    70: {'steps': 'Subtract h inside the function to move the graph h right → add k outside to move it k up.',
         'sub': 'f(x−2) + 3 = (x−2)² + 3',
         'answer': '2 right and 3 up'},
    77: {'sub': '½ × 3² × π = 4.5π ≈ 14.14', 'answer': '14.14'},
    81: {'answer': '2.1'},
    88: {'title': 'Unit Circle Values', 'topicTitle': 'Unit Circle Values',
         'steps': 'The point at angle θ on the unit circle is (cos θ, sin θ) → read off the coordinates.',
         'sub': 'θ = 90° → (cos 90°, sin 90°) = (0, 1)',
         'example': 'Given: θ = 90°. Find: (cos θ, sin θ)'},
    89: {'steps': 'Label the sides from the angle → pick the ratio that uses the sides you know → divide.',
         'sub': 'sin = opp/hyp = 3/5 = 0.6',
         'example': 'Given: opposite=3, hypotenuse=5. Find: sin'},
    95: {'answer': '2%'},
    97: {'sub': 'value 1 → 1, value 2 → 2, value 3 → 2, value 4 → 1',
         'answer': 'bars of height 1, 2, 2 and 1'},
    98: {'sub': '(1, 2), (2, 3), (3, 5) → y rises as x rises', 'answer': 'positive correlation'},
    100: {'sub': 'mean = 4 → deviations −2, 0, 2 → squares 4, 0, 4 → 8 ÷ 3 ≈ 2.67',
          'answer': 'about 2.67',
          'example': 'Given: values 2, 4, 6. Find: variance'},
    104: {'title': 'Log Base 10', 'topicTitle': 'Log Base 10'},
    105: {'sub': '2f(x) = 2x² → every height doubles', 'answer': 'vertical stretch by a factor of 2'},
    106: {'sub': 'f(x/2) = (x/2)² = x²/4 → the graph is twice as wide',
          'answer': 'horizontal stretch by a factor of 2'},
    107: {'answer': '(2, 0)'},
    108: {'answer': '(0, 5)'},
    111: {'sub': '100(1.03)² = 100(1.0609) = 106.09', 'answer': '106.09'},
    115: {'answer': '3.25'},
    119: {'answer': 'a horizontal line through (0, 4)'},
    120: {'answer': 'a vertical line through (2, 0)'},
    121: {'sub': 'a₂ = a₁ + d = 2 + 3 = 5', 'answer': '5'},
    125: {'sub': '−x² ≤ 0, so y ≤ 4, reached at x = 0', 'answer': '4'},
    126: {'sub': 'x² ≥ 0, so y ≥ 0, reached at x = 0', 'answer': '0'},
    130: {'steps': 'Multiply numerator and denominator by the radical, or by the conjugate when the denominator is a + √b.'},
    133: {'answer': '2 outcomes: H and T'},
    134: {'answer': '0.25'},
    135: {'steps': 'Subtract the shift inside the function → the graph moves that far to the right.',
          'sub': 'f(x−3) = (x−3)²', 'answer': 'y = (x − 3)²'},
    136: {'sub': 'f(x) + 2 = x² + 2', 'answer': 'y = x² + 2'},
    139: {'answer': 'x ≥ 0'},
    140: {'answer': 'y ≥ 0'},
    142: {'sub': 'the long tail is on the right', 'answer': 'skewed right'},
    144: {'answer': '5'},
    148: {'title': 'Expected Value (Two Outcomes)', 'topicTitle': 'Expected Value (Two Outcomes)',
          'answer': '1.6',
          'example': 'Given: values 1, 2 with probabilities 0.4, 0.6. Find: expected value'},
    155: {'sub': '|−9| = 9', 'example': 'Given: x=−9. Find: |x|'},
    156: {'sub': 'x = 0 → y = 3; y = 0 → x = −1.5', 'answer': '(0, 3) and (−1.5, 0)'},
    157: {'answer': '2'},
    158: {'answer': '20'},
    159: {'answer': 'symmetric about the y-axis'},
}

ENGLISH = {
    # The examples named one person and used another's pronoun ("Omar finished her homework").
    3: {'example': 'The students finished their homework.'},
    24: {'example': 'She taught herself to code.'},
    64: {'example': 'My sister said that she was tired.'},
    # Same title as lesson 44 once the "17. " is gone.
    110: {'title': 'Gerund subjects are singular'},
}

FIXES = {'math': MATH, 'english': ENGLISH}
LINES = (('steps', 'Steps:'), ('sub', 'Numeric substitution:'), ('answer', 'Answer:'))
PREFIX = dict(LINES)


def _set_line(lines, field, value):
    prefix = PREFIX[field]
    text = '%s %s' % (prefix, value)
    for i, line in enumerate(lines):
        if line.startswith(prefix):
            lines[i] = text
            return
    # Keep Steps, then the working, then the Answer.
    order = [p for _, p in LINES]
    rank = order.index(prefix)
    at = len([l for l in lines if any(l.startswith(p) for p in order[:rank])])
    lines.insert(at, text)


def _tidy_english(lesson):
    """The subject-verb lessons were titled "01. Singular subject -> singular verb"."""
    lesson['title'] = re.sub(r'^\d+\.\s*', '', lesson.get('title', ''))
    for field in ('title', 'example', 'tip'):
        lesson[field] = lesson.get(field, '').replace(' -> ', ' → ').replace('->', '→')
    lesson['explanation'] = [s.replace(' -> ', ' → ').replace('->', '→') for s in lesson.get('explanation', [])]


def apply(subject, lessons):
    """Correct the imported lessons in place. Running it twice changes nothing."""
    fixes = FIXES.get(subject)
    if not fixes:
        return 0
    by_number = {int(l['id'].rsplit('-', 1)[-1]): l for l in lessons}
    missing = sorted(set(fixes) - set(by_number))
    if missing:
        sys.exit('%s: lesson fixes for lessons that do not exist: %s' % (subject, missing))
    if subject == 'english':
        for lesson in lessons:
            _tidy_english(lesson)
    for number, change in fixes.items():
        lesson = by_number[number]
        for field, value in change.items():
            if field in PREFIX:
                _set_line(lesson.setdefault('explanation', []), field, value)
            else:
                lesson[field] = value
    return len(fixes)
