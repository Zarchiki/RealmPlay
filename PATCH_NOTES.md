# Patch Notes

## 2026-11-14 — Fix Hugging Face Model Fetching URL for Vision mmproj

### What changed
- **Model Downloader & Vision Projector URL ([`download_models.py`](file:///k:/RealmPlay-Standalone/download_models.py)):**
  - Discovered that the vision mmproj URL in Hugging Face returned `404 Not Found` due to filename mismatch:
    - Old/Invalid: `mmproj-Qwen3.5-4B-mmproj-BF16.gguf`
    - Actual repo path: `mmproj-Qwen3.5-4B-Uncensored-HauhauCS-Aggressive-BF16.gguf`
  - Fixed download URL and destination path in `download_models.py`.
  - Updated default `mmproj` config filename in `config.example.json` and `config.json`.
  - Updated model documentation table in `README.md`.

### Verification
- Queried Hugging Face API and performed HTTP GET verification for both models in `download_models.py`:
  - `Qwen3.5-4B-Uncensored-HauhauCS-Aggressive-Q4_K_M.gguf`: HTTP 200 (~2.7 GB)
  - `mmproj-Qwen3.5-4B-Uncensored-HauhauCS-Aggressive-BF16.gguf`: HTTP 200 (~675 MB)



## 2026-11-14 — Single-User Mode without Password Authentication

### What changed
- **Configuration (`config.example.json` & `config.json`):**
  - Added `"single_user_mode": true` under `"server"` block.
- **Backend Authentication Dependency ([`server.py`](file:///k:/RealmPlay-Standalone/server.py)):**
  - Added `is_single_user_mode()` helper checking `server.single_user_mode` in `config.json`.
  - Updated `get_current_user()`: when `single_user_mode` is enabled, automatically resolves as `"admin"` (with built-in admin permissions) if no Authorization header or token is provided.
  - Updated `/api/auth/me` response to include `"single_user_mode": is_single_user_mode()`.
- **Frontend Automatic Login ([`static/js/app_main.js`](file:///k:/RealmPlay-Standalone/static/js/app_main.js)):**
  - Updated `window.onload` and `fetchUserProfile()`: permits fetching profile without pre-existing token; in single-user mode, automatically initializes session for `admin` and skips displaying `#auth-screen`.

### Rules for other agents (avoid conflicts)
- Keep `single_user_mode` configurable via `config.json` under `server.single_user_mode`.
- When `single_user_mode` is false or unset, standard Bearer token validation and login prompt remain intact.

### Verification
- `python -c "import py_compile; py_compile.compile('server.py', doraise=True)"` passed with code 0.
- ASGI AsyncClient testing without Authorization headers successfully returned HTTP 200 for `/api/auth/me` (user: admin, is_admin: True, single_user_mode: True), `/api/characters`, `/api/rules`, and `/api/settings`.
- End-to-end frontend assets loaded without missing references.



## 2026-11-11 — Support CNC Session Agreement to Disable Automatic Scene Stop on Character Narrated Action Refusal

### What changed
- **CNC Session Boundary Handling in [`scene_state.py`](file:///k:/RealmPlay/scene_state.py):**
  - Updated `apply_character_action_refusal()`: When `cnc_agreement=True`, in-character resistance or verbal/physical refusals from CHAR against USER's narrated physical actions (`*...*`) are preserved as consensual roleplay resistance instead of executing a `hard_stop()` back to `normal:0`.
  - Maintained Requirement 4: Explicit USER stop requests (e.g. `หยุด`, `พอ`, `เลิก`, `ไม่ทำ`) confirmed by CHAR continue to stop the scene unconditionally as real boundaries.
  - Updated `resolve_normal_intimacy_character_response()`: When `normal_intimacy_cnc_agreement` is active, keep the scene active and transition accepted without dropping back to normal.
  - Fixed typo in `is_character_orgasm_signal()` regex where an unescaped/unbalanced parenthesis `)|มาแล้ว)` was causing a `re.PatternError`.
- **CNC Agreement Pass-through in [`server.py`](file:///k:/RealmPlay/server.py):**
  - Updated `update_h_scene_progression()` call to `scene_state.apply_character_action_refusal()` to pass `cnc_agreement=bool(cnc_enabled or advanced.get("normal_intimacy_cnc_agreement"))`.

### Rules for other agents (avoid conflicts)
- When `cnc_roleplay_enabled` (or `cnc_agreement`) is active, do not force active scenes back to `normal:0` merely because CHAR acts resistant or protests in-character against a USER action.
- Only actual USER stop commands (`หยุด`, `พอ`, etc.) override CNC agreements.

### Verification
- `python -m py_compile server.py scene_state.py` passed with code 0.
- Ran all CNC unit tests (`test_character_refusal_of_starred_action_stops_active_scene`, `test_cnc_agreement_keeps_starred_action_resistance_in_scene`, `test_explicit_cnc_session_agreement_keeps_fictional_resistance_in_intimacy`, `test_cnc_agreement_can_keep_normal_to_foreplay_entry`, `test_cnc_agreement_can_keep_normal_to_explicit_entry`, `test_cnc_signals_are_semantic_only_until_cnc_is_enabled`, `test_stealth_cnc_modifier_uses_the_following_sexual_action`) — all passed (7/7 OK).
- Tested `server.update_h_scene_progression()` with both `cnc_enabled=False` (scene stops to normal) and `cnc_enabled=True` (scene remains active in foreplay).
- `test_router_migration.py` and `test_service_helpers.py` passed with code 0.



## 2026-11-11 — Canonical Slot Tag Categorization in Wardrobe Catalog & Inventory Mutator

### What changed
- **Catalog Slot Tags (`data/wardrobe_catalog.json` & `import_wardrobe_wildcards.py`):**
  - Updated all items across catalog slots (`outer`, `top`, `top_inner`, `bottom`, `bottom_inner`, `socks`, `shoes`, `head`, `head_acc`, `neck_acc`, `hand_acc`, `leg_acc`, etc.) to carry explicit `"slot"` tags matching their category key.
  - Updated [`import_wardrobe_wildcards.py`](file:///k:/RealmPlay/import_wardrobe_wildcards.py) to persist `"slot": s` when importing wildcards into the wardrobe catalog.
- **Inventory Mutator Slot Determination ([`server.py`](file:///k:/RealmPlay/server.py)):**
  - Added cached catalog slot resolver `get_catalog_slot_for_item(name, prompt, default)` indexing all catalog items by canonical name and prompt.
  - Replaced fragile substring heuristics in `/api/characters/{char_name}/inventory` (`action == "equip"`) with canonical slot resolution:
    1. Check item's own `slot` tag (`target.get("slot")`).
    2. Query catalog slot cache via `get_catalog_slot_for_item(item_name, target.get("prompt"))`.
    3. Fallback to `"top"` if unresolvable.
  - Expanded `STANDARD_WARDROBE_SLOTS` to include accessory slots (`head_acc`, `neck_acc`, `hand_acc`, `leg_acc`).

### Rules for other agents (avoid conflicts)
- Never use manual name/description keyword heuristic blocks (e.g. `if "blazer" in name...`) to determine wardrobe slots.
- Always use the item's `"slot"` attribute or call `get_catalog_slot_for_item(name, prompt, default)`.

### Verification
- `python -m py_compile server.py import_wardrobe_wildcards.py` passed with code 0.
- `python -m unittest discover -s tests -p "test_wardrobe_transition.py"` passed with 6/6 tests OK.
- Tested `get_catalog_slot_for_item()` across multiple categories (`blazer` -> `outer`, `matching cheeky panties` -> `bottom_inner`, item with slot tag, unknown item default fallback).



## 2026-11-11 — Centralized Subset Synonym Dictionaries & Shared Reuse (Token Savings & Intent Precision)

### What changed
- **Centralized Wardrobe Removal Synonyms in [`server.py`](file:///k:/RealmPlay/server.py):**
  - Consolidated scattered regex patterns into shared reusable constants:
    - `WARDROBE_REMOVAL_VERBS`: `r"(?:ถอด|ปลด|เปลื้อง|ลอก|รูด|ดึง|remove|take\s+off|strip)"`
    - `WARDROBE_TOTAL_STRIP_SYNONYMS`: `r"(?:หมดตัว|ให้หมด|ทั้งหมด|ทั้งตัว|เปลือย|เกลี้ยง|แก้ผ้า|all(?:\s+of\s+it)?|strip\s+all)"`
    - `WARDROBE_UNDERWEAR_SET_SYNONYMS`: `r"(?:ชุดชั้นใน|กกน|lingerie|underwear\s*set)"`
    - `WARDROBE_SWIMSUIT_SET_SYNONYMS`: `r"(?:ชุดว่ายน้ำ|บิกินี(?:่+)?|swimsuit|swimwear)"`
    - `WARDROBE_OUTERWEAR_SYNONYMS`: `r"(?:ชุดตัวนอก|เสื้อตัวนอก|เสื้อนอก|เสื้อคลุม|แจ[็๊]?คเก็ต|โค้ท|jacket|coat|outerwear)"`
    - `WARDROBE_GENERAL_OUTFIT_SYNONYMS`: `r"(?:ชุด|เสื้อผ้า|outfit|clothes)"`
  - Reused across `_requested_remove_slots()`, `_inactive_removal_request_slots()`, `_suppress_inactive_wardrobe_removal_claim()`, and `_pending_user_request_state()`.
  - Added specific piece modifier preservation (`ชิ้นบน`, `ชิ้นล่าง`, `top`, `bottom`) so specific piece commands like `ถอดบิกินี่ชิ้นล่างสิ` target `bottom_inner` without accidentally triggering the whole compound bikini set.
  - Added dedicated handling for `เหลือแต่ชุดชั้นใน` / `เหลือเพียงชุดชั้นใน` (completed removal of outer garments leaving underwear).
- **Canonical Anatomical Polarity Subset Dictionaries (Token Optimization in Prompts):**
  - Standardized anatomical ownership strings into concise canonical subsets:
    - `CANONICAL_FEMALE_ANATOMY = "female (vagina, breasts / ช่องคลอด, เนินอก)"`
    - `CANONICAL_MALE_ANATOMY = "male (penis, shaft / องคชาต, ดุ้น)"`
    - `CANONICAL_FEMALE_LABEL = f"Female genitalia ({CANONICAL_FEMALE_ANATOMY} — receiving / vaginal partner)"`
    - `CANONICAL_MALE_LABEL = f"Male genitalia ({CANONICAL_MALE_ANATOMY} — penetrating partner)"`
  - Replaced repetitive lengthy word lists (`ช่องคลอด, จิ๋ม, หี, เนินอก`, `องคชาต, ดุ้น, ควย, ลำกาย`, etc.) in `build_system_instruction()`, `machine_turn_contract()`, and `hybrid_plan_instruction()`.
  - Significantly saves prompt token budget every turn while maintaining 100% strict polarity directives for LLM generation.

### Rules for other agents (avoid conflicts)
- Use `WARDROBE_REMOVAL_VERBS` and the centralized `WARDROBE_*_SYNONYMS` constants instead of declaring duplicate inline regexes.
- When referencing character and user anatomical descriptions in system prompts and contracts, use `CANONICAL_FEMALE_ANATOMY` and `CANONICAL_MALE_ANATOMY` to avoid token bloat.

### Verification
- `python -m py_compile server.py realmplay_features.py comfy_client.py comfy_workflows.py` passed with code 0.
- `test_router_migration.py` and `test_service_helpers.py` passed with 0 errors.
- Verified `_requested_remove_slots()` correctly distinguishes `ถอดบิกินี่ชิ้นล่างสิ`, `ถอดบิกินี่สิ`, `ถอดชุดสิ`, and `ลอกเสื้อออกจนเหลือแต่ชุดชั้นใน`.



## 2026-11-11 — Fix ComfyUI Configuration Validation (`Invalid comfy configuration`)

### What changed
- **Backend Schema Whitelist ([`realmplay_features.py`](file:///k:/RealmPlay/realmplay_features.py)):**
  - Updated the allowed keys set for `comfy` under the `/api/configuration` endpoint to include `'sam_model'`, `'emotion_categories'`, and `'rules'`.
  - Previously, saving the ComfyUI configuration from the frontend sent `sam_model` (and config.json contained `emotion_categories` / `rules`), causing `set(values) - allowed` to fail and return HTTP 422 `Invalid comfy configuration`.
- **Validation Consistency:**
  - Synchronized allowed keys across frontend serialization in [`static/features.js`](file:///k:/RealmPlay/static/features.js) and the backend endpoint schema in [`realmplay_features.py`](file:///k:/RealmPlay/realmplay_features.py).

### Rules for other agents (avoid conflicts)
- When adding new keys to `comfy` in `config.json` or `static/features.js`, always add them to the `allowed` set in `realmplay_features.py` `/api/configuration` validation.

### Verification
- `python -m py_compile realmplay_features.py server.py` passed with code 0.
- Simulated saving full configuration payloads from both `config.json` and `saveComfyConfig()`: all passed without 422 errors.
- Unit tests (`test_router_migration.py`, `test_service_helpers.py`) passed with 0 errors.



## 2026-11-11 — Image Generation Performance Restoration, SAM Model Selection & FaceDetailer Facial Pos Cleanup

### What changed
- **Image Generation Speed & SAM Optimization:**
  - Resolved root cause of workflow slowdown (>200s vs original <30s): reverted default `SAMLoader` in `data/workflows/RealmPlayADV_Default.json` and `data/workflows/RealmPlayADV_Anima.json` from `sam_vit_h_4b8939.pth` (2.56GB) to `sam_vit_b_01ec64.pth` (375MB). This eliminates heavy VRAM thrashing when FaceDetailer operates after the RTX 2.5x upscale step.
- **Adjustable SAM Model Selection (Expandable & Collapsible):**
  - Added collapsible `<details id="rp-facedetailer-settings">` section in ComfyUI settings ([`static/features.js`](file:///k:/RealmPlay/static/features.js)) containing the `SAM Model (FaceDetailer)` dropdown (`#rp-sam_model`).
  - Added dynamic options discovery from ComfyUI `/object_info/SAMLoader` in `/api/comfy/options` ([`realmplay_features.py`](file:///k:/RealmPlay/realmplay_features.py)).
  - Wired `sam_model` into `saveComfyConfig()`, `applyWorkflowPreset()`, `config.json`, and `config.example.json`.
  - Added dynamic override handling for `SAMLoader` in `compile_workflow()` ([`comfy_workflows.py`](file:///k:/RealmPlay/comfy_workflows.py)) and parameter passing in `generate_character_image()` ([`comfy_client.py`](file:///k:/RealmPlay/comfy_client.py)).
- **Full Sampler & Scheduler Synchronization:**
  - Added automatic synchronization of selected `sampler` and `scheduler` to FaceDetailer node (`45.sampler_name`, `45.scheduler`) in `compile_workflow()`, ensuring all relevant sampling nodes stay in sync.
  - Updated default `config.json` mappings to include FaceDetailer and metadata selector nodes.
- **FaceDetailer Prompt Quality Cleanup:**
  - Updated `extract_facial_identity_tags()` in [`comfy_workflows.py`](file:///k:/RealmPlay/comfy_workflows.py) to explicitly exclude full-body count/composition tokens (`1girl`, `1boy`, `2girls`, `2boys`, `solo`, `female`, `male`).
  - FaceDetailer's `Facial Pos` now receives clean facial features (hair, eyes, skin, facial characteristics) without body-level framing tags that distort face inpainting crops.

### Rules for other agents (avoid conflicts)
- Keep whole-body framing tags (`solo`, `1girl`, `1boy`, etc.) out of FaceDetailer conditioning; only facial feature tags belong in `Facial Pos`.
- For SAM models, default to base `sam_vit_b_01ec64.pth` for performance on consumer GPUs.

### Verification
- `python -m py_compile server.py comfy_client.py comfy_workflows.py realmplay_features.py` passed with code 0.
- `test_router_migration.py` and `test_service_helpers.py` passed with 0 errors.
- Verified workflow compilation with both Default and Anima workflows:
  - Node 27 successfully compiles with `sam_vit_b_01ec64.pth`.
  - Node 45 receives synchronized `sampler_name` and `scheduler`.
  - Node 36 (`Facial Pos`) retains facial features while stripping `1girl` and `solo`.



## 2026-11-11 — Streamlined Code Architecture & Crisp Instruction Precision (Code Mirroring Character)

### What changed
- **Code Clarity & Instruction Precision in [`server.py`](file:///k:/RealmPlay/server.py):**
  - Streamlined `language_adaptation_rule` for both Thai and English: directly embedded the requirement for concise speech in `"..."` and visual actions in `*...*`, removing verbose narrative framing.
  - Consolidated response rule composition in `build_system_instruction()` with `concise_presentation_rule`: zero fluff, clear directive.
  - Hardened the avoidance contract in `hybrid_plan_instruction()` to block unvisualable abstract fluff and purple prose at plan generation time.
- **Synchronized Rule Architecture:**
  - Standardized concise code and rules across `rules/character/core_embodiment.md`, `rules/nonliteral/Thai.md`, `rules/nonliteral/English.md`, `rules/language/2.Thai.md`, and `rules/language/1.English.md`.
  - The instructions mirror the exact behavior expected of the character: crisp, unambiguous, focused directly on concrete action and spoken dialogue without decorative excess.

### Rules for other agents (avoid conflicts)
- Write prompts and code with high signal-to-noise ratio: clear, imperative instructions without decorative fluff. Code style directly shapes model prompt quality and execution.

### Verification
- `python -m py_compile server.py` passed with code 0.
- All unit tests (`test_service_helpers.py`, `test_router_migration.py`) passed with 0 errors.



## 2026-11-11 — Reduce Descriptive Fluff & Focus Strictly on Speech and Observable Actions

### What changed
- **Authoritative Presentation Directives ([`rules/character/core_embodiment.md`](file:///k:/RealmPlay/rules/character/core_embodiment.md)):**
  - Updated `Observable Markup & Natural Voice` to enforce strict grounding on speech and directly visualable physical actions, gestures, and postures.
  - Mandated elimination of unnecessary descriptive words, abstract introspection, atmosphere embellishments, and flowery narrative padding.
- **Language & Non-Literal Rules ([`rules/nonliteral/Thai.md`](file:///k:/RealmPlay/rules/nonliteral/Thai.md), [`rules/nonliteral/English.md`](file:///k:/RealmPlay/rules/nonliteral/English.md), [`rules/language/2.Thai.md`](file:///k:/RealmPlay/rules/language/2.Thai.md), [`rules/language/1.English.md`](file:///k:/RealmPlay/rules/language/1.English.md)):**
  - Explicitly instructed the model to cut out decorative scene embellishments, purple prose, and descriptive padding.
  - Confined responses to audible spoken dialogue in quotes (`"..."`) and concrete, observable physical movements in asterisks (`*...*`).
- **System Instruction & Hybrid Turn Plan ([`server.py`](file:///k:/RealmPlay/server.py)):**
  - Added `concise_presentation_rule` to `[Response rules]` in `build_system_instruction()`:
    `Focus strictly on spoken dialogue in quotes and concrete, directly visualable actions in asterisks. Eliminate unnecessary descriptive words, decorative scene embellishments, purple prose, and abstract internal musings.`
  - Appended `"unnecessary descriptive words, embellishments, purple prose, or unvisualable abstract fluff"` to the EVA hybrid turn plan's `Avoid` contract list in `hybrid_plan_instruction()`.

### Rules for other agents (avoid conflicts)
- Keep all scene narration concrete and visualable. Do not inject abstract internal exposition, poetic atmospheric flourishes, or multi-clause descriptive padding.

### Verification
- `python -m py_compile server.py` passed with code 0.
- Verified `build_system_instruction()` and `hybrid_plan_instruction()` include concise presentation and avoid-fluff directives.
- `tests/test_service_helpers.py` and `tests/test_router_migration.py` passed with 0 errors.



## 2026-11-11 — Deterministic Upfront System Mechanics for Genital & Role Polarity (Zero Post-Processing)

### What changed
- **Removal of Post-Processing Regex Replacement ([`server.py`](file:///k:/RealmPlay/server.py)):**
  - Removed `enforce_genital_polarity_in_text()` from `enforce_reply_boundaries()`.
  - The system no longer performs text-munging or string regex replacements on LLM generation output for sexual anatomy.
- **Upfront Deterministic System Mechanics ([`server.py`](file:///k:/RealmPlay/server.py)):**
  - **Machine Turn Contract (`machine_turn_contract`):**
    - Expanded contract to accept `user_profile` and compute `anatomical_polarity` deterministically before planning.
    - Explicitly tags `char_is_female`, `char_role` (`receiving_partner` vs `penetrating_partner`), and `char_anatomy` vs `user_role` and `user_anatomy`.
  - **Deterministic Hybrid Reply Plan (`hybrid_plan_instruction`):**
    - Directly injects the physical role and genital polarity into the final prompt boundary instruction appended right before LLM dialogue turns:
      `- Anatomical Polarity & Body Ownership: CHAR is female (owns vagina/breasts, receiving partner). USER is male (owns penis/shaft, penetrating partner). In all actions and dialogue, maintain this polarity without confusion.`
    - Automatically appends `"confusing or inverting genital ownership between CHAR and USER"` to the plan's authoritative `Avoid` directive.
  - **Endpoints Integration:**
    - Updated `/api/chat/send` and `/api/chat/regenerate` to pass the resolved `user_prof` into `machine_turn_contract`.

### Rules for other agents (avoid conflicts)
- Do not use post-processing regex replacements on generated text to fix character confusion. Guide the generation upfront via system mechanics (`machine_turn_contract` and `hybrid_plan_instruction`).
- Output cleaning in `enforce_reply_boundaries` is reserved strictly for formatting/punctuation/delimiters, not content logic.

### Verification
- `python -m py_compile server.py` passed with code 0.
- `server.machine_turn_contract()` verified to produce correct `anatomical_polarity` dict.
- `server.hybrid_plan_instruction()` verified to inject the precise anatomical polarity and avoid directive.
- `tests/test_service_helpers.py` and `tests/test_router_migration.py` passed with 0 errors.



## 2026-11-10 — Clarify Gender & Genital Polarity between Character and User (Eliminate Genital Inversion)

### What changed
- **Explicit Biological Polarity & Genital Ownership Directive ([`server.py`](file:///k:/RealmPlay/server.py)):**
  - Added `is_user_male()` resolver to determine user gender from profile/persona (defaulting to male for heterosexual roleplay dynamics).
  - Injected an authoritative `[Anatomical Polarity & Genital Ownership]` contract into `[User]` block inside `build_system_instruction()`:
    - `{char}` (Female) -> strictly possesses Female genitalia (vagina, breasts, canal, cervix / ช่องคลอด, เนินอก) as the receiving partner. Strictly forbidden from claiming or describing possession of a penis, shaft, or balls.
    - `{user}` (Male) -> possesses Male genitalia (penis, shaft / องคชาต, ดุ้น, ลำกาย) as the penetrating partner. Strictly forbidden from attributing female genitalia to the user.
- **Rule Documents Genital Isolation ([`rules/H-mode/Thai_Female.md`](file:///k:/RealmPlay/rules/H-mode/Thai_Female.md) & [`Thai_Male.md`](file:///k:/RealmPlay/rules/H-mode/Thai_Male.md)):**
  - Added `Strict Genital Ownership Polarity` into `## NSFW Lexicon & Anatomy` in both male and female rule files.
  - Explicitly states the genital boundaries so LLMs do not confuse vocabulary lists with the character's own physical body parts.
- **Post-Processing Genital Polarity Guard ([`server.py`](file:///k:/RealmPlay/server.py)):**
  - Added `enforce_genital_polarity_in_text(text, feminine, user_male)` and integrated it into `enforce_reply_boundaries()`:
    - Replaces accidental male organs attributed to female character (e.g. `ดุ้นของฉัน` $\rightarrow$ `ดุ้นของคุณ`, `แกนกายของฉัน` $\rightarrow$ `แกนกายของคุณ`).
    - Replaces accidental female organs attributed to male user (e.g. `ช่องคลอดของคุณ` $\rightarrow$ `ช่องคลอดของฉัน`, `ร่องรักของคุณ` $\rightarrow$ `ร่องรักของฉัน`).

### Rules for other agents (avoid conflicts)
- Keep anatomical polarity explicit when prompting LLMs for erotic/H-Mode interactions.
- `enforce_genital_polarity_in_text()` automatically corrects accidental gender inversions without altering normal descriptive prose.

### Verification
- `py_compile server.py` passed with exit code 0.
- Unit test verified:
  - System prompt successfully injects `Anatomical Polarity & Genital Ownership` specifying Sable Hawthorne as Female and Player as Male.
  - Test input: `*ดุ้นของฉันกระตุกแน่นเมื่อสอดใส่เข้าไปในช่องคลอดของคุณ* "อ๊า..."` $\rightarrow$ corrected to `*ดุ้นของคุณกระตุกแน่นเมื่อสอดใส่เข้าไปในช่องคลอดของฉัน* "อ๊า..."` 100% accurately.
- `tests/test_service_helpers.py` and `tests/test_router_migration.py` passed with 0 errors.



## 2026-11-10 — Refine Clothing Removal Intent: "ถอดชุด" Only Removes Outer/Regular Clothes, Not Underwear

### What changed
- **Differentiated Removal Scope in [`server.py`](file:///k:/RealmPlay/server.py) (`_requested_remove_slots`):**
  - **Previous Behavior:** The regex rule treated any input containing `"ชุด"` (e.g. `*ถอดชุดเซเบิลออก*`, `ถอดชุด`, `ถอดชุดออก`) identically to `"ทั้งหมด"` / `"เกลี้ยง"`, which stripped all active wardrobe slots including `top_inner`, `bottom_inner`, socks, and shoes, causing unexpected full nudity.
  - **Refined Behavior:**
    1. **Total Nudity / Strip All:** Reserved strictly for explicit full stripping intents (`หมดตัว`, `ให้หมด`, `ทั้งหมด`, `ทั้งตัว`, `เปลือย`, `เกลี้ยง`, `แก้ผ้า`, `strip all`, `all`). Strips all active slots including underwear.
    2. **Underwear Sets:** Specific requests for underwear (`ชุดชั้นใน`, `กกน`, `lingerie`, `บิกินี`, `ชุดว่ายน้ำ`) target `top_inner` and `bottom_inner` only.
    3. **Outer Garment / Coats:** Specific outer requests (`ชุดตัวนอก`, `เสื้อคลุม`, `jacket`, `outerwear`) target `outer` only.
    4. **Regular Clothes / Outfits:** General outfit requests (`ถอดชุด`, `ถอดเสื้อผ้า`, `ถอดชุด<ชื่อตัวละคร>`, `outfit`, `clothes`) only remove outer and main clothing (`outer`, `top`, `bottom`), leaving innerwear (`top_inner`, `bottom_inner`) intact on the character.
    5. **Individual Pieces:** `ถอดเสื้อ` targets `top`, `ถอดกระโปรง`/`ถอดกางเกง` targets `bottom`.

### Rules for other agents (avoid conflicts)
- Do not collapse `"ชุด"` into total nudity regexes. In Thai roleplay, "ถอดชุด" means undressing the outer clothing/dress, not tearing off underwear unless explicitly asked ("ถอดหมดตัว", "ถอดทั้งหมด").

### Verification
- `py_compile server.py` passed with exit code 0.
- Unit test verified:
  - `*ถอดชุดเซเบิลออก*` $\rightarrow$ removes `['outer', 'top', 'bottom']`, underwear remains worn.
  - `ถอดชุดตัวนอกออก` $\rightarrow$ removes `['outer']`.
  - `ถอดชุดชั้นในออก` $\rightarrow$ removes `['top_inner', 'bottom_inner']`.
  - `ถอดเสื้อออก` $\rightarrow$ removes `['top']`.
  - `ถอดทั้งหมดออก` / `ถอดเสื้อผ้าออกให้หมด` $\rightarrow$ removes all active slots including underwear.
- `tests/test_service_helpers.py` and `tests/test_router_migration.py` passed with 0 errors.



## 2026-11-10 — Decoupling Multi-Piece Outfits & Underwear Sets across Existing Characters & Catalog

### What changed
- **Wardrobe Catalog Underwear Decoupling ([`data/wardrobe_catalog.json`](file:///k:/RealmPlay/data/wardrobe_catalog.json)):**
  - Decoupled two-piece set items in `top_inner` and `bottom_inner`:
    - `top_inner`: Stripped paired bottom clauses (e.g. `and matching panties`, `with high-cut Brazilian panties`, `with cheeky bottoms`) from 95 set items. Retained only the upper-body garment (bralette, bra, camisole, bikini top).
    - `bottom_inner`: Stripped paired top clauses (e.g. `Lace bralette with...`, `Velvet plunge bra with...`, `Cotton bra with...`). Retained only the lower-body garment (panties, thong, boyshorts, briefs).
    - Deduplicated entries: `top_inner` (249 clean items), `bottom_inner` (150 clean items).
  - Created backup at `data/wardrobe_catalog.json.bak_underwear`.
- **Character Data Migration ([`migrate_wardrobe_decoupling.py`](file:///k:/RealmPlay/migrate_wardrobe_decoupling.py)):**
  - Automated deep migration across all user profiles and characters in `users/`:
    - `outfits.json`: Decoupled compound outfits across slots (`top_inner`, `bottom_inner`, `top`, `head_acc`, `neck_acc`).
    - `wardrobe_inventory.json`: Decoupled compound wardrobe inventory items to match.
    - `turn_metadata.json`: Updated active datablocks and turn history snapshots to ensure prompt generation uses the clean, single-piece garment prompts.
  - Specifically migrated items such as:
    - `"Cute animal ear lace bralette with a fluffy tail accent and matching panties"` $\rightarrow$ `top_inner`: `"Cute animal ear lace bralette with a fluffy tail accent"`.
    - `"Striped bikini panties with a satin finish"` $\rightarrow$ `bottom_inner`: `"Striped bikini panties"`.
    - Miscategorized full outfits in `head_acc` / `neck_acc` replaced with clean accessories.
  - Successfully migrated 67 files across all characters.

### Rules for other agents (avoid conflicts)
- All wardrobe slots (`top`, `bottom`, `top_inner`, `bottom_inner`, `accessories`) are strictly single-piece.
- Never add items that describe both a top and a bottom into a single slot. Characters wear, remove, or swap items per individual slot.

### Verification
- `py_compile server.py migrate_wardrobe_decoupling.py` passed with exit code 0.
- Verified Sable Hawthorne and other characters:
  - `top_inner` is `"Cute animal ear lace bralette with a fluffy tail accent"` (no panties attached).
  - `bottom_inner` is `"Striped bikini panties"` (no bra attached).
- `data/wardrobe_catalog.json` validated: 0 remaining compound bra/panties combinations in `top_inner`.
- All tests in `tests/test_service_helpers.py` and `tests/test_router_migration.py` passed with 0 errors.



## 2026-11-10 — Fix Weather/Feeling "หนาว" Erroneously Sanitized to "ร้อนผ่าว"

### What changed
- **Refined Intimacy Coldness Sanitizer ([`server.py`](file:///k:/RealmPlay/server.py)):**
  - Removed overzealous replacement rules in `_sanitize_cold_intimacy()` that replaced `หนาว`, `หนาวมาก`, `หนาวจัง`, `เย็นจัง`, and `รู้สึกเย็น` with `ร้อนผ่าว` / `อุ่นจังเลย`.
  - Preserved natural weather and general physical sensations of coldness (e.g., "อากาศหนาวมาก", "หนาวจัง", "รู้สึกหนาว").
  - Retained strict protection only against unnatural necrophilic touch descriptions (`สัมผัสที่เย็นเฉียบ`, `เย็นเฉียบ`, `เย็นยะเยือก`).

### Rules for other agents (avoid conflicts)
- Do not add broad keyword replaces for `หนาว` or `เย็น` in post-processing boundaries. Roleplay often involves climate, temperature, and environment details that must not be rewritten.

### Verification
- `py_compile server.py` passed with exit code 0.
- Unit test verified:
  - `"วันนี้อากาศหนาวมาก หนาวจังเลย ฉันรู้สึกหนาวจนตัวสั่น"` remains completely unchanged (0 replacements).
  - Intimate touch `"สัมผัสที่เย็นเฉียบ"` is safely sanitized as intended.
- `python -m unittest discover -s tests -p "test_service_helpers.py"` and `test_router_migration.py` passed with 0 errors.



## 2026-11-10 — Strict Thai Female Pronoun Enforcement & "ผม" / "ครับ" Prevention

### What changed
- **Prompt Injection & Negative Constraint ([`rules/linguistic/Thai_Female.md`](file:///k:/RealmPlay/rules/linguistic/Thai_Female.md) & [`server.py`](file:///k:/RealmPlay/server.py)):**
  - Updated `## Absolute Isolation Rule` in `Thai_Female.md` with strict negative directive forbidding female characters from using masculine 1st-person pronouns "ผม" / "กระผม" and masculine particles "ครับ", mandating female pronouns ("ฉัน", "ชั้น", "เรา", "เค้า", "หนู", or name).
  - Fixed `_dynamic_linguistic_nodes()` in `server.py` to inject `[Absolute Gender & Pronoun Isolation]` into the prompt.
  - Removed outdated rejection pattern `(?<![\u0E00-\u0E7F])(?:ฉัน|ดิฉัน)(?![\u0E00-\u0E7F])` in `generate_nonrepeating_reply()` retry check which was inadvertently penalizing "ฉัน" and forcing models to output "ผม".
- **Hair-Safe Post-Sanitizer ([`server.py`](file:///k:/RealmPlay/server.py)):**
  - Added `_THAI_HAIR_COMPOUNDS` and `enforce_female_thai_speech(text, feminine)`: safely masks compound hair words (`เส้นผม`, `ปลายผม`, `ผมยาว`, `ผมสยาย`, `ปอยผม`, etc.), converts masculine particles (`ครับ`, `นะครับ`, `ครับผม`, `คร้าบ`) to female particles (`ค่ะ`, `นะคะ`, `ค่า`), replaces accidental 1st-person pronoun "ผม" with "ฉัน", and restores the compound hair tokens intact.
  - Added global helper `is_character_female(summary_text, card_dict, base_dict)`.
  - Wired `feminine=is_char_fem` across `enforce_reply_boundaries()` in `/api/chat/send`, `/api/chat/regenerate`, and `emit_proactive_message()`.

### Rules for other agents (avoid conflicts)
- Male characters (`Thai_Male.md`) and female characters (`Thai_Female.md`) have isolated linguistic rules.
- Do not add rules prohibiting "ฉัน" or "ดิฉัน" for Thai responses in LLM retry handlers.
- `enforce_female_thai_speech()` only operates when `feminine=True`, ensuring male characters are not altered.

### Verification
- `py_compile server.py` passed with exit code 0.
- Unit test verified:
  - Female: `"ผมคิดถึงคุณจังเลยครับ" *สะบัดผมยาว ปลายผมสีเงินสยาย* "ผมมีความสุขมากครับผม"` -> converted to `"ฉันคิดถึงคุณจังเลยค่ะ" *สะบัดผมยาว ปลายผมสีเงินสยาย* "ฉันมีความสุขมากค่ะ"`. Hair words preserved with 100% accuracy.
  - Male: `"ผมชื่อแวนซ์ครับ" *ลูบปลายผมเบาๆ* "ผมยินดีที่ได้รู้จักครับผม"` -> untouched.
  - Gender detection correctly resolves female/male from summaries and cards.
- `python -m unittest discover -s tests -p "test_service_helpers.py"` and `test_router_migration.py` passed with 0 errors.



## 2026-11-10 — Multilingual Character Name Translation & Self-Recognition

### What changed
- **Multilingual Name Translation Engine (`server.py`):**
  - Added `COMMON_CHARACTER_NAME_TRANSLATIONS` catalog and `resolve_character_name_in_language(name, language)` function to automatically translate English character names and surnames into the user's active language (Thai, Japanese, Simplified Chinese, French, Spanish).
  - Handles all registered catalog characters (e.g. `Aria` -> `อาเรีย`, `Sable Hawthorne` -> `เซเบิล ฮอว์ธอร์น`, `Aveline Silverbrook` -> `อเวลีน ซิลเวอร์บรู๊ค`, `Vance` -> `แวนซ์`, etc.).
- **Self-Recognition & Language Adaptation Integration (`server.py`):**
  - In `build_system_instruction()`, augmented `[Self-recognition]` with the character's translated native alias:
    `- Identity: {char} (Native / translated name in {Language}: '{char_native_alias}' — recognize and respond naturally when addressed by this name)`.
  - Added explicit multilingual name recognition directives in `[Language adaptation]` for Thai, Japanese, Chinese, French, and Spanish: characters recognize and respond in character when the user refers to them by either their native/translated name or their original English name.

### Rules for other agents (avoid conflicts)
- When adding new characters with English names, their localized counterparts can be registered in `COMMON_CHARACTER_NAME_TRANSLATIONS` in `server.py` so prompt self-recognition and language adaptation auto-wire immediately.

### Verification
- `py_compile server.py` passed with exit code 0.
- Verified prompt construction across multiple languages:
  - Thai: `Aria` resolves to `อาเรีย`, `Sable Hawthorne` resolves to `เซเบิล ฮอว์ธอร์น`.
  - Japanese: `Aria` resolves to `アリア`.
  - Chinese: `Aria` resolves to `阿丽亚`.
  - All verified with 100% assertions passing.
- `python -m unittest discover -s tests -p "test_service_helpers.py"` and `test_router_migration.py` passed with 0 errors.



## 2026-11-10 — Complete 2-File Gender Isolation for H-Mode Behavior, Physiology & Vocalizations (`Thai_Female.md` & `Thai_Male.md`)

### What changed
- **Split Thai H-Mode Behavioral & Physiological Rules into 2 Dedicated Files:**
  - Created [`rules/H-mode/Thai_Female.md`](file:///k:/RealmPlay/rules/H-mode/Thai_Female.md): exclusively contains Female Persona Dynamics, sweet and breathless TTS moan vocalizations (`อ๊ะ...`, `อ๊า!`, `อ๊าง...`, `อย๊า!`, `อื้อ!`, `ฮึก...`), female autonomous body reflexes (vaginal clenching, arching spine, shivering lower abdomen), and female climax responses. Stripped of all male persona/reflex directives.
  - Created [`rules/H-mode/Thai_Male.md`](file:///k:/RealmPlay/rules/H-mode/Thai_Male.md): exclusively contains Male Persona Dynamics, deep raspy TTS moans and growls (`อึก...`, `อืมม์...`, `ฮึ่ม...`, `ซี๊ด...`), masculine autonomous body reflexes (throbbing shaft, bulbar/prostatic contractions, pinning hips), and male climax responses. Stripped of all female persona/reflex directives.
- **Dynamic Gender Routing in [`server.py`](file:///k:/RealmPlay/server.py):**
  - Updated `_h_mode_neural_network_nodes(language: str, feminine: bool = True)` to select `H_MODE_BEHAVIOR_RULE_FILES["female"]` or `["male"]` based on character gender.
  - Updated `language_use_rule_block` to pass `feminine=feminine` to `_h_mode_neural_network_nodes`.
  - Fixed Moan section resolution to match full title `moan (nsfw) & tts vocalization — โหมดกระเส้ารัญจวน (sensual & arousing architecture)`.

### Rules for other agents (avoid conflicts)
- Edits to H-Mode female behaviors, moans, or reflexes must be made in [`rules/H-mode/Thai_Female.md`](file:///k:/RealmPlay/rules/H-mode/Thai_Female.md).
- Edits to H-Mode male behaviors, moans, or reflexes must be made in [`rules/H-mode/Thai_Male.md`](file:///k:/RealmPlay/rules/H-mode/Thai_Male.md).
- Both files maintain the exact section headers so node parsers and EVA set algebra work seamlessly.

### Verification
- `py_compile server.py` passed with exit code 0.
- Verified `_h_mode_neural_network_nodes` and `language_use_rule_block` prompt generation:
  - Female characters load `Thai_Female.md` with 0% Male Persona / Reflex leakage.
  - Male characters load `Thai_Male.md` with 0% Female Persona / Reflex leakage.
- `python -m unittest discover -s tests -p "test_service_helpers.py"` and `test_router_migration.py` passed with 0 errors.



## 2026-11-10 — Complete 2-File Gender Linguistic Rule Isolation (`Thai_Female.md` & `Thai_Male.md`)

### What changed
- **Split Thai Linguistic Directives into Dedicated Files:**
  - Created [`rules/linguistic/Thai_Female.md`](file:///k:/RealmPlay/rules/linguistic/Thai_Female.md) with absolute female-only speech directives, polite and sweet ending particles (`ค่ะ`, `คะ`, `นะคะ`, `จ้ะ`, `จ๊ะ`, `จ๋า`), and female relationship progression pronouns. Strictly prohibits masculine ending particles.
  - Created [`rules/linguistic/Thai_Male.md`](file:///k:/RealmPlay/rules/linguistic/Thai_Male.md) with absolute male-only speech directives, polite and masculine ending particles (`ครับ`, `นะครับ`, `คร้าบ`, `ขอรับ`, `พ่ะย่ะค่ะ`), and male relationship progression pronouns. Strictly prohibits feminine ending particles.
- **Dynamic File Routing in [`server.py`](file:///k:/RealmPlay/server.py):**
  - Updated `_dynamic_linguistic_nodes()` so that when `language == "thai"`, it routes directly to `Thai_Female.md` if `feminine` is True, or `Thai_Male.md` if `feminine` is False.
  - Ensures each character activates ONLY the single file matching their gender (0 token overhead, 0% cross-gender prompt leakage).
  - Falls back cleanly to `rules/linguistic/Thai.md` if custom files are absent.

### Rules for other agents (avoid conflicts)
- Edits to Thai linguistic directives for female characters must be made in [`rules/linguistic/Thai_Female.md`](file:///k:/RealmPlay/rules/linguistic/Thai_Female.md).
- Edits to Thai linguistic directives for male characters must be made in [`rules/linguistic/Thai_Male.md`](file:///k:/RealmPlay/rules/linguistic/Thai_Male.md).
- Do not merge female and male directives into a single file or re-introduce cross-gender examples into shared headers.

### Verification
- `python -m py_compile server.py` succeeded with exit code 0.
- Verified character prompt generation via `_dynamic_linguistic_nodes`:
  - Female characters load `Thai_Female.md` with `[Feminine Particles]` (`ค่ะ`, `คะ`, `นะคะ`, etc.) and 0% masculine particle contamination.
  - Male characters load `Thai_Male.md` with `[Masculine Particles]` (`ครับ`, `นะครับ`, etc.) and 0% feminine particle contamination.
- `python -m unittest discover -s tests -p "test_service_helpers.py"` and `test_router_migration.py` passed with 0 errors.



## 2026-11-10 — Absolute Character Gender Speech & Linguistic Isolation (Note for other agents)

### What changed
- **Linguistic Neural Node Isolation (`rules/linguistic/Thai.md`):**
  - Completely separated and restored female and male particle sections (`Ending Particles Female` vs `Ending Particles Male`) to match the multi-lingual standard used across Japanese, Chinese, French, and Spanish.
  - Female characters strictly receive feminine polite & sweet particles (`ค่ะ`, `คะ`, `นะคะ`, `จ้ะ`, `จ๊ะ`, `จ๋า`) and female relationship progression pronouns.
  - Male characters strictly receive masculine polite & sweet particles (`ครับ`, `นะครับ`, `คร้าบ`, `นะครับผม`) and male relationship progression pronouns (`ผม`, `พี่`, `เรา`). Male characters strictly forbid female particles.
- **Robust Gender Extraction & Prompt Isolation (`server.py`):**
  - Enhanced gender detection (`_resolve_char_is_female`) to check the explicit `## Gender` section in `Char_Summary.md`, card metadata, and baseline definitions directly instead of relying solely on general keyword scanning.
  - System instruction language adaptation now isolates Thai period punctuation examples (`สวัสดีค่ะ` for female vs `สวัสดีครับ` for male), completely preventing cross-gender particle contamination.

### Rules for other agents (avoid conflicts)
- When adding or editing linguistic rule files (`rules/linguistic/*.md`), keep `## Ending Particles Female` and `## Ending Particles Male` headers intact. `_dynamic_linguistic_nodes()` in `server.py` relies on these exact headers to dynamically inject matching particles for the character's gender.

### Verification
- Automated assertions verified that male characters receive `[Masculine Particles]` and `สวัสดีครับ` with 0% female particle leakage, and female characters receive `[Feminine Particles]` and `สวัสดีค่ะ` with 0% male particle leakage.
- `py_compile server.py` and `python -m unittest discover -s tests -p "test_service_helpers.py"` passed.

## 2026-11-10 — Router migration step 1: status + discovery (note for other agents)

### What changed
- NEW `app/wiring.py`: single place that attaches migrated routers (`include_migrated_routers(app, deps)`) and `MIGRATED_PATHS` list. **Add future migrated routers here instead of editing `server.py`.**
- `server.py` (backup of previous file: `tmp/server.py.pre-router.bak`):
  - Removed ONLY the 3 decorator lines for `/api/status/all`, `/api/chat/context_usage`, `/api/models/list`. The functions `get_all_status`, `chat_context_usage`, `list_available_models` stay in place, unchanged, and are now served through `app/routers/status.py` and `app/routers/discovery.py`.
  - Added one `include_migrated_routers(app, {...})` call immediately before `import realmplay_features` (end of file, after all handlers are defined).
- NEW `tests/test_router_migration.py` (2/2 pass): each migrated path is registered exactly once and callable; `server.py` no longer decorates migrated paths.

### Rules / warnings for other agents
- Do NOT re-add `@app.get("/api/status/all")`, `/api/chat/context_usage`, or `/api/models/list` to `server.py` (would duplicate the route; the test fails if you do).
- Editing the bodies of those three functions in `server.py` is still fine.
- To migrate another endpoint: delete its decorator, add it in `app/wiring.py` + `MIGRATED_PATHS`, run `tests/test_router_migration.py`. One endpoint group at a time.
- NOT migrated on purpose: `/api/image/generate` (router uses `app.schemas.system.GenerateImageRequest`; verify it matches the server's model first) and all chat/character/wardrobe routes (large handlers, other agents active in them).

### Verification
- `py_compile` OK; `import server` succeeds in a subprocess and OpenAPI lists all 3 paths (plus `/api/chat/send`). Pre-existing FastAPI "Duplicate Operation ID" warnings (`chat_edit_image_prompt`, `get_chat_display_settings`) are unrelated to this patch.
- Not tested against the running server: restart required to load.

### Pending
- Next candidates, smallest first: `inventory`, `wardrobe`, `voice`, `tunnel`, `catalogs` routers (check each handler signature against its router, as done here).

## 2026-11-10 — Memory token budget + persisted rolling summary (note for other agents)

### What changed
- NEW `rolling_summary.py` (root): per user+character summary stored in `users/<user>/<char>/rolling_summary.json` (`summary`, `covered`, `fingerprint`). Summarizes only turns older than the newest 4 messages, incrementally (>=600 uncovered tokens, <=2 batches of 10 messages per refresh). Resets automatically if history was edited/deleted/reset (fingerprint of last covered message). Never recreates a deleted character folder. Summarizer is injected (no LLM dependency in the module).
- `server.py` (4 small edits, backup of the previous file: `tmp/server.py.pre-rolling.bak`):
  1. `import rolling_summary` next to `import character_card`.
  2. `prune_memory_facts(..., token_budget=0)`: new optional arg; drops lowest-scoring WHOLE facts until under budget (keeps at least one). `route_context_nodes` now passes `token_budget=mem_char_cap`.
  3. `build_system_instruction`: if `context_summary` is empty, loads the persisted rolling summary (previously `context_summary` was never passed by any caller, so the "Prior Context Summary" block was always empty).
  4. New `_schedule_rolling_summary(...)` (defined just above `summarize_bloated_context`) and a call to it in `chat_send` right after `save_user_character_state`/`chat_inbox.receipt`. It runs `summarize_bloated_context` in a background thread via `asyncio.create_task`; failures are logged and ignored, the reply is never blocked.
- NEW tests: `tests/test_rolling_summary.py` (5/5 pass; run with `PYTHONPATH=K:\RealmPlay python tests\test_rolling_summary.py`).

### Rules / warnings for other agents
- `summarize_bloated_context` is now actually used (one LLM call of <=200 tokens per refresh; it competes with chat for the local LLM). If this causes latency, raise `TRIGGER_TOKENS` in `rolling_summary.py`.
- Only `chat_send` schedules refresh. `chat_regenerate` / `chat_continue` / proactive only READ the summary.
- H-Mode behavior unchanged: existing code still hides the summary during active H-Mode unless the user asks about the past.
- Restart the server (`start_realmplay.bat`) to load this; it runs without `--reload`.

### Verification
- `py_compile` OK for `server.py`, `rolling_summary.py`; unit tests pass (5/5 new). Not run against the live server/LLM.

### Pending
- Hook refresh into regenerate/continue if wanted; add a Memory Inspector view of the rolling summary; consider shrinking `build_bounded_history` default window (3 msgs) only after observing summary quality.

## 2026-11-10 — Memory helpers: wiring decision (note for other agents)

- Re-read `server.py` before integrating: `prune_memory_facts` there (line ~3713) already does keyword + Thai n-gram overlap + importance + recency. It supersedes `select_memories` in `app/services/memory_context.py`, so `select_memories` was NOT wired in (avoids two competing selectors).
- `server.py` was NOT modified in this step.
- Still unused/available: `plan_rolling_summary` and `merge_summary` (for `summarize_bloated_context`, which currently has no persisted rolling summary or token trigger), and a token-budget cap on selected facts (`prune_memory_facts` limits by count only).
- Pending: if wanted, add a token budget to `prune_memory_facts` and a persisted per-user+character summary; coordinate before touching `server.py`.

## 2026-11-10 — Memory & context helpers (note for other agents)

### What changed
- New pure module `app/services/memory_context.py`:
  - `select_memories(memory_text, query, token_budget, max_facts)` — relevance-ranked (word + character-bigram overlap, so Thai works) with a small recency boost, bounded by token budget, original order preserved.
  - `plan_rolling_summary(history, keep_recent, trigger_tokens)` — decides whether older turns need summarizing.
  - `merge_summary(previous, new_part, max_chars)` — capped rolling summary.
- New tests: `tests/test_memory_context.py` (5/5 pass; run with `PYTHONPATH=K:\RealmPlay python tests\test_memory_context.py`).

### Rules for other agents
- `server.py`, `character_card.py` and `app/services/context_utils.py` were NOT touched. The module is not wired in yet.
- Existing related code to integrate with later: `route_context_nodes` and `summarize_bloated_context` in `server.py`, `prune_memory_facts` in `context_utils.py`. Coordinate before editing `server.py`.

### Verification
- Unit tests only; no live-server check.

### Pending
- Replace `prune_memory_facts` (newest-N) with `select_memories` inside `route_context_nodes`.
- Feed `plan_rolling_summary` into `summarize_bloated_context` and persist the merged summary per user+character.

## 2026-11-10 — Wardrobe Catalog Option A: Tops and Bottoms Decoupling (Note for other agents)

### What changed
- Cleaned and decoupled `data/wardrobe_catalog.json` for slot `top` to enable independent mix-and-match styling:
  - Stripped paired bottom/footwear clauses (e.g. `paired with skinny jeans`, `tucked into a pleated skirt with ankle boots`, `with leather leggings`) from 115 sweater/top items.
  - Reclassified 9 pure bottom items that were miscategorized under `top` (e.g. `Textured knit skirt`, `Ribbed knit leggings`, `Textured knit wide-leg pants`) into slot `bottom`.
  - Deduplicated resulting normalized names within `top` (now 425 clean tops) and `bottom` (now 66 bottoms).
- Backup saved at `data/wardrobe_catalog.json.bak`.

### Rules for other agents (avoid conflicts)
- When generating or managing wardrobe slots, `top` prompts no longer bleed bottom-half clothing into image prompts. Characters can now wear or remove `top` and `bottom` independently without prompt leakage.

### Verification
- `data/wardrobe_catalog.json` syntax and JSON decoding validated.
- Zero remaining bottom keywords found in `data/wardrobe_catalog.json` `top` slot.
- Unit test suite `tests/test_service_helpers.py` passed (2/2).

## 2026-11-10 — EVA-Style Mechanics & Logic Set Engine Integration (Note for other agents)

### What changed
- **Set Algebra & Logical Operators Engine (`logic_set_engine.py`):**
  - Added native `OrderedTagSet` supporting set operations (`union`, `intersection`, `subtract`, `diff`, `complement`) and logical operators (`evaluate_if_elif_else`, `logic_and`, `logic_or`, `logic_not`).
  - Integrated into `server.py` context gating and `visual_state_engine.py` tag diffing.
- **Autonomous Personal Logic (`character_logic.py` & `rules/character/core_embodiment.md`):**
  - Replaced assistant-style planning with deterministic humanoid logic (`IF -> CAUSE -> THEN`).
  - Added `ELIF_INTENTIONAL_NEGOTIATION_PACT` allowing intentional character questions based on internal agency rather than trailing bot questions.
  - Strips service-bot boilerplate via `strip_assistant_bot_phrases`.
- **Compromised & Threshold-Triggered Context Gating (`server.py`):**
  - Gated system/story time, location, and deep background summaries so they only inject when thresholds are met (first message of the day, tired/sleepy state, or direct user inquiry).
  - During active H-Mode scenes, suppresses story opening anchors, origin backstories, and non-essential memories to save context tokens.
- **Bilingual & Multi-Language Isolation:**
  - System core prompt and character embodiment directives are kept in 100% universal English (0% Thai character leakage for non-Thai chats).
  - Thai idiomatic guidance (`meaning-first` like "เป็นตัวของตัวเอง") and specific ending particles are isolated exclusively to `rules/language/2.Thai.md` and `rules/linguistic/Thai.md`.
- **Facial Identity & Eye Color Injection:**
  - `comfy_workflows.py` and `comfy_client.py` now extract eye color directly from character appearance and merge into `EMOTION` / FaceDetailer tags via `OrderedTagSet.union()`.

### Rules for other agents (avoid conflicts)
- **Do not blindly overwrite `server.py`, `character_logic.py`, or `logic_set_engine.py` without checking latest git diff.**
- **Developer documentation:** Any architectural or system-writer notes must go to `rules/coder_system_writer/*.md` (which are strictly excluded from LLM prompts to preserve token budgets), NOT into `rules/character/*.md`.
- **Testing:** Verify changes with existing test suites:
  - `python tests\test_service_helpers.py`
  - Scratch verification scripts in brain folder if needed.

### Verification
- `py_compile` passed for all modified modules (`server.py`, `character_logic.py`, `logic_set_engine.py`, `visual_state_engine.py`, `comfy_workflows.py`, `comfy_client.py`).
- Automated tests for Set operations, Personal Logic, Context Gating, and Thai/English language isolation all passed.

## 2026-11-10 — Frontend JS extraction and standalone service helpers (note for other agents)

### What changed
- The single inline `<script>` block in `static/index.html` moved verbatim to `static/js/app_main.js` (~5,700 lines). `index.html` now loads it via `<script src="/static/js/app_main.js?v=20261110-modular">` at the same position, before `features.js` and `node_editor.js`.
- New standalone helpers (not yet called from `server.py`):
  - `app/services/audio_manager.py` — `cache_stats()`, `prune_audio_cache(dir, max_age_hours, max_total_mb)`.
  - `app/services/prompt_sanitizer.py` — `sanitize_prompt(prompt, removed_terms)`.
- New tests: `tests/test_service_helpers.py` (run: `set PYTHONPATH=K:\RealmPlay` then `python tests\test_service_helpers.py`).
- Backup of the pre-change page: `static/index.html.pre-modular.bak` (safe to delete once verified).

### Rules for other agents (avoid conflicts)
- **Edit frontend logic in `static/js/app_main.js`, NOT in `index.html`.** Inline JS no longer exists there; any edit still targeting the old inline block will not apply. Do not restore the backup over `index.html`.
- When you change `app_main.js`, bump the `?v=` query in `index.html` so browsers reload it.
- `server.py` was NOT touched. Backend logic files (`logic_set_engine.py`, `character_logic.py`, `visual_state_engine.py`, `comfy_*.py`) were NOT touched.
- `app/routers/` and `app/services/` are still not imported by `server.py` (partial migration from 2026-10-24). Do not wire routers in while others are editing `server.py`; coordinate first and migrate one router at a time with `py_compile` after each.

### Verification
- `node --check static/js/app_main.js` passed; `py_compile` passed for core modules; helper tests passed (2/2).
- Not yet verified in a browser: do a hard refresh and confirm chat, image, and TTS UI still work.

### Next (pending a quiet window on `server.py`)
- Hook audio pruning and the prompt sanitizer into `server.py`.
- Incrementally include `app/routers/*`.

## 2026-10-29 — Wardrobe state transaction and action handling

### State consistency

- Wardrobe changes now follow one chat-turn commit path.
- The wardrobe interpreter changes only in-memory state first.
- At the end of a successful chat or regenerate turn, the system persists the live state and the matching history record together.
- A wardrobe transition now updates the current outfit state, character inventory, wardrobe inventory, `current_datablock`, and the relevant assistant turn record from the same final state.
- Direct edits to `outfits.json` are not a supported way to change a live character state. Runtime state is persisted through the state writer and synchronized with the data-block table.

### Current state and historical records

- `current_datablock` represents the character's current live state for the next turn and current UI.
- `turn_records` retain the state for each individual message, including the wardrobe used by that message's image generation, regeneration, and rollback.
- A USER wardrobe action is applied before the USER turn snapshot is made.
- A CHAR wardrobe action is applied after the reply is interpreted and before the assistant turn snapshot is made.

### Wardrobe interaction

- `WardrobeTransition` is the single mutation path for USER actions, CHAR actions, regenerate, and the UI fallback toggle.
- Inventory equip/unequip, catalog-item equip, and preset application now also use `WardrobeTransition`; they no longer mutate active slots separately.
- It owns slot activation, naked-state synchronization, wardrobe inventory updates, and returning removed items to the character bag.
- An active pants/shorts/jeans/trousers `bottom` layer blocks removal of `bottom_inner`. Remove the outer bottom layer first, or remove both layers in one transition.
- USER may request that CHAR wear or remove an item using quoted or plain speech.
- USER may perform a completed wardrobe action using `*...*`; the action is applied before the reply is generated.
- Requests support item names and the following slot groups: outer, top, bottom, top inner, bottom inner, outfit, and underwear set.
- When CHAR accepts a specific wardrobe request, the reply must complete the requested change in that turn rather than partially performing it or asking for repeated confirmation.
- With Auto Wardrobe enabled, completed marked CHAR removal actions also synchronize the matching active slot.
- The interpreter recognizes completed removal wording such as a garment being pulled or slid off, including Thai wording equivalent to pulling a skirt free.

### Image continuity

- Image prompts use active outfit slots only.
- The image attached to a chat bubble uses that bubble's turn record rather than later wardrobe changes.
- A removed item is not sent as active attire in later image prompts.

### Verification

- Python syntax validation passed for `server.py`, `character_card.py`, and `turn_metadata.py`.
- Wardrobe request regression tests passed.
- An in-memory transaction test confirmed that one removal updates both `current_datablock` and the assistant turn record with the same outfit state.

## 2026-10-29 — Chat inbox notification and recency ordering

- The character list now uses the greatest message timestamp in each history, rather than assuming its last array entry is the newest message.
- The list refreshes immediately after send, regenerate, and continue, so the latest conversation moves to the top without waiting for the presence poll.
- New unread character messages show an in-app SMS-style alert and chime. When the player permits browser notifications, a background tab also receives a native notification.
- Existing unread badges are used as the initial baseline and do not trigger a false new-message alert at page load.
