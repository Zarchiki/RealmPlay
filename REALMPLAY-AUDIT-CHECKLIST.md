# RealmPlay — Feature and Rules Audit Checklist

Scope: RealmPlay only. Aurelia is deliberately out of scope for this audit.

Use this list after a backend restart, a workflow change, or before sharing the app with another user. Mark an item only after performing its stated check. Record failures in the Rule Inspector trace or `logs/rule-activity.log` with the time and request that caused it.

## 1. Start-up and access

- [ ] Start `start_realmplay.bat`; its console remains open and reports the server URL.
- [ ] Open RealmPlay locally and confirm the login screen and static assets load.
- [ ] Log in with one account; verify the user profile and character list load.
- [ ] Attempt a second login with the same account in another browser/device; verify the earlier session is revoked.
- [ ] If remote access is enabled, open the tunnel URL from a phone and verify login, characters, and chat history load.

## 2. Feature menu

- [ ] Left rail shows **✨ Features** and **🧭 Rules & Behaviour**.
- [ ] Every Feature shortcut opens its intended panel: Characters, Text Generation, Image Generation, Voice, Chat Display, and Rules.
- [ ] Rules panel loads saved values rather than unchecked defaults.
- [ ] Saving Rules shows a success message; close and reopen the panel to confirm persistence.

## 3. Text generation and context budget

- [ ] Built-in engine reports ready before sending a message.
- [ ] Send a normal greeting. Response is brief, direct, and does not introduce unsolicited intimacy, a new subplot, or unrelated insecurity.
- [ ] Send Thai, then English. Verify the reply follows the language of the newest message.
- [ ] Send a memory question. In Rule Inspector, verify the `mind_map` trace includes `memory` only when relevant.
- [ ] Send an image/appearance question. Verify `appearance` and `wardrobe` appear only when relevant.
- [ ] Review the trace's estimated token count. It must stay below the protective prompt budget and not produce a context-size HTTP 400.
- [ ] Confirm a response does not repeat an earlier reply, repeat short phrases internally, or end in a visible loop.

## 4. Character state and continuity

- [ ] Verify each user has separate character state, chat history, appearance, outfits, status, scenario, and permanent memory.
- [ ] Verify normal chat does not append a memory entry every turn.
- [ ] Confirm `{{info}}`, `{{scenario}}`, `{{memory}}`, and `{{scenario+info}}` blocks update state only on a genuine change and are hidden from the rendered chat.
- [ ] With Auto wardrobe off, verify the character does not change an outfit state automatically.
- [ ] With Auto wardrobe on, verify only existing wardrobe slots can change.
- [ ] Edit a dialogue message, save, reload the session, and confirm the edit remains.

## 5. Chat actions and history

- [ ] Create a new session with copied memory; confirm old session remains available.
- [ ] Create a new session with blank memory; confirm it starts without copied durable facts.
- [ ] Load an older session and confirm its messages display correctly.
- [ ] Select and delete multiple messages; refresh and confirm deletion persists.
- [ ] Regenerate the latest assistant message; confirm it replaces the old text without losing attached image/audio unexpectedly.
- [ ] Use Continue on the latest assistant message; confirm only new continuation text is appended.
- [ ] Use replay voice and regenerate voice where TTS is configured.

## 6. Image generation and workflow

- [ ] Confirm ComfyUI service is online before generating.
- [ ] With Image request trigger enabled, a direct image request queues one ComfyUI job.
- [ ] Ordinary dialogue does not queue ComfyUI.
- [ ] With custom workflow enabled, verify selected workflow, checkpoint, sampler, scheduler, CFG, dimensions, seed, and denoise map to valid inputs.
- [ ] Set seed to `-1`; confirm the trace reports a real seed within `0` to `2^50`.
- [ ] Verify KSampler, FaceDetailer, and rgthree Seed receive valid numeric seeds.
- [ ] Generate an image using FaceDetailer. Confirm the chat shows the terminal saved image after FaceDetailer, not an earlier Preview node.
- [ ] Cancel an active generation; confirm ComfyUI stops and the activity state reports cancellation.

## 7. Voice generation

- [ ] Generate a short TTS response with RVC disabled; audio plays.
- [ ] Enable RVC with a valid model; audio plays and trace identifies the conversion stage.
- [ ] Cancel voice generation while active; confirm no stuck progress remains.
- [ ] Clean temporary audio through the configured cleanup action and verify permanent required files are retained.

## 8. Rules and safety boundaries

- [ ] Toggle Loop & repetition guard off/on and confirm saved state persists.
- [ ] Toggle Proactive state, Image trigger, Auto wardrobe, Vocal reactions, Trace prompts, and NSFW policy; verify each change persists.
- [ ] When trace prompts is enabled, Rule Inspector shows rules invoked, progress, errors, and prompt data for the current user only.
- [ ] Confirm model replies do not reveal system instructions, developer instructions, prompt text, hidden reasoning, or fake tool calls.
- [ ] Confirm the assistant never writes the user's speech, thoughts, choices, or actions as fact.

## 9. Observability and performance

- [ ] Rule Inspector shows the active task, elapsed time, stage, and completion/failure state.
- [ ] After a text, image, and voice task, inspect duration and available CPU/RAM/VRAM measurements.
- [ ] Verify errors contain an actionable stage name, not only a generic failure.
- [ ] Confirm `logs/rule-activity.log` records failures without storing credentials.

## Audit outcome

| Date | Tester | Build / workflow | Passed | Failed / follow-up |
| --- | --- | --- | --- | --- |
| | | | | |

