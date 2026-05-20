---
name: pr-summary
description: Generate a concise PR summary from the diff and commit history
argument-hint: "<PR-number>"
allowed-tools: ["Bash", "Read", "WebFetch"]
---

# PR Summary Generator

Generate a concise, structured summary of a pull request for reviewers.

## Fetch PR data

```bash
# Get the diff
gh pr diff "$PR_NUMBER"

# Get PR metadata
gh pr view "$PR_NUMBER" --json title,body,labels,files,commits

# Get changed file list
gh pr diff "$PR_NUMBER" --name-only
```

If `gh` is not available, fall back to WebFetch with the PR URL.

## Analyze changes

Read the diff and classify the changes:

- **New files** — what do they add?
- **Modified files** — what changed and why?
- **Deleted files** — what was removed and is anything broken?
- **Test changes** — do tests cover the new functionality?

## Generate summary

Produce a summary with:

1. One-sentence description of what the PR does
2. List of key changes grouped by area
3. Risk assessment (low/medium/high)
4. Testing coverage assessment
