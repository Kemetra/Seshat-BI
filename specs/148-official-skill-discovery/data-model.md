# Data model: Official skill discovery

## Skill activation declaration

- component ID
- harness ID (`claude-code` or `codex`)
- mechanism (`native-plugin`, `agent-skills-projection`, or unsupported)
- upstream marketplace/plugin identity when applicable
- source skill paths and expected discovered names
- activation location/registration fact
- read-only discovery proof
- upgrade behavior

## Discovery result

- component ID and locked upstream coordinate
- harness ID
- installed: boolean + evidence
- activated: boolean + evidence/blocker
- discoverable: boolean + evidence/blocker
- status: present, activation-required, discoverable, unsupported, conflict, or
  failed
- operator next action

`discoverable` can be true only when `installed` and `activated` are both true
and the expected skill identities pass the harness-specific proof.
