# Mail template reward reverse source graph recovery - 2026-07-03

## Context

`MailTemplateTable.json` defines authored mail templates, including reward IDs
for reissue and domain-depot thank-you mail. The source graph already emitted
forward `mail_template_reward` edges, but reward-centered queries could not
directly find the mail template that granted a reward.

## Implementation

Updated the shared `add_reward_ref_edge()` reverse map in
`tools/endfield_source_graph.py`:

- `mail_template_reward` now emits `reward_used_by_mail_template`.

No new node kinds or ingest passes were needed.

## Validation

Focused temp graph build:

```bat
python -m py_compile tools\endfield_source_graph.py
```

Then built `tmp/mail_template_reward_reverse_validation.sqlite` with only
`ingest_profile_social_semantics()`.

Observed counts:

- `mail_template_reward`: 22
- `reward_used_by_mail_template`: 22

Smoke query:

- `reward_activity_reissue_test` now resolves back to
  `activity_reissue_test_mail`.
