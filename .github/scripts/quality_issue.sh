#!/usr/bin/env bash
# Keep one open GitHub issue (label data-quality) in sync with the pipeline result.
#   failure -> open the issue, or comment on the open one, with the failing checks
#   success -> comment and close the open issue
# Usage: quality_issue.sh <pipeline outcome: success|failure> <report.md>
# Needs GH_TOKEN with issues: write.
set -euo pipefail

outcome="$1"
report="$2"
run_url="${GITHUB_SERVER_URL}/${GITHUB_REPOSITORY}/actions/runs/${GITHUB_RUN_ID}"
label="data-quality"

gh label create "$label" --color D93F0B --description "Failed data quality run" --force >/dev/null
open_issue=$(gh issue list --label "$label" --state open --limit 1 --json number --jq '.[0].number // empty')

if [ "$outcome" = "failure" ]; then
  body=$(mktemp)
  {
    echo "Run: $run_url"
    echo
    if [ -f "$report" ] && grep -q '^| FAIL |' "$report"; then
      echo "| Status | Table | Check | Dimension | Observed | Expected |"
      echo "|---|---|---|---|---|---|"
      grep '^| FAIL |' "$report"   # table rows only, not the summary line
    else
      echo "The pipeline failed before the checks finished (scrape or load error). See the run log."
    fi
  } > "$body"
  if [ -n "$open_issue" ]; then
    gh issue comment "$open_issue" --body-file "$body"
    echo "commented on issue #$open_issue"
  else
    gh issue create --title "Data quality run failed" --label "$label" --body-file "$body"
  fi
elif [ -n "$open_issue" ]; then
  gh issue close "$open_issue" --comment "No failing checks in $run_url"
  echo "closed issue #$open_issue"
else
  echo "no open data-quality issue, nothing to do"
fi
