# RealmPlay Character State Protocol

## Purpose

RealmPlay keeps **character definition** separate from **a player's ongoing
relationship with that character**.  A Character Card controls personality,
voice, background, and the narrative rules.  A per-user state controls the
current roleplay, visual appearance used for generation, and memories.

This prevents one player's story, image prompt, wardrobe, or memory from
changing the Character Card or another player's experience.

## Storage layout

```text
characters/<character>/                         shared Character Card
├── card.json                                   Character Card V2 document
├── persona.md                                  Description / narrative context
├── personality.md                              Personality and voice
├── default_scenario.md                         New-session starting context
├── first_mes.txt                               First message
├── config.json                                 Character metadata
├── avatar.png                                  Shared chat icon
└── sprites/                                    Shared sprite assets

users/<username>/<character>/                   isolated player state
├── appearance.md                               Image-only visual identity
├── profile_image.png                           Player-specific character portrait
├── scenario.md                                 Current Situation
├── status.md                                   Current Status / info panel
├── PermanentMemory.md                          Durable shared history for this pair
├── emotion.txt                                 Current emotion for image generation
├── outfits.json                                Active wardrobe and clothing prompts
├── history.json                                Active-session message history
└── chat_sessions/
    ├── index.json                              Active session and session list
    └── <session-id>.json                       Archived session history + memory
```

## Ownership and use

| Data | Owner | Used by LLM | Used by image generation |
| --- | --- | --- | --- |
| Character Card description, personality, scenario | Character Card | Yes | No |
| `appearance.md` | User + character | No | Yes |
| `scenario.md`, `status.md`, `PermanentMemory.md` | User + character | Yes | Optional context source |
| `emotion.txt`, `outfits.json` | User + character | Yes | Yes |
| `profile_image.png` | User + character | No | Display only |

`appearance.md` is migrated from the old Card Description on first access for
existing data.  After that migration it never syncs back to `persona.md`.

## Autonomous state updates

The model may update state after a reply only when the state genuinely changes.
The blocks are internal: RealmPlay saves them, removes them from the displayed
chat message, and keeps the roleplay reply clean.

Use exactly one of these forms, with matching closing fences:

````text
```{{info}}
Location: Academy library
Time: 19:30
Mood: Focused
```

```{{scenario}}
The two are researching the sealed archive after class.
```

```{{scenario+info}}
D6 | 0000/00/00 | Sun | 19:30 | 🌙 | Academy library
The two are researching the sealed archive after class.
```

```{{memory}}
{{user}} promised to help {{char}} find the missing archive key.
```
````

- `{{info}}` writes `status.md`.
- `{{scenario}}` writes `scenario.md`.
- `{{scenario+info}}` writes both files.
- `{{memory}}` appends one new durable fact to `PermanentMemory.md` and skips
  duplicates.
- `[emotion: shy]` writes `emotion.txt`.

Do not create blocks for ordinary dialogue beats.  Permanent memory is limited
to commitments, discoveries, relationship changes, major events, or facts that
must persist across sessions.

## Update pipeline

1. RealmPlay loads the Character Card and the active player's isolated state.
2. The prompt builder supplies card context plus compressed current state.
3. The LLM produces the visible roleplay reply and optional internal state
   blocks.
4. The parser strips valid state blocks before saving/displaying the reply.
5. The state writer persists only the changed per-user files.
6. Image generation takes scene/action first, then `appearance.md`, wardrobe,
   emotion, and configured image suffixes.

## Compatibility

Older ` ```status`, ` ```scenario`, and ` ```memory` blocks are still read so
existing chats remain usable.  New prompts must emit the canonical
` ```{{...}}` format above.
