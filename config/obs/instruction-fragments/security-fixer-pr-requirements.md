**Pull Request Requirements:**
- Create a pull request in `Draft` state first.
- PR title should reference fixing the security issue (e.g., "[oblt-aw][security] Fix token exposure in workflow X").
- PR body must include:
  - `Closes #<issue-number>` at the top to link and auto-close the source issue on merge
  - checklist of plan steps completed
  - evidence of successful tests/validation
  - explicit confirmation that least-privilege and env-indirection patterns were applied
