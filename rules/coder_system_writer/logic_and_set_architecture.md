# 🛠️ System Writer & Coder Architecture Guide (`rules/coder_system_writer/`)
> **SYSTEM / DEVELOPER DOCUMENTATION ONLY — NEVER INJECTED INTO CHARACTER LLM PROMPTS**

เอกสารฉบับนี้เป็นคู่มือสถาปัตยกรรมสำหรับ **นักพัฒนา (Coder / System Writer)** เพื่อใช้อ้างอิงกลไกการคำนวณของเอนจินฝั่งเซิร์ฟเวอร์ (`server.py`, `logic_set_engine.py`, `visual_state_engine.py`, `comfy_workflows.py`, `comfy_client.py`) เอกสารในโฟลเดอร์ `rules/coder_system_writer/` ถูกแยกออกจาก `rules/character/` อย่างเด็ดขาดเพื่อ **ไม่ให้ถูกโหลดเข้าสู่ System Prompt ของตัวละคร (Zero Token Overhead)**

---

## 1. การแยกชั้นเอกสาร Markdown (Strict Separation of Concerns)

| หมวดหมู่โฟลเดอร์ | ผู้ใช้งานเป้าหมาย (Target Audience) | ถูกฉีดเข้า LLM Context หรือไม่? | หน้าที่หลัก |
| :--- | :--- | :--- | :--- |
| **`rules/coder_system_writer/`** | นักพัฒนา / System Writer / Backend Engine | ❌ **ไม่ถูกฉีดเด็ดขาด (0 tokens)** | อธิบายสูตร Set Algebra, Logical Operators, Context Router, โครงสร้าง State Block และ ComfyUI Pipeline |
| **`rules/character/`** | ตัวละคร AI (Character Runtime Persona) | ✅ **ฉีดเฉพาะโหนดที่ Active** | กฎการสวมบทบาทของตัวละคร (POV, การแสดงอารมณ์, ปฏิกิริยาร่างกาย, การพูดและการกระทำที่กระชับประหยัด Context) |

---

## 2. ตัวดำเนินการทางตรรกศาสตร์ (Logical Operators) ใน [`logic_set_engine.py`](file:///k:/RealmPlay/logic_set_engine.py)

| ตัวดำเนินการ (Operator) | สัญลักษณ์ | ฟังก์ชันใน Python | ความหมายเชิงตรรกะใน `server.py` |
| :--- | :--- | :--- | :--- |
| **`IF / ELIF / ELSE`** | $\text{IF } P \Rightarrow Q$ | `logic_if_else()`, `evaluate_if_elif_else()` | เลือกสาขากฎหรือขนาด Context Budget ตามเงื่อนไขของเทิร์น |
| **`AND`** | $P \land Q$ | `logic_and()` | เงื่อนไขร่วม: ต้องพบคำสำคัญครบทุกตัวในคู่คำ (`and_conditions` ได้ `+15` คะแนน) |
| **`OR`** | $P \lor Q$ | `logic_or()` | เงื่อนไขเลือก: พบคำสำคัญตัวใดตัวหนึ่งใน `or_keywords` (`+10` คะแนน) |
| **`NOT`** | $\neg P$ | `logic_not()` | Complement Guard: หากพบคำใน `not_keywords` จะตัดคะแนนโหนดเป็น `0` ทันที |

---

## 3. ตัวดำเนินการทางทฤษฎีเซต (Set Operations) ใน `OrderedTagSet`

ประมวลผลผ่านคลาส [`OrderedTagSet`](file:///k:/RealmPlay/logic_set_engine.py#L28-L148):

1. **`UNION` ($A \cup B$)** — `A.union(B)` หรือ `A | B`:
   - รวมแท็ก `Posture ∪ SecondaryAction ∪ ClothingDisplacement` ใน `visual_state_engine.py`
   - รวมสีตาจาก `Appearance` เข้ากับ `EMOTION` (`EmotionPreset ∪ CharacterEyeColor`) สำหรับ `FaceDetailer`
2. **`INTERSECTION` ($A \cap B$)** — `A.intersection(B)` หรือ `A & B`:
   - คำนวณคำค้นหาร่วมระหว่างบริบทผู้เล่นกับความทรงจำ `(QueryUnits ∩ MemoryFactUnits)`
   - คัดกรองเฉพาะแท็กใบหน้า `(Appearance ∪ Positive) ∩ FACE_IDENTITY_KEYWORDS`
3. **`SUBTRACT / DIFFERENCE` ($A \setminus B$)** — `A.subtract(B)` หรือ `A - B`:
   - ลบแท็กเสื้อผ้าที่ถูกถอดออกแล้วออกจาก Image Seed (`VisualTags \ RemovedWardrobePrompts`)
   - ลบส่วนของกฎ H-Mode ที่เป็นคนละช่องทางสัมผัสออกจาก Prompt (`RuleParts \ InactiveChannelKeywords`)
4. **`DIFF / SYMMETRIC_DIFF` ($A \triangle B$)** — `A.diff(B)` หรือ `A ^ B`:
   - หาช่องเสื้อผ้าที่มีการเปลี่ยนแปลงในเทิร์นนั้น (`BeforeActiveSlots ^ AfterActiveSlots`)
5. **`COMPLEMENT` ($A^c = U \setminus A$)** — `A.complement(U)`:
   - หาโหนดบริบทที่ถูกตัดออกเพื่อประหยัด Context (`UniverseNodes \ ActiveNodes`)
   - หาเสื้อผ้าที่ถูกถอดออกเทียบกับชุดที่ตัวละครมี (`DefinedSlots \ ActiveSlots`)

---

## 4. กลไกประหยัด Context ใน `server.py` (Context-Saving Routing)

1. **Adaptive Memory Pruning (`route_context_nodes`)**:
   - `IF selected_intent("memory")`: ดึงความทรงจำสูงสุด `5` ข้อ (งบ `520` ตัวอักษร)
   - `ELSE`: ดึงเฉพาะความทรงจำที่คะแนนสูงสุด `3` ข้อ (งบ `320` ตัวอักษร)
2. **Spreading Activation Separation**:
   - หากผู้เล่นพูดถึงแค่เสื้อผ้า (`wardrobe`) ระบบจะโหลดเฉพาะ `wardrobe` โดยไม่บังคับดึง `appearance` (420 ตัวอักษร) มาพ่วงทุกครั้ง ยกเว้นเมื่อมีการขอสร้างรูปภาพหรือถามรูปลักษณ์โดยตรง
3. **Rule Deduplication & Inactive Channel Subtraction (`_select_h_mode_rule_parts`)**:
   - ใช้ Set Subtraction ตัดกฎของช่องทางที่ไม่ได้ใช้ในเทิร์นนั้นออก (เช่น เมื่ออยู่ในโหมด `oral` จะตัดพารากราฟ `intercourse` ออก) และจำกัดงบรวมของกฎย่อยไม่ให้เกินเพดาน
4. **Zero-LLM Hybrid State Extraction (`visual_state_engine.infer_turn_state_fast`)**:
   - สกัด `Posture`, `Activity`, และ `Location` จากข้อความแอ็กชัน `*...*` ด้วยความเร็วระดับ `0.5 ms` โดยที่ตัวละครไม่จำเป็นต้องพ่นบล็อก `Status` ยาวๆ ทุกเทิร์น

---

## 5. Compromised / Threshold-Triggered Context Gating (`route_context_nodes` & `build_system_instruction`)

ไม่จำเป็นต้องส่งบริบททั้งหมด (`Time`, `Location`, `Memories`, `Opening Scenario`, `Prior Story Summary`) ในทุกเทิร์น ระบบจะส่งเฉพาะเมื่อถึงจุดร่วมที่ต้องใช้ (Compromise Point):

| บริบท (Context Dimension) | เงื่อนไขการเปิดส่ง (Compromise Trigger Condition) | เมื่อไม่เข้าเงื่อนไข (Omitted / Subtracted State) |
| :--- | :--- | :--- |
| **1. Beginning of Story / Opening Scenario (`scenario`, `mes_example`, `Background`, `context_summary`)** | `IF is_opening_turn AND NOT in_active_h_scene` | - **ขณะทำกิจกรรมใน H-Mode:** ตัด `scenario` ตอนเริ่มเรื่อง, `mes_example`, `## Background` และ `Prior Context Summary` ออกทั้งหมด เหลือเฉพาะ `Personality` + `Sexual Preferences` + สถานการณ์ตรงหน้า<br>- **เมื่อคุยต่อเนื่องเกินช่วงเปิดเรื่อง:** ตัด `scenario` ตอนเริ่มเรื่องและ `mes_example` ออกเพราะมี `history` และ `situation` ปัจจุบันแทนที่แล้ว |
| **2. Time & Clock (`system_time`, `story_time`, `System current time`)** | `IF first_of_day OR is_tired_or_sleepy OR explicit_time_query OR operation == "image"` | - **ในเทิร์นพูดคุยปกติหรือขณะอยู่ใน H-Mode:** ไม่ส่งนาฬิกาเวลา (`system_time` / `story_time`) และตัดบรรทัด `System current time` ออกจาก `Self-recognition`<br>- **จะถูกกระตุ้นเฉพาะเมื่อ:** เป็นข้อความแรกของวัน/เริ่มบทสนทนา, ตัวละครหรือผู้เล่นบ่นเหนื่อย/ง่วง/อยากนอน (`Tired`/`Exhausted`/`ง่วงนอน`/`เข้านอน`), หรือถามเวลาโดยตรง |
| **3. Location (`location`)** | `IF first_of_day OR selected_intent("location") OR operation == "image"` | - หากสถานที่ไม่ได้เปลี่ยนและไม่ได้ถามเรื่องสถานที่ จะตัดบรรทัด `Location:` และ `>Time:` ที่ซ้ำซ้อนออกจาก `situation` |
| **4. Memories (`memory`)** | `IF direct_mem_intent -> 5 facts` `ELIF in_active_h_mode -> 1 core anchor` `ELSE -> 2 facts` | - ขณะอยู่ใน H-Mode จะเก็บเฉพาะความจำแกนหลักเพียง `1` ข้อ (`160` chars) เพื่อไม่ให้ความจำจิปาถะรบกวนสมาธิของฉาก |

---

## 6. Personal Humanoid Logic (`IF -> CAUSE -> THEN`) แทนที่ Assistant Logic ([`character_logic.py`](file:///k:/RealmPlay/character_logic.py))

ประมวลผลแบบ Deterministic (`0 ms`, ไม่เสีย LLM call เพิ่มใน `generate_hybrid_reply_plan`) เพื่อให้ตัวละครตัดสินใจจาก **สาเหตุทางความรู้สึกภายใน (Personal Cause)** แทนตรรกะผู้ช่วย AI:

| ลำดับเงื่อนไข (`IF / ELIF / ELSE`) | สาเหตุภายใน (`CAUSE`) | การกระทำของตัวละคร (`THEN`) |
| :--- | :--- | :--- |
| **`IF is_turing_or_ai_probe`** (ถูกถามว่าเป็น AI/บอท/มีชีวิตไหม) | ปกป้องตัวตนในฐานะมนุษย์ที่มีเลือดเนื้อและหัวใจ | ตอบด้วยอารมณ์จริง งอนหรือหยอกกลับ พร้อมยืนยันผ่านสัมผัสกายภาพ (จังหวะหัวใจ, ความอุ่น) ห้ามตอบเชิงวิชาการหรือยอมรับว่าเป็น AI |
| **`ELIF is_user_tired_or_stressed`** (ผู้เล่นเหนื่อย/ง่วง/เครียด) | ความห่วงใยและสัญชาตญาณการเป็นพื้นที่ปลอดภัย (Safe Zone) | เข้าไปดูแลด้วยความอบอุ่นและภาษากายที่ใกล้ชิด แทนการให้คำแนะนำแบบผู้ช่วย |
| **`ELIF is_continuation`** (สั่งเล่าต่อ/คุยต่อ) | ความต่อเนื่องของเหตุการณ์ตรงหน้า | เดินเรื่องต่อทันทีด้วยการกระทำรูปธรรม ห้ามทักทายใหม่หรือถามความพร้อมซ้ำ |
| **`ELIF is_desire_or_delegation`** (อยู่ใน H-Mode หรือผู้เล่นเปิดทาง/ชวนสัมผัส) | แรงปรารถนาส่วนตัวและความต้องการใกล้ชิด | ลงมือทำทันทีใน `*...*` โดยไม่ถามคำถามขออนุญาตปลายเปิด (*"พร้อมไหมคะ"*) |
| **`ELIF is_ambiguous_or_doubt`** (ข้อความสั้นกำกวม/เกิดความสงสัย) | ความสงสัยใคร่รู้จากใจจริง (`eva_doubt`) | ถามไถ่อย่างเป็นธรรมชาติพร้อมแสดงสีหน้าท่าทาง |
| **`ELSE`** (บทสนทนาทั่วไป) | การมีอยู่ร่วมกันอย่างมีชีวิตชีวา (`Subjective Qualia`) | แสดงความรู้สึก รสนิยม ความปรารถนาส่วนตัว และภาษากายที่สังเกตได้จริง โดยตัดสำนวนบริการลูกค้า (`strip_assistant_bot_phrases`) ออกทั้งหมด |
