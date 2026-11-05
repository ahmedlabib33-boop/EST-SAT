# -*- coding: utf-8 -*-
"""Rebuild the practice questions in backend/content/*.json.

The imported banks were mostly placeholders: 586 of the 622 questions came from
four templates, and every English question offered the lesson's own example
sentence against the same three wrong sentences, so a student could score well
without reading the question. This script throws those away and writes the
hand-written questions in items_math.py and items_english.py in their place.

Run it after scripts/import_content.py, which regenerates the banks from the
source app:

    python scripts/import_content.py
    python scripts/build_practice.py

Questions that were already real keep their ids, so saved mistakes still point
at the same question. New questions start at 400 to stay clear of them.
"""

import io
import json
import os
import random
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from items_english import EXTRA as ENGLISH_EXTRA, ITEMS as ENGLISH_ITEMS  # noqa: E402
from items_math import EXTRA as MATH_EXTRA, ITEMS as MATH_ITEMS  # noqa: E402
from items_physics import EXTRA as PHYSICS_EXTRA, LESSONS as PHYSICS_LESSONS, TOPICS as PHYSICS_TOPICS  # noqa: E402

NEW_ID_FROM = 400
# A lesson can carry more than one question: the first is 400 + the lesson number, the
# second 800 + it, and so on. Fixed ids mean a saved mistake always finds its question.
ID_BASES = (400, 800, 1200)
LETTERS = 'ABCD'
# The four generated templates, in the order they appeared in the banks.
PLACEHOLDERS = (
    'Which formula or statement correctly represents',
    'An EST-style problem requires',
    'Which choice best shows the rule',
    'In an EST question about',
)


def is_placeholder(question):
    return question.get('question', '').startswith(PLACEHOLDERS)


def lesson_number(lesson_id):
    return int(lesson_id.rsplit('-', 1)[-1])


def build(subject, items):
    path = os.path.join(ROOT, 'backend', 'content', subject + '.json')
    with io.open(path, encoding='utf-8') as handle:
        payload = json.load(handle)

    def written_here(question):
        return int(question['id'].rsplit('-', 1)[-1]) >= NEW_ID_FROM

    lessons = {lesson_number(l['id']): l for l in payload['lessons']}
    # Placeholders go; so do the questions a previous run wrote, which this run replaces.
    kept = [q for q in payload.get('practice', []) if not is_placeholder(q) and not written_here(q)]
    dropped = len([q for q in payload.get('practice', []) if is_placeholder(q)])

    missing = sorted(n for n in items if n not in lessons)
    if missing:
        sys.exit('%s: questions written for lessons that do not exist: %s' % (subject, missing))

    written = []
    for number in sorted(items):
        entries = items[number]
        if entries and isinstance(entries[0], str):
            entries = [entries]
        if len(entries) > len(ID_BASES):
            sys.exit('%s: lesson %d has more questions than there are id slots' % (subject, number))
        lesson = lessons[number]
        for slot, entry in enumerate(entries):
            stem, options, why = entry
            question_id = '%s-practice-%d' % (subject, ID_BASES[slot] + number)
            # Shuffled from the id, so the answer is in a different place for each
            # question but never moves between rebuilds.
            order = list(options)
            random.Random(question_id).shuffle(order)
            written.append({
                'id': question_id,
                'lessonId': lesson['id'],
                'lessonKey': lesson.get('key', ''),
                'topicId': lesson.get('topicId', ''),
                'domain': lesson.get('domain', ''),
                'difficulty': lesson.get('difficulty', '') or 'Medium',
                'question': stem,
                'choices': [{'id': LETTERS[i], 'text': text} for i, text in enumerate(order)],
                'answer': LETTERS[order.index(options[0])],
                'explanation': [why],
            })

    practice = kept + written
    practice.sort(key=lambda q: (lesson_number(q['lessonId']), int(q['id'].rsplit('-', 1)[-1])))
    payload['practice'] = practice
    with io.open(path, 'w', encoding='utf-8', newline='\n') as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=1, sort_keys=True)
        handle.write(u'\n')
    return payload, dropped, len(kept), len(written)


def check(subject, payload):
    """Nothing reaches a student without passing all of this."""
    seen = set()
    lessons = {l['id'] for l in payload['lessons']}
    for q in payload['practice']:
        where = '%s %s' % (subject, q['id'])
        assert q['id'] not in seen, '%s: duplicate id' % where
        seen.add(q['id'])
        assert q['lessonId'] in lessons, '%s: unknown lesson %s' % (where, q['lessonId'])
        assert not is_placeholder(q), '%s: still a placeholder' % where
        texts = [c['text'].strip() for c in q['choices']]
        assert len(texts) == 4, '%s: %d choices' % (where, len(texts))
        assert len(set(texts)) == 4, '%s: two choices say the same thing' % where
        assert all(texts), '%s: an empty choice' % where
        assert q['answer'] in LETTERS, '%s: answer %r' % (where, q['answer'])
        assert [c['id'] for c in q['choices']] == list(LETTERS), '%s: choice ids' % where
        assert q.get('question', '').strip(), '%s: empty question' % where
        assert q.get('explanation'), '%s: no explanation' % where
    with_questions = {q['lessonId'] for q in payload['practice']}
    empty = sorted(lessons - with_questions, key=lesson_number)
    return empty


def build_physics():
    """Physics has no source workbook, so the whole subject is written here."""
    topics = [{'id': tid, 'name': name} for tid, name in PHYSICS_TOPICS]
    known = {t['id'] for t in topics}
    lessons, items = [], {}
    for index, row in enumerate(PHYSICS_LESSONS, start=1):
        topic, title, formula, steps, example, tip, arabic, difficulty, stem, options, why = row
        if topic not in known:
            sys.exit('physics: lesson %r has unknown topic %r' % (title, topic))
        lessons.append({
            'id': 'physics-lesson-%d' % index,
            'topicId': topic,
            'topicTitle': title,
            'title': title,
            'key': title,
            'formula': formula,
            'explanation': list(steps),
            'example': example,
            'tip': tip,
            'arabic': arabic,
            'domain': dict(PHYSICS_TOPICS)[topic],
            'difficulty': difficulty,
        })
        items[index] = [(stem, options, why)]
        if title in PHYSICS_EXTRA:
            items[index].append(PHYSICS_EXTRA[title])
    payload = {'subject': 'physics', 'topics': topics, 'lessons': lessons, 'practice': []}
    path = os.path.join(ROOT, 'backend', 'content', 'physics.json')
    with io.open(path, 'w', encoding='utf-8', newline='\n') as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=1, sort_keys=True)
        handle.write(u'\n')
    return items


def merge(items, extra):
    """One lesson, its first question and any second one, in order."""
    stray = sorted(set(extra) - set(items))
    if stray:
        sys.exit('second questions written for lessons with no first question: %s' % stray)
    out = {}
    for number, first in items.items():
        out[number] = [first] + ([extra[number]] if number in extra else [])
    return out


def main():
    stray = _unused_titles()
    if stray:
        sys.exit('physics: extra questions for lessons that do not exist: %s' % stray)
    physics_items = build_physics()
    total = 0
    banks = (('math', merge(MATH_ITEMS, MATH_EXTRA)),
             ('english', merge(ENGLISH_ITEMS, ENGLISH_EXTRA)),
             ('physics', physics_items))
    for subject, items in banks:
        payload, dropped, kept, written = build(subject, items)
        empty = check(subject, payload)
        total += len(payload['practice'])
        print('%-8s dropped %3d placeholders, kept %3d real, wrote %3d new -> %3d questions'
              % (subject, dropped, kept, written, len(payload['practice'])))
        if empty:
            print('         lessons with no question yet: %d (%s)' % (len(empty), ', '.join(empty[:5])))
    print('%d practice questions in all' % total)


def _unused_titles():
    titles = {row[1] for row in PHYSICS_LESSONS}
    return sorted(set(PHYSICS_EXTRA) - titles)


if __name__ == '__main__':
    main()
