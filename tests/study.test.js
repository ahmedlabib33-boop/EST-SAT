// The study engine runs in the browser, but its logic is plain data in and out. Run with: npm test
const test = require('node:test');
const assert = require('node:assert/strict');
const S = require('../public/assets/study.js');

const DAY = '2026-11-05'; // a Thursday
const CATALOG = {
  math: {
    topics: [{ id: 'MATH-01', name: 'Algebra' }, { id: 'MATH-02', name: 'Geometry' }],
    lessons: [{ id: 'math-lesson-1', topicId: 'MATH-01' }, { id: 'math-lesson-2', topicId: 'MATH-01' }, { id: 'math-lesson-3', topicId: 'MATH-02' }],
  },
  english: { topics: [{ id: 'eng-01', name: 'Verbs' }], lessons: [{ id: 'english-lesson-1', topicId: 'eng-01' }] },
};

test('normalize fills every field and keeps what is already there', () => {
  const s = S.normalize({ exam: '2027-01-01', xp: 40, unknown: 'kept' });
  assert.equal(s.exam, '2027-01-01');
  assert.equal(s.xp, 40);
  assert.equal(s.unknown, 'kept');
  assert.deepEqual(s.mistakes, []);
  assert.deepEqual(s.freezes, { usedDays: [], earnedOn: [] });
  assert.deepEqual(S.normalize(null).stats, { answered: 0, correct: 0, time: 0 });
});

test('a wrong answer is saved for review and comes back after one day', () => {
  const s = S.normalize({});
  S.recordAnswer(s, { id: 'math-practice-1', subject: 'math', topic: 'MATH-01', correct: false, seconds: 30 }, DAY);
  assert.equal(s.stats.answered, 1);
  assert.equal(s.stats.correct, 0);
  assert.equal(s.xp, S.XP.wrong);
  assert.deepEqual(s.topics['math|MATH-01'], [1, 0]);
  assert.equal(S.reviewSummary(s, DAY).total, 1);
  assert.equal(S.reviewSummary(s, DAY).due, 0);
  assert.equal(S.reviewSummary(s, S.addDays(DAY, 1)).due, 1);
});

test('questions without an id still count, but cannot be reviewed', () => {
  const s = S.normalize({});
  S.recordAnswer(s, { subject: 'physics', topic: 'Mechanics', correct: false }, DAY);
  assert.equal(s.mistakes.length, 0);
  assert.deepEqual(s.topics['physics|Mechanics'], [1, 0]);
});

test('reviews step out over 1, 3, 7 and 14 days, then the mistake is mastered', () => {
  const s = S.normalize({});
  const item = { id: 'english-practice-9', subject: 'english', topic: 'eng-01' };
  S.recordAnswer(s, Object.assign({ correct: false }, item), DAY);
  let day = S.addDays(DAY, 1);
  const gaps = [3, 7, 14];
  gaps.forEach((gap) => {
    S.recordReview(s, Object.assign({ correct: true }, item), day);
    const st = s.reviews[item.id];
    assert.equal(st.due, S.addDays(day, gap));
    day = st.due;
  });
  S.recordReview(s, Object.assign({ correct: true }, item), day);
  assert.equal(s.reviews[item.id].stage, S.MASTERED_STAGE);
  assert.equal(s.reviews[item.id].due, '');
  assert.equal(S.reviewSummary(s, day).mastered, 1);
  assert.equal(S.reviewQueue(s, S.addDays(day, 100)).length, 0);
  assert.equal(S.reviewLabel(s.reviews[item.id], day), 'Mastered');
});

test('getting a review wrong sends it back to the start', () => {
  const next = S.scheduleReview({ stage: 3, due: DAY }, false, DAY);
  assert.deepEqual(next, { stage: 0, due: S.addDays(DAY, 1), last: DAY });
});

test('a fresh wrong answer replaces the old copy and restarts its schedule', () => {
  const s = S.normalize({});
  const wrong = { id: 'math-practice-2', subject: 'math', topic: 'MATH-01', correct: false };
  S.recordAnswer(s, wrong, DAY);
  S.recordReview(s, { id: wrong.id, correct: true }, S.addDays(DAY, 1));
  S.recordAnswer(s, wrong, S.addDays(DAY, 2));
  assert.equal(s.mistakes.length, 1);
  assert.equal(s.mistakes[0].date, S.addDays(DAY, 2));
  assert.equal(s.reviews[wrong.id], undefined);
});

test('the mistake list is capped and forgets the schedule of what falls off', () => {
  const s = S.normalize({});
  for (let i = 0; i < S.MAX_MISTAKES + 5; i += 1) {
    S.recordAnswer(s, { id: 'math-practice-' + i, correct: false }, DAY);
    s.reviews['math-practice-' + i] = { stage: 1, due: DAY, last: DAY };
  }
  assert.equal(s.mistakes.length, S.MAX_MISTAKES);
  assert.equal(s.mistakes[0].id, 'math-practice-5');
  assert.equal(s.reviews['math-practice-0'], undefined);
});

test('a lesson only counts the first time', () => {
  const s = S.normalize({});
  assert.equal(S.completeLesson(s, 'math-lesson-1', DAY), true);
  assert.equal(S.completeLesson(s, 'math-lesson-1', DAY), false);
  assert.equal(s.xp, S.XP.lesson);
  assert.equal(s.lessons.length, 1);
});

test('an exam counts blanks as wrong, but only answered questions in accuracy', () => {
  const s = S.normalize({});
  S.recordExam(s, {
    subject: 'mixed', score: 1, total: 3, percent: 33, seconds: 120,
    results: [
      { id: 'math-practice-1', subject: 'math', topic: 'MATH-01', correct: true, answered: true },
      { id: 'math-practice-2', subject: 'math', topic: 'MATH-01', correct: false, answered: true },
      { id: 'english-practice-1', subject: 'english', topic: 'eng-01', correct: false, answered: false },
    ],
  }, DAY);
  assert.equal(s.stats.answered, 2);
  assert.equal(s.stats.correct, 1);
  assert.equal(s.mistakes.length, 2);
  assert.deepEqual(s.topics['english|eng-01'], [1, 0]);
  assert.equal(s.attempts[0].percent, 33);
  assert.equal(s.xp, S.XP.exam + 33);
  assert.equal(s.week.exams, 1);
  assert.equal(S.minutesStudied(s, 1, DAY), 2);
});

test('levels step up at the published thresholds', () => {
  assert.equal(S.levelFor(0).level, 1);
  assert.equal(S.levelFor(199).level, 1);
  assert.equal(S.levelFor(200).level, 2);
  assert.equal(S.levelFor(200).rank, S.RANKS[1]);
  assert.equal(S.levelFor(350).progress, 0.5);
  assert.equal(S.levelFor(999999).level, S.LEVELS.length);
});

test('streaks count back from today, or from yesterday before today is studied', () => {
  const days = {};
  days[DAY] = 2; days[S.addDays(DAY, -1)] = 1; days[S.addDays(DAY, -2)] = 1; days[S.addDays(DAY, -5)] = 1;
  const st = S.streak({ days }, DAY);
  assert.equal(st.current, 3);
  assert.equal(st.best, 3);
  assert.equal(st.studiedToday, true);
  assert.equal(S.streak({ days }, S.addDays(DAY, 1)).current, 3);
  assert.equal(S.streak({ days }, S.addDays(DAY, 2)).current, 0);
});

test('a protector covers one missed day, and is spent only once', () => {
  const days = {};
  days[S.addDays(DAY, -2)] = 1; // yesterday was missed
  const s = S.normalize({ days });
  assert.equal(S.freezesLeft(s), 1);
  assert.equal(S.updateFreezes(s, DAY), true);
  assert.deepEqual(s.freezes.usedDays, [S.addDays(DAY, -1)]);
  assert.equal(S.freezesLeft(s), 0);
  assert.equal(S.updateFreezes(s, DAY), false);
  assert.equal(S.streak(s, DAY).current, 2);
});

test('a gap bigger than the protectors left does not spend any', () => {
  const days = {};
  days[S.addDays(DAY, -4)] = 1;
  const s = S.normalize({ days });
  assert.equal(S.updateFreezes(s, DAY), false);
  assert.equal(S.freezesLeft(s), 1);
});

test('seven days in a row earns a protector, up to two saved', () => {
  const days = {};
  for (let i = 0; i < 7; i += 1) days[S.addDays(DAY, -i)] = 1;
  const s = S.normalize({ days });
  assert.equal(S.updateFreezes(s, DAY), true);
  assert.equal(S.freezesLeft(s), 2);
  assert.equal(S.updateFreezes(s, DAY), false);
  s.freezes.earnedOn.push('2026-01-01');
  assert.equal(S.freezesLeft(s), S.MAX_FREEZES);
});

test('topic rows combine lessons and accuracy, and include physics with no catalog', () => {
  const s = S.normalize({ lessons: ['math-lesson-1', 'math-lesson-2'], topics: { 'math|MATH-01': [10, 10], 'physics|Mechanics': [4, 2] } });
  const rows = S.topicRows(s, CATALOG);
  const algebra = rows.find((r) => r.key === 'math|MATH-01');
  assert.equal(algebra.lessonsDone, 2);
  assert.equal(algebra.score, 100);
  assert.equal(algebra.level, 'mastered');
  assert.equal(rows.find((r) => r.key === 'math|MATH-02').level, 'new');
  const physics = rows.find((r) => r.subject === 'physics');
  assert.equal(physics.name, 'Mechanics');
  assert.equal(physics.score, 50);
});

test('top gains put a weak big topic ahead of a strong one', () => {
  const s = S.normalize({ topics: { 'math|MATH-01': [10, 2], 'math|MATH-02': [10, 9] } });
  assert.equal(S.topGains(s, CATALOG, 1)[0].key, 'math|MATH-01');
});

test('readiness needs real data, and prefers exams over practice', () => {
  assert.equal(S.readiness({ stats: { answered: 5, correct: 5 } }), null);
  const practice = S.readiness({ stats: { answered: 20, correct: 10 } });
  assert.equal(practice.percent, 50);
  assert.equal(practice.basis, 'practice');
  assert.equal(practice.confidence, 'low');
  const exams = S.readiness({ stats: { answered: 20, correct: 10 }, attempts: [{ percent: 90 }, { percent: 80 }, { percent: 70 }, { percent: 10 }] });
  assert.equal(exams.percent, 80);
  assert.equal(exams.basis, 'exams');
  assert.equal(exams.confidence, 'high');
});

test('the daily plan serves due reviews first and fills up with fresh questions', () => {
  const s = S.normalize({});
  S.recordAnswer(s, { id: 'math-practice-1', correct: false }, DAY);
  const none = S.dailyPlan(s, CATALOG, DAY, 8);
  assert.equal(none.due.length, 0);
  assert.equal(none.freshCount, 8);
  const next = S.dailyPlan(s, CATALOG, S.addDays(DAY, 1), 8);
  assert.equal(next.due[0].id, 'math-practice-1');
  assert.equal(next.freshCount, 7);
  assert.ok(next.weak.every((r) => r.subject !== 'physics'));
});

test('badges follow real milestones', () => {
  const earned = (state) => S.badges(state, CATALOG, DAY).filter((b) => b.earned).map((b) => b.id);
  assert.deepEqual(earned({}), []);
  assert.ok(earned({ lessons: ['math-lesson-1'] }).includes('first-step'));
  assert.ok(earned({ stats: { answered: 100, correct: 90 } }).includes('sharp'));
  assert.ok(!earned({ stats: { answered: 10, correct: 10 } }).includes('sharp'));
  assert.ok(earned({ attempts: [{ percent: 85 }] }).includes('top-score'));
});

test('the weekly challenge resets on Monday', () => {
  const s = S.normalize({});
  S.completeLesson(s, 'math-lesson-1', DAY);
  const thisWeek = S.weeklyChallenge(s, DAY);
  assert.equal(thisWeek.start, '2026-11-02');
  assert.equal(thisWeek.end, '2026-11-08');
  const lessons = thisWeek.goals.find((g) => g.key === 'lessons');
  if (lessons) assert.equal(lessons.done, 1);
  const nextWeek = S.weeklyChallenge(s, '2026-11-09');
  nextWeek.goals.forEach((g) => assert.equal(g.done, 0));
});

test('goals unlock once, when the student reaches them', () => {
  const s = S.normalize({ xp: 250, lessons: ['math-lesson-1'], goals: [
    { id: 'g-1', kind: 'level', target: '2' },
    { id: 'g-2', kind: 'level', target: '5' },
    { id: 'g-3', kind: 'topic', target: 'math|MATH-01' },
  ] });
  assert.deepEqual(S.unlockGoals(s, CATALOG, DAY).map((g) => g.id), ['g-1']);
  assert.deepEqual(S.unlockGoals(s, CATALOG, DAY), []);
  S.completeLesson(s, 'math-lesson-2', DAY);
  assert.deepEqual(S.unlockGoals(s, CATALOG, DAY).map((g) => g.id), ['g-3']);
});

test('assignments finish when the lesson or a later exam is done', () => {
  const s = S.normalize({ lessons: ['math-lesson-1'], attempts: [{ date: '2026-11-01', subject: 'math', percent: 50 }] });
  assert.equal(S.assignmentDone({ kind: 'lesson', target: 'math-lesson-1' }, s), true);
  assert.equal(S.assignmentDone({ kind: 'lesson', target: 'math-lesson-2' }, s), false);
  assert.equal(S.assignmentDone({ kind: 'exam', target: 'math-20', created: DAY }, s), false);
  assert.equal(S.assignmentDone({ kind: 'exam', target: 'math-20', created: '2026-10-30' }, s), true);
  assert.equal(S.assignmentDone({ kind: 'exam', target: 'english-20', created: '2026-10-30' }, s), false);
});

test('an exam taken earlier on the day it was assigned does not count', () => {
  const s = S.normalize({ attempts: [{ date: DAY, subject: 'math', percent: 50 }] });
  const assignment = { kind: 'exam', target: 'math-20', created: DAY, sameDay: 1 };
  assert.equal(S.assignmentDone(assignment, s), false);
  s.attempts.unshift({ date: DAY, subject: 'math', percent: 70 });
  assert.equal(S.assignmentDone(assignment, s), true);
});

test('reset clears progress but keeps the exam date and music link', () => {
  const s = S.normalize({ exam: '2027-01-01', music: 'https://x', xp: 900, lessons: ['math-lesson-1'] });
  S.reset(s);
  assert.equal(s.exam, '2027-01-01');
  assert.equal(s.music, 'https://x');
  assert.equal(s.xp, 0);
  assert.deepEqual(s.lessons, []);
});

const LESSONS = {
  math: {
    topics: [{ id: 'M1', name: 'Algebra' }],
    lessons: ['Speed Formula', 'Slope Formula', 'Slope Intercept Form', 'Horizontal Line Equation', 'Zero Product Rule', 'Mean', 'Linear Equation', 'Circle Equation', 'Absolute Value Equation', 'Vertical Line Equation', 'Quadratic Standard Form', 'Percent formula', 'Triangle Area']
      .map((title, i) => ({ id: 'm' + i, topicId: 'M1', title }))
  },
  english: {
    topics: [{ id: 'E1', name: 'Verb tenses' }, { id: 'E2', name: 'Vocabulary in context' }, { id: 'E3', name: 'Reading comprehension and writing' }],
    lessons: [['Future time clauses', 'E1'], ['At / on / in time', 'E1'], ['Past perfect', 'E1'], ['Zero article', 'E1'], ['Comma in list', 'E1'], ['Intro comma', 'E1'], ['Comma splice', 'E1'], ['Who / whom', 'E1'], ['The', 'E1'], ['novel', 'E2'], ['factor', 'E2'], ['Purpose', 'E3']]
      .map(([title, topicId], i) => ({ id: 'e' + i, topicId, title }))
  }
};
const titles = (question, reply) => S.relatedLessons(question, reply, LESSONS).picks.map((p) => p.lesson.title);

test('a physics question gets the formula vault, not lessons that share a word with it', () => {
  const reply = 'Use v = v0 + a t. The speed after this time follows the formula, and the future velocity is 24 m/s.';
  const found = S.relatedLessons('A car starts from rest and accelerates at 3 m/s^2 for 8 s. What is its final velocity?', reply, LESSONS);
  assert.equal(found.physics, true);
  assert.deepEqual(found.picks, []);
});

test('related lessons come from the words in the question', () => {
  const picks = titles('Why is the slope of a horizontal line zero?', 'A horizontal line has zero slope because rise is zero.');
  assert.ok(picks.includes('Slope Formula'));
  assert.ok(picks.includes('Horizontal Line Equation'));
  assert.ok(!picks.includes('Zero Product Rule'));
  assert.ok(!picks.includes('Zero article'));
});

test('words in the answer alone do not bring in unrelated lessons', () => {
  const picks = titles('How do I work out 15 + 27?', 'Add the tens, then the ones. The time you save follows a simple formula, and the future is bright.');
  assert.deepEqual(picks, []);
});

test('a grammar question stays in English', () => {
  assert.deepEqual(titles('What is the past perfect tense?', 'The past perfect uses had.'), ['Past perfect']);
  const commas = titles('When do I use a comma?', 'Commas separate items.');
  assert.equal(commas.length, 3);
  assert.ok(commas.every((t) => /comma/i.test(t)));
});

test('everyday words need the question to be about the word', () => {
  assert.deepEqual(titles('What does novel mean?', 'New and original.'), ['novel']);
  assert.deepEqual(titles('Which choice best shows the rule "novel"?', 'It means new.'), ['novel']);
  assert.deepEqual(titles('I read a novel for school. What is a good summary?', 'A summary is short.'), []);
  assert.ok(!titles('Solve this: factor x^2 - 5x + 6 = 0', 'The roots are 2 and 3.').includes('factor'));
});

test('"what does this mean" does not link to the Mean lesson, but the mean of numbers does', () => {
  assert.ok(!titles('What does this mean?', 'It means the answer is 4.').includes('Mean'));
  assert.ok(titles('How do I find the mean of 3, 5 and 7?', 'Add them and divide by 3.').includes('Mean'));
});

test('small-word lessons need the words named', () => {
  assert.deepEqual(titles('Should I say who or whom here?', 'Use whom after a preposition.'), ['Who / whom']);
  assert.deepEqual(titles('When do I use "the"?', 'For something specific.'), ['The']);
  assert.ok(!titles('What is the capital of France?', 'Paris.').includes('The'));
});

test('a photo with no typed question matches only full titles from the answer', () => {
  const picks = titles('', 'This is a quadratic in standard form. The slope is not needed.');
  assert.deepEqual(picks, ['Quadratic Standard Form']);
});

test('a question in Arabic is matched through a title named in the answer', () => {
  assert.deepEqual(titles('ما هو الميل؟', 'The slope formula is rise over run.'), ['Slope Formula']);
});

test('nothing related means nothing is shown', () => {
  assert.deepEqual(titles('Hello, can you help me?', 'Of course!'), []);
  assert.deepEqual(S.relatedLessons('hello', 'hi', null).picks, []);
});

test('bold marks in an AI reply become bold text, with no asterisks left', () => {
  const blocks = S.replyBlocks('**Rule:** The area is half base times height.');
  assert.deepEqual(blocks, [{ type: 'para', parts: [{ text: 'Rule:', bold: true }, { text: ' The area is half base times height.' }] }]);
  assert.equal(S.replyPlain('**What you need to know:**  \nUse **v = u + at**.'), 'What you need to know:\nUse v = u + at.');
});

test('an unfinished bold mark never shows', () => {
  assert.equal(S.replyPlain('**Rule: add the numbers'), 'Rule: add the numbers');
});

test('lists and headings are recognised, and a numbered list keeps its numbers', () => {
  const blocks = S.replyBlocks('## Worked example\n1. Find v0\n   - v0 = 0 m/s\n2. Plug in\n\nDone.');
  assert.deepEqual(blocks.map((b) => b.type), ['heading', 'list', 'list', 'list', 'para']);
  assert.equal(blocks[1].ordered, true);
  assert.equal(blocks[2].ordered, false);
  assert.equal(blocks[3].start, 2);
  assert.equal(S.replyBlocks('- one\n* two\n• three')[0].items.length, 3);
});

test('maths and fill-in-the-blank questions are left alone', () => {
  ['3*4*5 = 60', 'x * y * z', '2*3 + 4*5', 'She ____ to school and ____ home.', '3.14 is close to pi', 'a_1 + a_2'].forEach((text) => {
    assert.equal(S.replyPlain(text), text);
  });
});

test('single stars and backticks are understood', () => {
  assert.deepEqual(S.replyInline('Use *past* tense and `had`.'), [
    { text: 'Use ' }, { text: 'past', italic: true }, { text: ' tense and ' }, { text: 'had', code: true }, { text: '.' }
  ]);
});

test('HTML in a reply stays as text for the page to draw', () => {
  const text = '<img src=x onerror=alert(1)> **<script>alert(1)</script>**';
  assert.equal(S.replyPlain(text), '<img src=x onerror=alert(1)> <script>alert(1)</script>');
});

test('Arabic replies and empty replies are safe', () => {
  assert.equal(S.replyPlain('**القاعدة:** اجمع الأرقام'), 'القاعدة: اجمع الأرقام');
  assert.deepEqual(S.replyBlocks(''), []);
  assert.deepEqual(S.replyBlocks(null), []);
});
