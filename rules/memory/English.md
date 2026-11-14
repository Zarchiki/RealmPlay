## memory_record
- Record into Permanent Memory only when a genuine, durable fact occurs in this turn.
- What to record:
  1. Real names, nicknames, and multilingual aliases (e.g. Chinese, Japanese, Thai) when mentioned.
  2. Critical personal secrets, trauma, backstory, or family lore revealed.
  3. Explicit promises, oaths, commitments, and relationship milestones.
  4. Enduring preferences, phobias, allergies, hard boundaries, or meaningful gifted items.
- What NOT to record:
  - Fleeting physical actions (sitting, smiling, walking).
  - Momentary emotions (feeling tired, startled).
  - Routine greetings and casual banter without new facts.
  - Duplicate facts already recorded in memory.
- Output Format: When triggered, append closed fenced block with importance (`imp:3` to `5`) and search tags:
  `memory
  - [imp:5 | tags:topic,keyword] Concise, single-sentence factual memory line
  `
