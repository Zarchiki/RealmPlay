# RealmPlay Function Audit Checklist

ใช้คู่กับเมนู **✨ Features → Run audit** ใน RealmPlay

## ตรวจอัตโนมัติในโปรแกรม

เมนู Audit อ่านสถานะโดยไม่ส่งแชท ไม่สร้างภาพ และไม่สร้างเสียง:

- [ ] Backend และ session ของผู้ใช้ตอบกลับ
- [ ] Single-login protection เปิดใช้
- [ ] Built-in LLM อยู่สถานะ ready
- [ ] ComfyUI เชื่อมต่อได้
- [ ] มีค่า TTS และแสดงสถานะ RVC
- [ ] Rules registry โหลดได้
- [ ] Image trigger เปิด/ปิดตามการตั้งค่า
- [ ] อ่าน Character library ได้
- [ ] Statistics และ activity log ใช้งานได้

สถานะ ✓ หมายถึง endpoint หรือบริการตอบกลับได้ในขณะนั้น; สถานะ ! หมายถึง
ต้องเปิดบริการหรือทบทวนการตั้งค่า ไม่ได้หมายความว่าข้อมูลเสียหายเสมอไป.

## ตรวจใช้งานจริงก่อนปล่อยรุ่น

### บัญชีและข้อมูล

- [ ] ล็อกอินบน PC แล้วล็อกอินบัญชีเดียวกันบนมือถือ: PC ต้องถูกตัด session
- [ ] บัญชีต่างกันมองไม่เห็นประวัติหรือภาพ profile ของกันและกัน
- [ ] Import ตัวละครใหม่, แก้ Character Card, เปลี่ยน avatar และเปิดใหม่
- [ ] สร้าง session ใหม่, โหลด session เก่า, ลบ session และตรวจว่าความจำคงตาม policy

### แชทและกฎ

- [ ] ส่งข้อความปกติ: AI ตอบตาม Character Card และบริบทปัจจุบัน
- [ ] ส่งข้อความต่อเนื่อง: ไม่มี opening/action ซ้ำจนเป็น pattern
- [ ] Edit, regenerate และ continue: ประวัติหน้าจอและข้อมูลที่บันทึกตรงกัน
- [ ] ตรวจ Status, Current Situation, Memory และ Emotion หลังเหตุการณ์สำคัญ
- [ ] เปิด/ปิด Loop guard, Safety boundaries และตรวจผลใน Rule Inspector

### ภาพและเสียง

- [ ] `สร้างรูป...` ต้อง trigger แบบ natural language
- [ ] `/image ...` และ `[[image: ...]]` ต้อง trigger แบบ command
- [ ] คำบรรยายธรรมดา เช่น “เดินเข้าห้อง” ต้องไม่ trigger ภาพ
- [ ] รูปที่ได้สะท้อน subject, action, place/time, appearance, wardrobe และ emotion
- [ ] TTS อ่านเฉพาะ dialogue ตามตัวเลือก, replay ได้, RVC ใช้เมื่อเปิด
- [ ] กด ■ ระหว่างสร้างภาพ: ComfyUI ต้องหยุดและ trace เป็น Cancelled

### เสถียรภาพและทรัพยากร

- [ ] Rule Inspector แสดง progress, error, duration และ resource snapshot
- [ ] `/api/statistics` มีจำนวนงานและเวลาเฉลี่ยหลังทดสอบ chat/image/TTS
- [ ] ปิด RealmPlay แล้วไม่มี RealmPlay backend ค้างอยู่
- [ ] ทดสอบมือถือทั้งแนวตั้ง/แนวนอน: input และเมนูเข้าถึงได้

## หลักฐานที่ควรแนบในการตรวจรับ

- ภาพผล Run audit
- เวลา chat/image/TTS อย่างน้อย 3 ครั้งต่อประเภท
- ภาพ Rule Inspector เมื่อ complete, error และ cancelled อย่างละหนึ่งครั้ง
- รุ่นโมเดล LLM, workflow ComfyUI, resolution และ RVC model ที่ใช้ทดสอบ
