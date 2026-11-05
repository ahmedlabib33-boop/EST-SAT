/* The study engine: spaced review, XP, streaks, badges, the daily plan and progress maths.
   Everything works on the plain progress object that auth.js saves and syncs, so the logic can be
   unit-tested (tests/study.test.js). The record* functions change the object they are given. */
(function (root, factory) {
  var api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.EstSatStudy = api;
}(typeof self !== 'undefined' ? self : this, function () {
  'use strict';

  var REVIEW_STEPS = [1, 3, 7, 14];
  var MASTERED_STAGE = REVIEW_STEPS.length;
  var MAX_MISTAKES = 100;
  var MAX_ATTEMPTS = 30;
  var MAX_FREEZES = 2;
  var LEVELS = [0, 200, 500, 900, 1400, 2000, 2700, 3500, 4400, 5400, 6500, 7700];
  var RANKS = ['Rookie', 'Warm-up', 'Steady Starter', 'Question Hunter', 'Formula Friend', 'Grammar Guard',
    'Topic Tamer', 'Mock Ready', 'Score Chaser', 'Exam Hunter', 'Top Scorer', 'EST · SAT Legend'];
  var XP = { lesson: 50, right: 10, wrong: 3, reviewRight: 15, reviewWrong: 5, exam: 100 };
  var CHALLENGES = [
    { name: 'Foundation week', goals: { lessons: 5, reviews: 10, exams: 1 } },
    { name: 'Practice week', goals: { lessons: 4, practice: 30 } },
    { name: 'Exam week', goals: { reviews: 15, exams: 2 } },
    { name: 'Momentum week', goals: { lessons: 6, practice: 25, reviews: 10 } }
  ];
  var CHALLENGE_LABELS = { lessons: 'lessons completed', practice: 'practice questions', reviews: 'spaced reviews', exams: 'timed exams' };
  var GOAL_TARGETS = { level: [2, 3, 4, 5, 6, 8, 10], streak: [3, 5, 7, 14, 21, 30], exam: [50, 60, 70, 80, 90] };

  // ---------- Dates (plain local YYYY-MM-DD keys) ----------
  function pad(n) { return (n < 10 ? '0' : '') + n; }
  function dayKey(d) { d = d || new Date(); return d.getFullYear() + '-' + pad(d.getMonth() + 1) + '-' + pad(d.getDate()); }
  function parseKey(k) { var p = k.split('-'); return new Date(+p[0], p[1] - 1, +p[2]); }
  function addDays(k, n) { var d = parseKey(k); return dayKey(new Date(d.getFullYear(), d.getMonth(), d.getDate() + n)); }
  function daysBetween(a, b) {
    var p = a.split('-'), q = b.split('-');
    return Math.round((Date.UTC(+q[0], q[1] - 1, +q[2]) - Date.UTC(+p[0], p[1] - 1, +p[2])) / 86400000);
  }
  function weekStart(k) { return addDays(k, -((parseKey(k).getDay() + 6) % 7)); } // Monday

  // ---------- The progress object ----------
  function emptyWeek(start) { return { start: start || '', lessons: 0, practice: 0, reviews: 0, exams: 0 }; }
  function isList(v) { return Array.isArray(v); }
  function isMap(v) { return !!v && typeof v === 'object' && !Array.isArray(v); }

  function normalize(state) {
    var s = isMap(state) ? state : {};
    if (!isMap(s.stats)) s.stats = {};
    s.stats.answered = s.stats.answered || 0;
    s.stats.correct = s.stats.correct || 0;
    s.stats.time = s.stats.time || 0;
    if (!isMap(s.days)) s.days = {};
    if (!isList(s.chapters)) s.chapters = [];
    if (typeof s.exam !== 'string') s.exam = '';
    if (!isMap(s.mission)) s.mission = { date: '', done: [] };
    if (!isList(s.mistakes)) s.mistakes = [];
    if (!isMap(s.reviews)) s.reviews = {};
    if (!isMap(s.topics)) s.topics = {};
    if (!isList(s.lessons)) s.lessons = [];
    if (!isList(s.attempts)) s.attempts = [];
    if (!isMap(s.time)) s.time = {};
    if (!isMap(s.week)) s.week = emptyWeek();
    if (typeof s.xp !== 'number') s.xp = 0;
    if (!isMap(s.freezes)) s.freezes = {};
    if (!isList(s.freezes.usedDays)) s.freezes.usedDays = [];
    if (!isList(s.freezes.earnedOn)) s.freezes.earnedOn = [];
    if (!isList(s.assignments)) s.assignments = [];
    if (!isList(s.goals)) s.goals = [];
    if (typeof s.music !== 'string') s.music = '';
    return s;
  }

  // Clears study progress but keeps the exam date and music link.
  function reset(state) {
    var s = normalize(state), exam = s.exam, music = s.music;
    Object.keys(s).forEach(function (k) { delete s[k]; });
    normalize(s);
    s.exam = exam;
    s.music = music;
    return s;
  }

  function currentWeek(s, today) {
    var start = weekStart(today);
    if (s.week.start !== start) s.week = emptyWeek(start);
    return s.week;
  }
  function addTopic(s, subject, topic, correct) {
    if (!subject || !topic) return;
    var key = subject + '|' + topic, row = s.topics[key] || [0, 0];
    row[0] += 1;
    if (correct) row[1] += 1;
    s.topics[key] = row;
  }
  function addStudyTime(state, seconds, today) {
    var s = normalize(state);
    today = today || dayKey();
    seconds = Math.max(0, Math.round(seconds || 0));
    s.stats.time += seconds;
    s.time[today] = (s.time[today] || 0) + seconds;
    return s;
  }
  function addMistake(s, id, today) {
    s.mistakes = s.mistakes.filter(function (m) { return m && m.id !== id; });
    s.mistakes.push({ id: id, date: today });
    delete s.reviews[id]; // a fresh wrong answer restarts the schedule
    while (s.mistakes.length > MAX_MISTAKES) delete s.reviews[s.mistakes.shift().id];
  }

  // ---------- Recording activity ----------
  function recordAnswer(state, item, today) {
    var s = normalize(state);
    today = today || dayKey();
    s.stats.answered += 1;
    if (item.correct) s.stats.correct += 1;
    s.days[today] = (s.days[today] || 0) + 1;
    addStudyTime(s, item.seconds, today);
    addTopic(s, item.subject, item.topic, item.correct);
    currentWeek(s, today).practice += 1;
    s.xp += item.correct ? XP.right : XP.wrong;
    if (!item.correct && item.id) addMistake(s, item.id, today);
    return s;
  }

  function reviewState(state, mistake, today) {
    var saved = normalize(state).reviews[mistake.id];
    return saved || { stage: 0, due: addDays(mistake.date || today || dayKey(), REVIEW_STEPS[0]), last: '' };
  }
  function scheduleReview(current, correct, today) {
    if (!correct) return { stage: 0, due: addDays(today, REVIEW_STEPS[0]), last: today };
    var stage = Math.min(MASTERED_STAGE, ((current && current.stage) || 0) + 1);
    return { stage: stage, due: stage >= MASTERED_STAGE ? '' : addDays(today, REVIEW_STEPS[stage]), last: today };
  }
  function recordReview(state, item, today) {
    var s = normalize(state);
    today = today || dayKey();
    var mistake = { id: item.id, date: today };
    s.mistakes.forEach(function (m) { if (m && m.id === item.id) mistake = m; });
    s.reviews[item.id] = scheduleReview(reviewState(s, mistake, today), item.correct, today);
    s.stats.answered += 1;
    if (item.correct) s.stats.correct += 1;
    s.days[today] = (s.days[today] || 0) + 1;
    addStudyTime(s, item.seconds, today);
    addTopic(s, item.subject, item.topic, item.correct);
    currentWeek(s, today).reviews += 1;
    s.xp += item.correct ? XP.reviewRight : XP.reviewWrong;
    return s;
  }
  function completeLesson(state, lessonId, today) {
    var s = normalize(state);
    today = today || dayKey();
    if (s.lessons.indexOf(lessonId) >= 0) return false;
    s.lessons.push(lessonId);
    s.days[today] = (s.days[today] || 0) + 1;
    currentWeek(s, today).lessons += 1;
    s.xp += XP.lesson;
    return true;
  }
  // results: [{ id, subject, topic, correct, answered, seconds }]; a blank counts as wrong and is saved for review.
  function recordExam(state, exam, today) {
    var s = normalize(state);
    today = today || dayKey();
    exam.results.forEach(function (r) {
      if (r.answered) {
        s.stats.answered += 1;
        if (r.correct) s.stats.correct += 1;
        s.days[today] = (s.days[today] || 0) + 1;
      }
      addTopic(s, r.subject, r.topic, r.correct);
      if (!r.correct && r.id) addMistake(s, r.id, today);
    });
    addStudyTime(s, exam.seconds, today);
    s.attempts.unshift({ date: today, subject: exam.subject, score: exam.score, total: exam.total, percent: exam.percent, seconds: exam.seconds });
    s.attempts = s.attempts.slice(0, MAX_ATTEMPTS);
    currentWeek(s, today).exams += 1;
    s.xp += XP.exam + Math.round(exam.percent || 0);
    return s;
  }

  // ---------- Spaced review ----------
  function reviewQueue(state, today) {
    var s = normalize(state);
    today = today || dayKey();
    return s.mistakes.map(function (m) { return { mistake: m, state: reviewState(s, m, today) }; })
      .filter(function (e) { return e.state.stage < MASTERED_STAGE && e.state.due && e.state.due <= today; })
      .sort(function (a, b) { return a.state.due < b.state.due ? -1 : a.state.due > b.state.due ? 1 : 0; });
  }
  function reviewSummary(state, today) {
    var s = normalize(state), due = 0, mastered = 0;
    today = today || dayKey();
    s.mistakes.forEach(function (m) {
      var st = reviewState(s, m, today);
      if (st.stage >= MASTERED_STAGE) mastered += 1;
      else if (st.due && st.due <= today) due += 1;
    });
    return { total: s.mistakes.length, due: due, mastered: mastered };
  }
  function reviewLabel(st, today) {
    today = today || dayKey();
    if (st.stage >= MASTERED_STAGE) return 'Mastered';
    if (!st.due || st.due <= today) return 'Due today';
    var n = daysBetween(today, st.due);
    return 'Next review in ' + n + ' day' + (n === 1 ? '' : 's');
  }

  // ---------- Topics (catalog comes from /api/practice/<subject>/topics) ----------
  function makeRow(subject, id, name, pair, lessons, lessonsDone) {
    var answered = pair[0] || 0, correct = pair[1] || 0;
    var accuracy = answered ? correct / answered : null;
    var confidence = Math.min(1, answered / 4);
    var share = lessons ? Math.min(1, lessonsDone / lessons) : 0;
    var score = Math.round(lessons ? 40 * share + 60 * (accuracy || 0) * confidence : 100 * (accuracy || 0) * confidence);
    var level = score === 0 && !answered ? 'new' : score >= 80 ? 'mastered' : score >= 50 ? 'good' : 'learning';
    return { key: subject + '|' + id, subject: subject, id: id, name: name, answered: answered, correct: correct, accuracy: accuracy, lessons: lessons, lessonsDone: lessonsDone, score: score, level: level };
  }
  function topicRows(state, catalog) {
    var s = normalize(state), rows = [], seen = {}, done = {};
    s.lessons.forEach(function (id) { done[id] = true; });
    ['math', 'english'].forEach(function (subject) {
      var c = catalog && catalog[subject];
      if (!c) return;
      c.topics.forEach(function (t) {
        var key = subject + '|' + t.id;
        var lessons = c.lessons.filter(function (l) { return l.topicId === t.id; });
        var lessonsDone = lessons.filter(function (l) { return done[l.id]; }).length;
        seen[key] = true;
        rows.push(makeRow(subject, t.id, t.name, s.topics[key] || [0, 0], lessons.length, lessonsDone));
      });
    });
    Object.keys(s.topics).forEach(function (key) {
      if (seen[key]) return;
      var cut = key.indexOf('|');
      rows.push(makeRow(key.slice(0, cut), key.slice(cut + 1), key.slice(cut + 1), s.topics[key], 0, 0));
    });
    return rows;
  }
  // The topics that would lift the student most: weak accuracy in the biggest topics.
  function topGains(state, catalog, count) {
    var rows = topicRows(state, catalog), totals = {};
    rows.forEach(function (r) { totals[r.subject] = (totals[r.subject] || 0) + Math.max(1, r.lessons); });
    return rows.map(function (r) {
      var known = r.accuracy === null ? 0.5 : r.accuracy;
      r.priority = (Math.max(1, r.lessons) / totals[r.subject]) * (1 - known) * (r.answered ? 1 : 0.8);
      return r;
    }).sort(function (a, b) { return b.priority - a.priority; }).slice(0, count || 3);
  }

  // An estimate from the student's own work. Never presented as an official SAT or EST score.
  function readiness(state) {
    var s = normalize(state), recent = s.attempts.slice(0, 3), percent, basis;
    if (recent.length) {
      percent = recent.reduce(function (sum, a) { return sum + (a.percent || 0); }, 0) / recent.length;
      basis = 'exams';
    } else if (s.stats.answered >= 12) {
      percent = s.stats.correct / s.stats.answered * 100;
      basis = 'practice';
    } else return null;
    percent = Math.round(percent);
    var band = percent >= 80 ? 'On track for a top score' : percent >= 60 ? 'Solid, keep pushing' : percent >= 40 ? 'Building up' : 'Early days';
    var confidence = basis === 'practice' || s.attempts.length < 2 ? 'low' : s.attempts.length < 4 ? 'medium' : 'high';
    return { percent: percent, band: band, basis: basis, confidence: confidence };
  }

  // Today's session: due reviews first, then fresh questions from the weakest topics.
  function dailyPlan(state, catalog, today, size) {
    size = size || 8;
    var due = reviewQueue(state, today).slice(0, size).map(function (e) { return e.mistake; });
    var weak = topGains(state, catalog, 4).filter(function (r) { return r.subject !== 'physics'; });
    return { due: due, freshCount: Math.max(0, size - due.length), weak: weak };
  }

  // ---------- XP, levels, streaks, badges ----------
  function levelFor(xp) {
    var level = 1;
    LEVELS.forEach(function (floor, i) { if (xp >= floor) level = i + 1; });
    var floor = LEVELS[level - 1];
    var ceiling = level < LEVELS.length ? LEVELS[level] : floor + 1500;
    return { level: level, rank: RANKS[Math.min(level, RANKS.length) - 1], xp: xp, floor: floor, ceiling: ceiling, progress: Math.min(1, (xp - floor) / (ceiling - floor)) };
  }
  function coveredDays(s) {
    var covered = {};
    Object.keys(s.days).forEach(function (k) { if (s.days[k] > 0) covered[k] = true; });
    s.freezes.usedDays.forEach(function (k) { covered[k] = true; });
    return covered;
  }
  function freezesLeft(state) {
    var s = normalize(state);
    return Math.max(0, Math.min(MAX_FREEZES, 1 + s.freezes.earnedOn.length - s.freezes.usedDays.length));
  }
  function streak(state, today) {
    var s = normalize(state), covered = coveredDays(s);
    today = today || dayKey();
    var cursor = covered[today] ? today : addDays(today, -1), current = 0;
    while (covered[cursor]) { current += 1; cursor = addDays(cursor, -1); }
    var best = 0, run = 0, prev = null;
    Object.keys(covered).sort().forEach(function (k) {
      run = prev && daysBetween(prev, k) === 1 ? run + 1 : 1;
      if (run > best) best = run;
      prev = k;
    });
    return { current: current, best: Math.max(best, current), studiedToday: !!s.days[today], freezes: freezesLeft(s) };
  }
  // Spends streak protectors on missed days and earns one for every 7 days in a row. True when anything changed.
  function updateFreezes(state, today) {
    var s = normalize(state), changed = false;
    today = today || dayKey();
    var before = Object.keys(coveredDays(s)).filter(function (k) { return k < today; }).sort();
    var last = before[before.length - 1];
    if (last) {
      var gap = daysBetween(last, today) - 1;
      if (gap > 0 && gap <= freezesLeft(s)) {
        for (var i = 1; i <= gap; i += 1) s.freezes.usedDays.push(addDays(last, i));
        changed = true;
      }
    }
    var st = streak(s, today);
    if (st.studiedToday && st.current > 0 && st.current % 7 === 0 && s.freezes.earnedOn.indexOf(today) < 0 && freezesLeft(s) < MAX_FREEZES) {
      s.freezes.earnedOn.push(today);
      changed = true;
    }
    return changed;
  }
  function badges(state, catalog, today) {
    var s = normalize(state), rows = topicRows(s, catalog), st = streak(s, today), summary = reviewSummary(s, today);
    function subjectRows(subject) { return rows.filter(function (r) { return r.subject === subject; }); }
    function allStarted(subject) { var r = subjectRows(subject); return r.length > 0 && r.every(function (x) { return x.level !== 'new'; }); }
    function allStrong(subject) { var r = subjectRows(subject); return r.length > 0 && r.every(function (x) { return x.level === 'good' || x.level === 'mastered'; }); }
    var accuracy = s.stats.answered ? s.stats.correct / s.stats.answered : 0;
    return [
      { id: 'first-step', name: 'First Step', hint: 'Complete your first lesson', earned: s.lessons.length > 0 },
      { id: 'century', name: 'Century', hint: 'Answer 100 questions', earned: s.stats.answered >= 100 },
      { id: 'sharp', name: 'Sharp Shooter', hint: 'Hold 80% accuracy over 50 or more answers', earned: s.stats.answered >= 50 && accuracy >= 0.8 },
      { id: 'math-map', name: 'Math Explorer', hint: 'Start every Math topic', earned: allStarted('math') },
      { id: 'english-map', name: 'English Explorer', hint: 'Start every English topic', earned: allStarted('english') },
      { id: 'math-strong', name: 'Math Strong', hint: 'Reach Good in every Math topic', earned: allStrong('math') },
      { id: 'english-strong', name: 'English Strong', hint: 'Reach Good in every English topic', earned: allStrong('english') },
      { id: 'mock-warrior', name: 'Mock Warrior', hint: 'Finish 3 timed exams', earned: s.attempts.length >= 3 },
      { id: 'top-score', name: 'Top Score Mindset', hint: 'Score 80% or more in a timed exam', earned: s.attempts.some(function (a) { return a.percent >= 80; }) },
      { id: 'comeback', name: 'Comeback Kid', hint: 'Master 10 old mistakes through spaced review', earned: summary.mastered >= 10 },
      { id: 'week-warrior', name: 'Week Warrior', hint: 'Study 7 days in a row', earned: st.best >= 7 },
      { id: 'deep-focus', name: 'Deep Focus', hint: 'Study for 5 hours in total', earned: s.stats.time >= 5 * 3600 }
    ];
  }

  // ---------- Weekly challenge and study time ----------
  function weeklyChallenge(state, today) {
    var s = normalize(state);
    today = today || dayKey();
    var start = weekStart(today);
    var index = Math.abs(Math.floor(daysBetween('2026-01-05', start) / 7)) % CHALLENGES.length;
    var challenge = CHALLENGES[index];
    var progress = s.week.start === start ? s.week : emptyWeek(start);
    var goals = Object.keys(challenge.goals).map(function (key) {
      var target = challenge.goals[key];
      return { key: key, label: CHALLENGE_LABELS[key], target: target, done: Math.min(target, progress[key] || 0) };
    });
    return { name: challenge.name, start: start, end: addDays(start, 6), goals: goals, complete: goals.every(function (g) { return g.done >= g.target; }) };
  }
  function minutesStudied(state, days, today) {
    var s = normalize(state), seconds = 0;
    today = today || dayKey();
    for (var i = 0; i < days; i += 1) seconds += s.time[addDays(today, -i)] || 0;
    return Math.round(seconds / 60);
  }

  // ---------- Parent assignments and goals ----------
  function goalLabel(kind, target, topicName) {
    if (kind === 'level') return 'Reach level ' + target;
    if (kind === 'streak') return 'Study ' + target + ' days in a row';
    if (kind === 'exam') return 'Score ' + target + '% or more in a timed exam';
    return 'Finish every lesson in ' + (topicName || target);
  }
  function goalReached(goal, state, catalog, today) {
    var s = normalize(state), target = Number(goal.target);
    if (goal.kind === 'level') return levelFor(s.xp).level >= target;
    if (goal.kind === 'streak') return streak(s, today).best >= target;
    if (goal.kind === 'exam') return s.attempts.some(function (a) { return a.percent >= target; });
    if (goal.kind === 'topic') {
      var row = topicRows(s, catalog).filter(function (r) { return r.key === goal.target; })[0];
      return !!row && row.lessons > 0 && row.lessonsDone >= row.lessons;
    }
    return false;
  }
  // Marks newly reached goals as unlocked and returns them, so the page can celebrate once.
  function unlockGoals(state, catalog, today) {
    var s = normalize(state), fresh = [];
    today = today || dayKey();
    s.goals.forEach(function (g) {
      if (!g.unlockedAt && goalReached(g, s, catalog, today)) { g.unlockedAt = today; fresh.push(g); }
    });
    return fresh;
  }
  function assignmentDone(a, state) {
    var s = normalize(state);
    if (a.kind === 'lesson') return s.lessons.indexOf(a.target) >= 0;
    // An exam assigned as "<subject>-<count>". sameDay is how many that subject had already been
    // taken on the day it was assigned, because attempts only record the date.
    var subject = String(a.target).split('-')[0];
    var since = s.attempts.filter(function (t) { return t.subject === subject && t.date >= (a.created || ''); });
    return since.length > (a.sameDay || 0);
  }

  // ---------- Related lessons for the AI coach ----------
  // Showing nothing is better than a lesson that only shares a word with the question.
  var RELATED_STOP = ('the and for are was were what why how when where which who that this with from your have has ' +
    'then than does did can could would should will about into there their them they you our not but its use used ' +
    'using find get give show shows explain tell help rule rules formula formulas concept definition case form model ' +
    'relation property value values time times number numbers word words question answer example problem best choice ' +
    'correct right wrong difference between same make makes work').split(' ');
  var SUBJECT_TERMS = {
    physics: /\b(velocity|accelerat\w*|forces?|newtons?|momentum|kinetic|energy|volts?|voltage|amperes?|resistors?|resistance|ohms?|circuits?|wavelength|frequency|photons?|electrons?|magneti\w*|gravit\w*|friction|projectile|torque|joules?|watts?|isotopes?|half-life|nuclear|radioactive|doppler|capacitors?|inertia|displacement)\b|\bm\/s\b/g,
    math: /\b(equations?|solve|factori[sz]e|quadratic|polynomials?|derivatives?|integrals?|slopes?|intercepts?|triangles?|circles?|angles?|radius|diameter|perimeter|area|volume|sine?|cos(ine)?|tan(gent)?|logs?|logarithms?|fractions?|percent(age)?|ratio|proportion|probability|median|graph|inequalit\w*|exponents?|roots?|matrix|sequence|sum|multiply|divide|subtract)\b|\d\s*[-+*\/=^]\s*\d|\d[a-z]\b|=/g,
    english: /\b(grammar|sentences?|verbs?|nouns?|pronouns?|adjectives?|adverbs?|prepositions?|tenses?|clauses?|commas?|semicolons?|apostrophes?|punctuation|synonyms?|antonyms?|vocabulary|paragraphs?|passages?|essays?|spelling|conjunctions?|gerunds?|infinitives?|articles?|conditionals?|plural|singular)\b/g
  };
  function relatedTokens(text, keepStops) {
    var seen = {}, out = [];
    (String(text || '').toLowerCase().match(/[a-z]{2,}/g) || []).forEach(function (word) {
      if (!keepStops && (word.length < 3 || RELATED_STOP.indexOf(word) >= 0)) return;
      var stem = word.length > 7 ? word.slice(0, 7) : word.replace(/s$/, '');
      if (!seen[stem]) { seen[stem] = true; out.push(stem); }
    });
    return out;
  }
  function guessSubject(text) {
    function count(subject) { return (text.match(SUBJECT_TERMS[subject]) || []).length; }
    var physics = count('physics'), math = count('math'), english = count('english');
    if (physics && physics >= english) return 'physics';
    return math > english ? 'math' : english > math ? 'english' : '';
  }
  // Physics has no lessons yet, so a physics question gets { physics: true } and no picks.
  function relatedLessons(question, reply, catalog) {
    var raw = String(question || '').toLowerCase(), answer = String(reply || '').toLowerCase();
    // "What does this mean?" is not a question about the statistics lesson called Mean.
    var asked = raw.replace(/\b(does|do|did)\b([^?.!]*)\bmean(?=\s*(?:[?.!]|$))/g, '$2').replace(/\bmean (by|that|to)\b/g, ' ');
    var typed = relatedTokens(asked), subject = guessSubject(typed.length ? asked : answer);
    if (subject === 'physics') return { physics: true, picks: [] };
    // A photo or an Arabic question has no English words to match, so the reply stands in for it.
    var inQuestion = typed.length ? typed : relatedTokens(answer), inReply = relatedTokens(answer);
    var allQuestionWords = relatedTokens(raw, true);
    var aboutWords = /\b(mean|meaning|means|define|definition|synonyms?|antonyms?|vocabulary|passage|reading|paragraph|author|essay)\b/.test(raw);
    var picks = [];
    ['math', 'english'].forEach(function (name) {
      if ((subject && subject !== name) || !catalog || !catalog[name]) return;
      var softTopics = {}, usage = {};
      (catalog[name].topics || []).forEach(function (topic) { if (/vocab|reading/i.test(topic.name)) softTopics[topic.id] = true; });
      var lessons = catalog[name].lessons || [];
      lessons.forEach(function (l) { relatedTokens(l.title).forEach(function (w) { usage[w] = (usage[w] || 0) + 1; }); });
      lessons.forEach(function (lesson) {
        var words = relatedTokens(lesson.title);
        if (!words.length) {
          // Titles made only of small words, such as "Some / any" or "Who / whom".
          var small = relatedTokens(lesson.title, true);
          var quoted = small.length === 1 && new RegExp('[\'"‘“]' + small[0] + '[\'"’”]').test(raw);
          var named = small.length > 1 && small.every(function (w) { return allQuestionWords.indexOf(w) >= 0; });
          if (quoted || named) picks.push({ score: 9, subject: name, lesson: lesson });
          return;
        }
        var hits = words.filter(function (w) { return inQuestion.indexOf(w) >= 0; });
        var extra = words.filter(function (w) { return inReply.indexOf(w) >= 0; }).length;
        var full = hits.length === words.length;
        var literal = subject && lesson.title.indexOf(' ') > 0 && answer.indexOf(lesson.title.toLowerCase()) >= 0;
        // Everyday words such as "novel" or "purpose" count only if the question is about words.
        if (words.length === 1 && softTopics[lesson.topicId]) {
          var isQuoted = new RegExp('[\'"‘“]' + lesson.title.toLowerCase() + '[\'"’”]').test(raw);
          if (full && (isQuoted || aboutWords)) picks.push({ score: 9, subject: name, lesson: lesson });
          return;
        }
        if (!typed.length && words.length < 2 && !literal) return;
        var rare = typed.length && subject && hits.some(function (w) { return w.length >= 5 && usage[w] <= 4; });
        if (full || hits.length >= 2 || rare) {
          picks.push({ score: hits.length * 3 + (full ? 3 : 0) + extra, subject: name, lesson: lesson });
        } else if (literal || (subject && words.length >= 2 && extra === words.length)) {
          // The title is in the answer, such as "Quadratic Standard Form".
          picks.push({ score: 1, subject: name, lesson: lesson });
        }
      });
    });
    picks.sort(function (a, b) { return b.score - a.score; });
    return {
      physics: false,
      picks: picks.slice(0, 3).map(function (p) { return { subject: p.subject, lesson: p.lesson }; })
    };
  }

  // ---------- Small rewards (browser only; every one can be turned off) ----------
  var SETTINGS_KEY = 'estsat.settings';
  function getSettings() {
    var saved = {};
    try { saved = JSON.parse(localStorage.getItem(SETTINGS_KEY)) || {}; } catch (e) { saved = {}; }
    return { sound: saved.sound !== false, confetti: saved.confetti !== false, haptics: saved.haptics !== false };
  }
  function setSetting(name, value) {
    var s = getSettings();
    s[name] = value;
    try { localStorage.setItem(SETTINGS_KEY, JSON.stringify(s)); } catch (e) { /* stays on for this visit */ }
    return s;
  }
  var audio = null;
  function chime(big) {
    try {
      audio = audio || new (window.AudioContext || window.webkitAudioContext)();
      (big ? [523.25, 659.25, 783.99, 1046.5] : [659.25, 987.77]).forEach(function (hz, i) {
        var osc = audio.createOscillator(), gain = audio.createGain(), at = audio.currentTime + i * 0.09;
        osc.type = 'sine';
        osc.frequency.value = hz;
        gain.gain.setValueAtTime(0.0001, at);
        gain.gain.exponentialRampToValueAtTime(0.16, at + 0.02);
        gain.gain.exponentialRampToValueAtTime(0.0001, at + 0.35);
        osc.connect(gain);
        gain.connect(audio.destination);
        osc.start(at);
        osc.stop(at + 0.4);
      });
    } catch (e) { /* sound is optional */ }
  }
  function confetti(count) {
    if (window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
    var canvas = document.createElement('canvas');
    canvas.className = 'confetti-canvas';
    canvas.setAttribute('aria-hidden', 'true');
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;
    document.body.appendChild(canvas);
    var ctx = canvas.getContext('2d'), colors = ['#8B5CF6', '#22D3EE', '#34D399', '#EC4899', '#FBBF24'], pieces = [], started = performance.now();
    for (var i = 0; i < count; i += 1) {
      pieces.push({
        x: canvas.width / 2 + (Math.random() - 0.5) * canvas.width * 0.3, y: canvas.height * 0.35,
        vx: (Math.random() - 0.5) * 14, vy: -Math.random() * 12 - 4, size: Math.random() * 6 + 4,
        rotation: Math.random() * Math.PI, spin: (Math.random() - 0.5) * 0.3, color: colors[Math.floor(Math.random() * colors.length)]
      });
    }
    function frame(now) {
      var elapsed = now - started;
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      pieces.forEach(function (p) {
        p.vy += 0.35; p.x += p.vx; p.y += p.vy; p.rotation += p.spin;
        ctx.save();
        ctx.globalAlpha = Math.max(0, 1 - elapsed / 1700);
        ctx.translate(p.x, p.y);
        ctx.rotate(p.rotation);
        ctx.fillStyle = p.color;
        ctx.fillRect(-p.size / 2, -p.size / 4, p.size, p.size / 2);
        ctx.restore();
      });
      if (elapsed < 1700) requestAnimationFrame(frame); else canvas.remove();
    }
    requestAnimationFrame(frame);
  }
  // Browsers refuse vibration before the person has touched the page, and log an error if asked.
  function vibrate(pattern) {
    if (!navigator.vibrate) return;
    if (navigator.userActivation && !navigator.userActivation.hasBeenActive) return;
    if (getSettings().haptics) navigator.vibrate(pattern);
  }
  function celebrate(big) {
    if (typeof window === 'undefined') return;
    var s = getSettings();
    if (s.sound) chime(big);
    if (s.confetti) confetti(big ? 120 : 28);
    vibrate(big ? [40, 40, 80] : 20);
  }

  // ---------- Parent voice notes stay on this device ----------
  function voiceStore(mode, work) {
    return new Promise(function (resolve, reject) {
      if (typeof indexedDB === 'undefined') { reject(new Error('unavailable')); return; }
      var open = indexedDB.open('estsat-voice', 1);
      open.onupgradeneeded = function () { open.result.createObjectStore('notes'); };
      open.onerror = function () { reject(open.error); };
      open.onsuccess = function () {
        var tx = open.result.transaction('notes', mode), req = work(tx.objectStore('notes'));
        tx.oncomplete = function () { resolve(req.result); open.result.close(); };
        tx.onerror = function () { reject(tx.error); open.result.close(); };
      };
    });
  }
  function saveVoice(id, blob) { return voiceStore('readwrite', function (st) { return st.put(blob, id); }); }
  function loadVoice(id) { return voiceStore('readonly', function (st) { return st.get(id); }); }
  function deleteVoice(id) { return voiceStore('readwrite', function (st) { return st.delete(id); }); }

  return {
    REVIEW_STEPS: REVIEW_STEPS, MASTERED_STAGE: MASTERED_STAGE, MAX_MISTAKES: MAX_MISTAKES, LEVELS: LEVELS, RANKS: RANKS, XP: XP, MAX_FREEZES: MAX_FREEZES, GOAL_TARGETS: GOAL_TARGETS,
    dayKey: dayKey, addDays: addDays, daysBetween: daysBetween, weekStart: weekStart, normalize: normalize, reset: reset,
    addStudyTime: addStudyTime, recordAnswer: recordAnswer, recordReview: recordReview, completeLesson: completeLesson, recordExam: recordExam,
    reviewState: reviewState, scheduleReview: scheduleReview, reviewQueue: reviewQueue, reviewSummary: reviewSummary, reviewLabel: reviewLabel,
    topicRows: topicRows, topGains: topGains, readiness: readiness, dailyPlan: dailyPlan, levelFor: levelFor, streak: streak, freezesLeft: freezesLeft, updateFreezes: updateFreezes, badges: badges,
    weeklyChallenge: weeklyChallenge, minutesStudied: minutesStudied, goalLabel: goalLabel, goalReached: goalReached, unlockGoals: unlockGoals, assignmentDone: assignmentDone,
    relatedLessons: relatedLessons,
    getSettings: getSettings, setSetting: setSetting, celebrate: celebrate, vibrate: vibrate, saveVoice: saveVoice, loadVoice: loadVoice, deleteVoice: deleteVoice
  };
}));
