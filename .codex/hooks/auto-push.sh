#!/usr/bin/env bash
# Commit every local change and push it to origin. Wired to the Stop hook in
# .claude/settings.json, so it runs each time Claude finishes a turn.
# Pushing the default branch makes Vercel redeploy est-sat-platform.vercel.app.
set -uo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO" 2>/dev/null || exit 0
[ -d .git ] || exit 0

LOG="$REPO/.claude/auto-push.log"
log() { printf '[%s] %s\n' "$(date '+%F %T')" "$*" >> "$LOG"; }
msg() {
  local m
  m="$(printf '%s' "$*" | tr -d '"\\' | tr '\n\r\t' '   ' | cut -c1-300)"
  printf '{"systemMessage":"%s","suppressOutput":true}\n' "$m"
}

BRANCH="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || true)"
if [ -z "$BRANCH" ] || [ "$BRANCH" = "HEAD" ]; then
  log "detached HEAD; skipping"; msg "auto-push skipped: detached HEAD"; exit 0
fi

ahead() { [ -n "$(git log --oneline "origin/$BRANCH..$BRANCH" 2>/dev/null || true)" ]; }

if [ -z "$(git status --porcelain)" ]; then
  if ! ahead; then log "clean and in sync on $BRANCH"; exit 0; fi
  log "clean but ahead of origin/$BRANCH; pushing"
else
  git add -A

  # Secret guard: these never reach the remote, even if .gitignore misses them.
  BLOCKED="$(git diff --cached --name-only \
    | grep -Ei '(^|/)\.env($|\.)|\.(pem|key|p12|pfx|keystore)$|(^|/)id_(rsa|ed25519)|(^|/)credentials\.json$' \
    | grep -v '\.env\.example$' || true)"
  if [ -n "$BLOCKED" ]; then
    log "BLOCKED, left uncommitted: $(printf '%s' "$BLOCKED" | tr '\n' ' ')"
    while IFS= read -r f; do [ -n "$f" ] && git reset -q -- "$f"; done <<< "$BLOCKED"
  fi

  if [ -n "$(git diff --cached --name-only)" ]; then
    N="$(git diff --cached --name-only | wc -l | tr -d ' ')"
    FILES="$(git diff --cached --name-only | head -3 | sed 's#.*/##' | paste -sd', ' -)"
    if ! git commit -q -m "Auto-sync: $N file(s) ($FILES)

Committed and pushed automatically when the Claude Code session stopped.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"; then
      log "commit failed"; msg "auto-push: commit failed, see .claude/auto-push.log"; exit 0
    fi
    log "committed $N file(s) on $BRANCH"
  elif ! ahead; then
    log "nothing to commit after secret guard"
    msg "auto-push: nothing committed (only ignored or blocked files changed)"
    exit 0
  fi
fi

if git push -q origin "HEAD:refs/heads/$BRANCH" 2>>"$LOG"; then
  log "pushed $(git rev-parse --short HEAD) to origin/$BRANCH"
  msg "Pushed $(git rev-parse --short HEAD) to origin/$BRANCH - Vercel will redeploy"
elif git pull -q --rebase --autostash origin "$BRANCH" 2>>"$LOG" \
  && git push -q origin "HEAD:refs/heads/$BRANCH" 2>>"$LOG"; then
  log "pushed $(git rev-parse --short HEAD) after rebase"
  msg "Pushed $(git rev-parse --short HEAD) to origin/$BRANCH after rebase"
else
  log "PUSH FAILED on $BRANCH; commit is local only"
  msg "auto-push FAILED on $BRANCH - commit is local only, see .claude/auto-push.log"
fi
exit 0
