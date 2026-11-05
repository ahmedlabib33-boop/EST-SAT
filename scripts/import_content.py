#!/usr/bin/env python3
"""Import the SAT lesson and practice banks from the Excel workbooks.

Reads the six `learning_*` workbooks and writes `backend/content/{math,english}.json`.
Standard library only -- no openpyxl, no pandas, no build step. Run it by hand when
the workbooks change and commit the JSON it produces:

    python scripts/import_content.py [--source DIR] [--check]

`--check` regenerates in memory and exits non-zero if the committed JSON is stale.
"""

import argparse
import json
import os
import re
import sys
import zipfile
import xml.etree.ElementTree as ET

NS = '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_SOURCE = os.path.join('D:' + os.sep, 'Omar-Eng.Ola', 'SAT_Quiz_App', 'data')
OUT_DIR = os.path.join(REPO, 'backend', 'content')

# Expected shape of each workbook. The importer fails loudly if a column disappears.
WORKBOOKS = {
    'math': {
        'topics': ('learning_math_topics.xlsx',
                   ('topic_id', 'topic_name', 'order')),
        'lessons': ('learning_math_content.xlsx',
                    ('topic_id', 'domain', 'lesson_title', 'formula', 'example',
                     'explanation', 'difficulty', 'arabic')),
        'questions': ('learning_math_questions.xlsx',
                      ('domain', 'lesson_title', 'formula', 'difficulty', 'question',
                       'option_a', 'option_b', 'option_c', 'option_d',
                       'correct_answer', 'explanation')),
    },
    'english': {
        'topics': ('learning_english_topics.xlsx',
                   ('topic_id', 'topic_name', 'order')),
        'lessons': ('learning_english_content.xlsx',
                    ('topic_id', 'lesson_title', 'rule_title', 'explanation',
                     'example', 'tip')),
        'questions': ('learning_english_questions.xlsx',
                      ('topic_id', 'lesson_title', 'rule_title', 'difficulty',
                       'question', 'option_a', 'option_b', 'option_c', 'option_d',
                       'correct_answer', 'explanation')),
    },
}

# Math is 159 workbook rows minus 4 that repeat an earlier lesson verbatim.
EXPECTED = {
    'math': {'topics': 5, 'lessons': 155, 'practice': 308},
    'english': {'topics': 12, 'lessons': 157, 'practice': 314},
}

LETTERS = ('A', 'B', 'C', 'D')
SUPERSCRIPT = str.maketrans('0123456789', '⁰¹²³⁴⁵⁶⁷⁸⁹')
CARET_RE = re.compile(r'\^(\d)')
ARABIC_STEP_RE = re.compile(r'^Arabic\s*:\s*(.+)$', re.IGNORECASE)


# ---------------------------------------------------------------- xlsx reading

def _column_index(ref):
    """'BC12' -> 54. Cells carry their column letter, and empty cells are omitted
    from the XML entirely, so rows must be keyed by letter rather than position."""
    n = 0
    for ch in ref:
        if not ch.isalpha():
            break
        n = n * 26 + (ord(ch.upper()) - 64)
    return n - 1


def _shared_strings(zf):
    if 'xl/sharedStrings.xml' not in zf.namelist():
        return []
    root = ET.fromstring(zf.read('xl/sharedStrings.xml'))
    return [''.join(t.text or '' for t in si.iter(NS + 't')) for si in root.findall(NS + 'si')]


def _cell_text(cell, shared):
    kind = cell.get('t')
    if kind == 'inlineStr':
        return ''.join(t.text or '' for t in cell.iter(NS + 't')).strip()
    node = cell.find(NS + 'v')
    if node is None or node.text is None:
        return ''
    if kind == 's':
        try:
            return shared[int(node.text)].strip()
        except (ValueError, IndexError):
            return ''
    return node.text.strip()


def read_workbook(path, required):
    """Return a list of dicts, one per data row, keyed by the header names."""
    if not os.path.exists(path):
        raise SystemExit('missing workbook: %s' % path)
    with zipfile.ZipFile(path) as zf:
        shared = _shared_strings(zf)
        sheets = sorted(n for n in zf.namelist() if re.match(r'xl/worksheets/sheet\d+\.xml$', n))
        if not sheets:
            raise SystemExit('no worksheet in %s' % path)
        root = ET.fromstring(zf.read(sheets[0]))

    rows = []
    for row in root.findall('.//' + NS + 'row'):
        cells = {}
        for cell in row.findall(NS + 'c'):
            ref = cell.get('r') or ''
            cells[_column_index(ref)] = _cell_text(cell, shared)
        rows.append(cells)

    if not rows:
        raise SystemExit('no rows in %s' % path)

    header = {}
    for idx, name in rows[0].items():
        if name:
            header[name.strip().lower()] = idx

    missing = [c for c in required if c not in header]
    if missing:
        raise SystemExit('%s is missing column(s): %s' % (os.path.basename(path), ', '.join(missing)))

    out = []
    for cells in rows[1:]:
        record = {name: cells.get(idx, '') for name, idx in header.items()}
        if any(v for v in record.values()):
            out.append(record)
    return out


# ------------------------------------------------------------------- cleaning

def tidy(value):
    """Collapse whitespace and convert caret exponents to the Unicode superscripts
    the rest of the site already uses (x^2 -> x², matching the existing x², 3x⁴)."""
    text = re.sub(r'\s+', ' ', (value or '').strip())
    return CARET_RE.sub(lambda m: m.group(1).translate(SUPERSCRIPT), text)


def split_explanation(value):
    """The workbooks pack several steps into one cell separated by ' | ', and bury
    the Arabic translation among them. Return (steps, arabic)."""
    steps, arabic = [], ''
    for chunk in (value or '').split('|'):
        step = tidy(chunk)
        if not step:
            continue
        found = ARABIC_STEP_RE.match(step)
        if found:
            arabic = found.group(1).strip()
        else:
            steps.append(step)
    return steps, arabic


def answer_letter(raw, options):
    """Accept a literal A-D, otherwise match the answer text against the options."""
    value = (raw or '').strip()
    if value.upper() in LETTERS:
        return value.upper()
    folded = value.casefold()
    for letter, text in zip(LETTERS, options):
        if text.strip().casefold() == folded:
            return letter
    return ''


# -------------------------------------------------------------------- building

def build(subject, source):
    spec = WORKBOOKS[subject]
    topic_rows = read_workbook(os.path.join(source, spec['topics'][0]), spec['topics'][1])
    lesson_rows = read_workbook(os.path.join(source, spec['lessons'][0]), spec['lessons'][1])
    question_rows = read_workbook(os.path.join(source, spec['questions'][0]), spec['questions'][1])

    topics = []
    for row in topic_rows:
        topic_id = tidy(row.get('topic_id'))
        if not topic_id:
            continue
        try:
            order = int(float(row.get('order') or 0))
        except ValueError:
            order = 0
        topics.append({'id': topic_id, 'name': tidy(row.get('topic_name')), 'order': order})
    topics.sort(key=lambda t: (t['order'], t['name']))

    by_topic = {t['id'].casefold(): t['id'] for t in topics}

    # A lesson's key is what its practice questions are matched on. For Math that is
    # the lesson title (154 distinct, ~2 questions each). For English the workbook's
    # lesson_title is really the *topic* name -- only 12 distinct values -- so keying
    # on it makes every rule in a topic show the same two questions. Key on the rule.
    lessons, seen_keys = [], {}
    duplicates = 0
    for index, row in enumerate(lesson_rows, start=1):
        title = tidy(row.get('lesson_title'))
        rule = tidy(row.get('rule_title'))
        key = (rule if subject == 'english' else title)
        # The math workbook repeats a few lesson rows verbatim. Keeping both would
        # leave a second, identical lesson showing "0 Q", because practice matches on
        # this same key and attaches to the first one.
        if key.casefold() in seen_keys:
            duplicates += 1
            continue
        steps, arabic = split_explanation(row.get('explanation'))
        topic_id = tidy(row.get('topic_id'))
        lesson = {
            'id': '%s-lesson-%d' % (subject, index),
            'topicId': by_topic.get(topic_id.casefold(), topic_id),
            'key': key,
            'title': rule or title,
            'topicTitle': title,
            'domain': tidy(row.get('domain')),
            'formula': tidy(row.get('formula')),
            'example': tidy(row.get('example')),
            'explanation': steps,
            'tip': tidy(row.get('tip')),
            'arabic': tidy(row.get('arabic')) or arabic,
            'difficulty': tidy(row.get('difficulty')),
        }
        lessons.append(lesson)
        seen_keys[key.casefold()] = lesson
    if duplicates:
        print('%-8s merged %d duplicate lesson row(s)' % (subject, duplicates))

    practice = []
    for index, row in enumerate(question_rows, start=1):
        options = [tidy(row.get('option_' + letter.lower())) for letter in LETTERS]
        if not all(options):
            continue
        answer = answer_letter(row.get('correct_answer'), options)
        if not answer:
            raise SystemExit('%s question %d: cannot resolve correct_answer %r'
                             % (subject, index, row.get('correct_answer')))
        title = tidy(row.get('lesson_title'))
        rule = tidy(row.get('rule_title'))
        key = (rule if subject == 'english' else title)
        lesson = seen_keys.get(key.casefold())
        steps, _ = split_explanation(row.get('explanation'))
        practice.append({
            'id': '%s-practice-%d' % (subject, index),
            'lessonKey': key,
            'lessonId': lesson['id'] if lesson else '',
            'topicId': lesson['topicId'] if lesson else tidy(row.get('topic_id')),
            'domain': tidy(row.get('domain')),
            'difficulty': tidy(row.get('difficulty')),
            'question': tidy(row.get('question')),
            'choices': [{'id': letter, 'text': text} for letter, text in zip(LETTERS, options)],
            'answer': answer,
            'explanation': steps,
        })

    return {'subject': subject, 'topics': topics, 'lessons': lessons, 'practice': practice}


def serialize(payload):
    return json.dumps(payload, ensure_ascii=False, indent=1, sort_keys=True) + '\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', default=DEFAULT_SOURCE, help='folder holding the .xlsx workbooks')
    parser.add_argument('--check', action='store_true', help='fail if the committed JSON is stale')
    args = parser.parse_args()

    stale = []
    for subject in sorted(WORKBOOKS):
        payload = build(subject, args.source)
        counts = {k: len(payload[k]) for k in ('topics', 'lessons', 'practice')}
        expected = EXPECTED[subject]
        flag = '' if counts == expected else '  <-- expected %s' % expected
        print('%-8s topics %-4d lessons %-5d practice %-5d%s'
              % (subject, counts['topics'], counts['lessons'], counts['practice'], flag))

        unmatched = sum(1 for q in payload['practice'] if not q['lessonId'])
        if unmatched:
            print('%-8s %d practice question(s) matched no lesson' % ('', unmatched))

        text = serialize(payload)
        target = os.path.join(OUT_DIR, subject + '.json')
        if args.check:
            current = ''
            if os.path.exists(target):
                with open(target, encoding='utf-8') as handle:
                    current = handle.read()
            if current != text:
                stale.append(target)
            continue

        if not os.path.isdir(OUT_DIR):
            os.makedirs(OUT_DIR)
        with open(target, 'w', encoding='utf-8', newline='\n') as handle:
            handle.write(text)
        print('%-8s wrote %s (%.0f KB)' % ('', target, len(text.encode('utf-8')) / 1024.0))

    if stale:
        print('\nstale, re-run without --check: %s' % ', '.join(stale))
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
