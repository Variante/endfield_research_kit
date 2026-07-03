# Profile Social Reverse Source-Graph Recovery - 2026-07-03

## Scope

Profile/social catalog tables already emitted forward links from profile
pictures, avatars, business-card topics, mail templates, and friend-chat
entries to their typed targets. This pass added reverse lookup edges so item,
character, sender, and tab queries can recover the catalog objects that use
them.

## Added Reverse Edges

- `character_has_profile_picture`
- `profile_picture_in_type`
- `item_unlocks_profile_picture`
- `item_unlocks_user_avatar`
- `item_unlocks_business_card_topic`
- `mail_sender_used_by_template`
- `friend_chat_emotion_in_tab`
- `friend_chat_text_in_tab`

## Validation

Focused temp graph:
`tmp/profile_social_reverse_validate.sqlite`

Counts from `ingest_profile_social_semantics()`:

| Forward edge | Count | Reverse edge | Count |
| --- | ---: | --- | ---: |
| `picture_for_character` | 88 | `character_has_profile_picture` | 88 |
| `profile_picture_type_has_picture` | 176 | `profile_picture_in_type` | 176 |
| `profile_picture_unlock_item` | 176 | `item_unlocks_profile_picture` | 176 |
| `user_avatar_unlock_item` | 39 | `item_unlocks_user_avatar` | 39 |
| `business_card_unlock_item` | 20 | `item_unlocks_business_card_topic` | 20 |
| `mail_template_sender` | 39 | `mail_sender_used_by_template` | 39 |
| `friend_chat_emotion_tab_has_emotion` | 118 | `friend_chat_emotion_in_tab` | 118 |
| `friend_chat_text_tab_has_text` | 48 | `friend_chat_text_in_tab` | 48 |

CLI smoke checks:

- `python tools\endfield_source_graph.py query chr_0004_pelica --kind character --db tmp\profile_social_reverse_validate.sqlite --limit 12`
  showed `character_has_profile_picture`.
- `python tools\endfield_source_graph.py query user_avatar_activity_1 --kind user_avatar --db tmp\profile_social_reverse_validate.sqlite --limit 12`
  showed `item_unlocks_user_avatar`.
- `python tools\endfield_source_graph.py query activity_reissue_test_mail --kind mail_template --db tmp\profile_social_reverse_validate.sqlite --limit 12`
  showed `mail_sender_used_by_template`.
- `python tools\endfield_source_graph.py query chat_emojis_tab_1 --kind friend_chat_emotion_tab --db tmp\profile_social_reverse_validate.sqlite --limit 12`
  showed `friend_chat_emotion_in_tab`.

`python -m py_compile tools\endfield_source_graph.py` passed.
