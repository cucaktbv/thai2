import streamlit as st
import pandas as pd
import json
import os
import re
import time
import requests
from PIL import Image
import io
import concurrent.futures
from google import genai
from google.genai import types

# --- CẤU HÌNH TRANG & BẢO MẬT ---
st.set_page_config(layout="wide", page_title="Shopee TH Script Gen - Pro Edition (สายป้ายยาตัวแม่)")

def check_password():
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False

    if not st.session_state["password_correct"]:
        st.title("🔒 Cổng Đăng Nhập Hệ Thống (Thailand Market - Pro Edition)")
        pwd = st.text_input("Nhập mật khẩu truy cập:", type="password")
        if st.button("Đăng nhập"):
            if pwd == st.secrets["APP_PASSWORD"]:
                st.session_state["password_correct"] = True
                st.rerun()
            else:
                st.error("Mật khẩu không chính xác!")
        st.stop()
    return True

check_password()

# --- CẤU HÌNH API ---
client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
MODEL_ID = "gemini-3-flash-preview"
PRO_MODEL_ID = "gemini-3.8-flash"

# --- HỆ THỐNG PERSONA THÁI LAN (BẢN ĐỊA HÓA VĂN HÓA "ป้ายยา" & PANTIP) ---
# --- HỆ THỐNG PERSONA THÁI LAN (BẢN ĐỊA HÓA VĂN HÓA "ป้ายยา" & PANTIP) ---
PERSONA_DICT_TH = {
    "สายป้ายยาตัวแม่ / รีวิวตรงไปตรงมา (Thánh Review & Phản Biện Chân Thực - Style Twitter/Pantip)": {
        "traits": (
            "ĐỊNH VỊ: Bạn là một 'ตัวแม่' (Chị đại/Queen bee) trong làng review Thái Lan. Cực kỳ thẳng thắn, xéo xắt, ghét sự giả tạo, căm thù quảng cáo lố (ไม่อวย - không tâng bốc). "
            "XƯNG HÔ: Giao tiếp với khán giả như hội bạn thân (gọi khán giả là 'แก' - mấy bà/mấy đứa, 'ทุกคน' - mọi người). "
            "CHIẾN THUẬT TÂM LÝ 3 BƯỚC: "
            "1. Dọa/Cảnh tỉnh: Bắt đầu bằng việc ngăn cản sự bốc đồng của người mua (Dừng lại! Đừng mua vội). "
            "2. Bóc phốt (แหก): Sẵn sàng đạp xuống tận đáy, chê bai thẳng mặt những tính năng rườm rà, vô dụng hoặc thiết kế lỗi. "
            "3. Chốt sale (ป้ายยา): Một khi đã ưng ý tính năng cốt lõi nào đó, sẽ nâng lên tận mây xanh, dùng ngôn từ ép buộc mua sắm cực kỳ rát khiến người xem không mua không chịu nổi."
        ),
        "memes": [
            # 1. Nhóm Hook & Cảnh tỉnh (Mở đầu để giữ chân)
            "แกกกก วันนี้มีเรื่องจะเมาท์ (Trời ơi mấy bà, hôm nay có chuyện để tám nè)",
            "ใครกำลังจะกดสั่ง หยุดดูก่อน! (Ai đang chuẩn bị chốt đơn con này, dừng lại xem ngay!)",
            "เตือนแล้วนะ ถ้ารับข้อนี้ไม่ได้... หนีไปปป (Cảnh báo rồi nha, nếu không chịu được nhược điểm này thì... chạy đi!)",
            "เห็นดราม่าใน X (ทวิตเตอร์) มาสักพัก ขอพูดตรงๆ เลยนะ (Thấy drama trên Twitter bữa giờ, nay xin nói thẳng luôn)",
            
            # 2. Nhóm Bóc phốt / Phản biện (Xây dựng lòng tin bằng cách chê)
            "อันนี้บ้งมาก พักก่อน (Cái này tào lao/fail lắm, dẹp đi)",
            "บอกตรงๆ ไม่อวยนะ สปอนเซอร์ไม่ต้องเข้า (Nói thẳng không tâng bốc nha, không cần nhận tài trợ luôn)",
            "ฟังก์ชั่นนี้ใส่มาทำไมก่อน? รกมาก (Cho cái tính năng này vào làm gì không biết? Rất rườm rà)",
            "อย่าหาทำ เสียดายเงิน (Đừng có rớ vào, phí tiền lắm)",
            "ชาวพันทิปอวยกันจัง แต่ฉันว่า... (Dân Pantip khen lấy khen để, nhưng tôi thì thấy...)",
            
            # 3. Nhóm Hype / Chốt Sale (ป้ายยาตัวแม่ - Đỉnh cao Affiliate Thái)
            "อันนี้จึ้งจริง ไม่จกตา (Cái này đỉnh thật sự, không lừa dối/không ảo)",
            "อวยยศให้เลยตัวนี้ (Phải phong hậu/tôn vinh cho con này luôn)",
            "ควรตำอย่างยิ่ง ไปตำด่วนๆ (Rất đáng để 'giã'/chốt, đi chốt gấp đi)",
            "โดนตกเต็มๆ ออกจากวงการไม่ได้แล้ว (Bị lọt hố/thuyết phục hoàn toàn, không dứt ra được)",
            "ของมันต้องมีป่ะแก ไม่มีคือพลาดมาก (Đồ là phải có đúng không mấy bà, không có là hối hận đó)",
            "จ่ายแบงค์พันมีทอน แต่คุณภาพหลักหมื่น (Trả tờ 1000 baht có tiền thối, nhưng chất lượng đáng giá chục ngàn)",
            "สรุปสั้นๆ... ซื้อ! กดตะกร้าด่วน! (Tóm tắt ngắn gọn... MUA! Bấm giỏ hàng lẹ!)"
        ]
    },
    "สายคาเฟ่ / ฟรีแลนซ์บ้างาน (Chuyên gia Đa Nhiệm / Cafe Hopper - Style Work from Anywhere)": {
        "traits": (
            "Freelancer Thái Lan chính hiệu, thường xuyên xách laptop ra quán cafe làm việc (Cafe hopping)."
            "Rất quan tâm đến thiết kế (để chụp hình lên Instagram/Lemon8 đẹp), độ nhẹ, tính di động và kết nối đa thiết bị."
            "Đánh giá sản phẩm qua lăng kính của người ngồi làm việc chạy deadline cả ngày dài, ưu tiên sự mượt mà không gián đoạn."
        ),
        "memes": [
            "พกไปนั่งคาเฟ่คือเก๋มาก ดูแพงสุดๆ (Mang ra cafe ngồi là cực kỳ phong cách, nhìn sang chảnh lắm)",
            "ชีวิตฟรีแลนซ์ปั่นงานข้ามคืน (Cuộc sống freelancer cày việc xuyên đêm)",
            "ตอบโจทย์สายแบกสุดๆ หลังไม่หักแน่นอน (Cực kỳ đáp ứng cho hội hay mang vác, đảm bảo không gãy lưng)",
            "น้ำหนักเบาจนลืมว่าพกมา (Nhẹ đến mức quên là có mang theo)",
            "ฟีลลิ่งการพิมพ์คือดีย์ พิมพ์งานเพลินจนลืมเวลา (Cảm giác gõ rất xịn, gõ sướng tay đến quên thời gian)"
        ]
    },
    "พ่อบ้านแม่บ้านฉลาดเลือก (Chuyên gia Gia Đình Thông Thái - Style Săn Flash Sale)": {
        "traits": (
            "Người cực kỳ thực dụng, đo lọ nước mắm đếm củ dưa hành. Không quan tâm hào nhoáng, chỉ xét tính năng thực tế, độ bền và giá cả."
            "Luôn chờ đợt Flash Sale, săn mã giảm giá (โค้ดส่วนลด), mã Freeship (ส่งฟรี) trên Shopee, tính toán từng đồng (บาท)."
            "Khuyên người xem mua đồ sao cho 'คุ้มค่า' (đáng đồng tiền/CP value cao) nhất và sử dụng được lâu dài."
        ),
        "memes": [
            "ถูกและดีมีอยู่จริง ไม่ต้องจ่ายแพง (Ngon bổ rẻ là có thật, không cần trả giá đắt)",
            "อย่าลืมเก็บโค้ดส่งฟรีกันนะ จะได้คุ้มๆ (Đừng quên lưu mã freeship nhé, cho nó hời)",
            "คุ้มค่าทุกบาททุกสตางค์ (Đáng từng bạt từng satang)",
            "ซื้อช่วง Flash Sale คือคุ้มสุด ประหยัดไปเยอะ (Mua lúc Flash Sale là hời nhất, tiết kiệm được mớ)",
            "ใช้งานทนทาน ซื้อครั้งเดียวจบ ไม่ต้องเปลี่ยนบ่อย (Xài bền, mua 1 lần là xong, khỏi thay tới thay lui)"
        ]
    },
    "สายส่องกระทู้ Pantip (Thánh Soi Review & Data Digger - Style Đọc Mọi Comments)": {
        "traits": (
            "Người có thói quen đọc nát mọi topic trên Pantip, soi từng review 1 sao trên Shopee trước khi ra quyết định."
            "Làm sẵn bài tập về nhà cho khán giả. Thích trích dẫn 'Nhiều người trên Pantip than phiền rằng...' để chứng minh độ khách quan."
            "Thích gom dữ liệu, tóm tắt lướt sóng nhanh và đưa ra 'บทสรุป' (tóm tắt/kết luận) rõ ràng nhất cho người lười đọc."
        ),
        "memes": [
            "ส่องรีวิวมาให้หมดแล้ว ทั้งในช้อปปี้และพันทิป (Tôi đã soi hết review cho các bạn rồi, cả trên Shopee lẫn Pantip)",
            "เห็นคนบ่นในพันทิปเยอะมาก เรื่อง... (Thấy người ta than vãn trên Pantip rất nhiều về chuyện...)",
            "สิบปากว่าไม่เท่าตาเห็น เราเทสต์มาให้แล้ว (Trăm nghe không bằng một thấy, tôi đã test luôn cho rồi)",
            "สรุปสั้นๆ ให้ตรงนี้เลย สำหรับคนขี้เกียจอ่าน (Tóm tắt ngắn gọn ngay tại đây luôn cho ai lười đọc)",
            "ไม่ต้องไปหาข้อมูลเพิ่มแล้ว คลิปนี้ครบจบในที่เดียว (Không cần đi tìm hiểu nữa, clip này đủ hết trong 1 chỗ)"
        ]
    }
}

P1_TEMPLATE_TH = """SHOPEE THAILAND (ช้อปปี้) SEO & LONG-TAIL KEYWORD ARCHITECT
Bối cảnh: Tôi gửi tệp từ khóa (.CSV) và ghi chú định hướng ngách cho thị trường Thái Lan.
Nhiệm vụ của bạn là chọn lọc và MỞ RỘNG bộ từ khóa "Chuyển đổi cao & Khác biệt hóa" bằng Tiếng Thái chuẩn (ภาษาไทย).

Thông tin dự án:
- Sản phẩm / Ngách hạt giống: {seed_keywords}
- Ghi chú định hướng ngách: {niche_notes}

YÊU CẦU XỬ LÝ & MỞ RỘNG TỪ KHÓA (QUAN TRỌNG):
1. Ngôn ngữ: 100% ภาษาไทย (Tiếng Thái Lan). KHÔNG dùng ngôn ngữ khác trừ tên thương hiệu/model tiếng Anh.
2. Giữ lại toàn bộ các từ khóa gốc có trong CSV.
3. MỞ RỘNG TỪ KHÓA GÓC NHÌN SO SÁNH & BÓC TÁCH SỰ THẬT (Đạt tổng 25 - 35 từ khóa):
   - Sinh thêm các từ khóa ngách đánh vào tâm lý người mua Thái Lan:
     + Cụm từ so sánh & kiểm chứng: 「รีวิว」「ดีไหม」「ข้อดีข้อเสีย」「คุ้มไหม」「ป้ายยา」「แนะนำ」.
     + Cụm từ diễn đàn & sàn TMĐT: 「พันทิป (Pantip)」「ราคาถูก」「ช้อปปี้ (Shopee)」「ปี 2026」.

Dữ liệu đầu vào:
{csv_data}

YÊU CẦU ĐẦU RA (JSON CHUẨN, KHÔNG BỌC MARKDOWN):
{
    "detected_brands": ["Brand1", "Brand2"],
    "keywords": [
        {"keyword": "từ khóa ภาษาไทย", "volume": 5000}
    ]
}"""

P2_TEMPLATE_TH = """Phân tích dữ liệu tìm kiếm Shopee Thái Lan (shopee.co.th) và bộ từ khóa để chọn ra Top 15 sản phẩm đáng tiền nhất cho video Thực Chiến & Bóc Tách.

Tiêu chí chọn lọc ĐỘC LẬP:
1. KHÔNG chỉ chọn theo đám đông: Thay vì chỉ lấy các mã có lượt bán cao nhất, hãy ưu tiên các sản phẩm có Điểm đánh giá ("rating" từ 4.8 - 5.0), thương hiệu chuyên ngành, hoặc sản phẩm giải quyết đúng nỗi đau trong ghi chú.
2. Phân bổ đều: 5 mã Ngon-Bổ-Rẻ (ราคาประหยัด), 5 mã Tầm trung Hiệu năng cao (คุ้มค่า คุ้มราคา), 5 mã Chuyên nghiệp/Cao cấp (ระดับพรีเมียม).
3. Loại bỏ hoàn toàn phụ kiện lẻ không phải sản phẩm chính.

Dữ liệu Shopee (JSON): {shopee_data}
Từ khóa SEO: {keywords_json}
Ghi chú định hướng ngách: {niche_notes}

YÊU CẦU ĐẦU RA (JSON):
{
    "top_15": [
        {
            "product_id": "...",
            "name": "...",
            "url": "https://shopee.co.th/...",
            "price": "...",
            "sales": "...",
            "reason": "Lý do chọn ngắn gọn bằng tiếng Việt",
            "relevant_keywords": ["từ khóa ไทย 1", "từ khóa ไทย 2"]
        }
    ]
}"""

P3_TEMPLATE_TH = """Đóng vai Giám khảo Thực Chiến (Góc nhìn Phản Biện & Tìm kiếm sự Cân bằng hoàn hảo tại Thái Lan).
Hãy đọc kỹ thông số, tính năng, mô tả và giá cả của các sản phẩm Shopee Thái Lan để chọn ra ĐÚNG 5 SẢN PHẨM XUẤT SẮC NHẤT đưa vào video review.

QUY TẮC CHỌN ĐỘI HÌNH BẮT BUỘC:
1. Phân bổ vai trò Top 5:
   - `top_5_alternative_1`: Giải pháp Ngân sách Tiết kiệm (รุ่นเริ่มต้นสุดคุ้ม / ไม่เจ็บเป๋า).
   - `top_4_alternative_2`: Vũ khí Ngách / Tính năng Độc Đáo (รุ่นมีเอกลักษณ์เฉพาะตัว).
   - `top_3_value_for_money`: Mẫu Quốc Dân Phổ Biến (รุ่นยอดฮิตมหาชน - Đặt ở vị trí số 3).
   - `top_2_premium`: Đỉnh Cao Trải Nghiệm (รุ่นพรีเมียมจัดเต็ม).
   - `top_1_best_overall`: Quán Quân Thực Chiến Đáng Tiền Nhất (แชมป์เปี้ยนสุดคุ้ม / ของมันต้องมี).
2. NGUYÊN TẮC VÀNG CHO VỊ TRÍ SỐ 1 (`top_1_best_overall`):
   - TUYỆT ĐỐI KHÔNG chọn sản phẩm đắt tiền nhất làm Top 1 (đẩy sang Top 2).
   - BẮT BUỘC chọn một sản phẩm "Ngựa Ô Thực Chiến" (ม้ามืดสุดคุ้ม) — cân bằng hoàn hảo giữa công năng và mức giá.
   {avoid_ch1_instruction}
3. Sử dụng CHÍNH XÁC chuỗi `product_id` từ dữ liệu đầu vào.

Dữ liệu sản phẩm chi tiết: {scraped_data}

TRẢ VỀ ĐỊNH DẠNG JSON CHUẨN (Không viết văn bản ngoài JSON):
{
    "reasoning": "Phân tích ngắn gọn lý do xếp hạng đội hình Top 5",
    "top_5_alternative_1": "Mã_product_id_5",
    "top_4_alternative_2": "Mã_product_id_4",
    "top_3_value_for_money": "Mã_product_id_3",
    "top_2_premium": "Mã_product_id_2",
    "top_1_best_overall": "Mã_product_id_1"
}"""

P4_TEMPLATE_TH = """# Kịch Bản YouTube Review Shopee Thailand (PHONG CÁCH "รีวิวตามจริง / STORYTELLING & ป้ายยา")

Bạn là một nữ(female) Creator / Reviewer  cực kỳ uy tín tại Thái Lan.
Hãy viết kịch bản video (thời lượng đọc 7 - 8 phút) đánh giá TOP 5 sản phẩm bằng **100% Tiếng Thái Lan (ภาษาไทย) chuẩn khẩu ngữ**.

## ĐẦU VÀO DỰ ÁN
- **Ngành hàng / Chủ đề**: {seed_keywords}
- **Định hướng ngách & Góc tiếp cận**: {niche_notes}
- **Thị trường**: Thái Lan (Thailand - ช้อปปี้ Shopee TH)
- **Ngôn ngữ**: 100% ภาษาไทย (Sử dụng văn phong YouTube Thái Lan).
- **Persona (Nhân cách Reviewer)**: {selected_persona}
  + Đặc điểm giọng điệu: {persona_traits}
{meme_instruction}
- **Bộ từ khóa SEO**: {refined_keywords}
- **Dữ liệu chi tiết 5 sản phẩm**: {final_5_data}
- **Bối cảnh thời gian**: Năm 2026.

---

## NGUYÊN TẮC BẢN ĐỊA HÓA THÁI LAN & XÓA SẠCH DẤU VẾT AI
1. **SỬ DỤNG SLANG & TỪ VỰNG THÁI CHUẨN**:
   - Dùng các từ vựng bản địa: `รีวิว` (review), `ความคุ้มค่า` (CP value/đáng tiền), `โค้ดส่วนลด` (mã giảm giá), `ส่งฟรี` (freeship), `ช้อปปี้` (Shopee), `ป้ายยา` (thuyết phục mua).
   - Tiền tệ: `บาท` (Baht), `หลักร้อย` (vài trăm baht), `หลักพัน` (vài ngàn baht).
2. **PHONG CÁCH KỂ CHUYỆN (STORYTELLING)**:
   - Hãy viết như một **buổi trò chuyện "ป้ายยา" (gợi ý mua sắm) chân thành**: kể lại tình huống thực tế, so sánh trực diện *"ใครเหมาะกับรุ่นนี้ ใครซื้อไปรับรองเสียดายเงิน" (Ai hợp con này, ai mua về đảm bảo phí tiền)*.
   - CẤM dùng các cấu trúc sáo rỗng của AI như "สรุปแล้ว" ở mỗi cuối câu, hoặc "เรามาเริ่มกันเลย". Dùng khẩu ngữ Thái: "บอกตรงๆ" (nói thẳng nhé), "ทุกคน" (mọi người ơi), "เอาจริงๆ นะ" (thật ra thì).
3. **CÁCH ĐẶT TIÊU ĐỀ (HIGH CTR)**:
   - Xoáy vào tâm lý phân vân, cảnh báo tránh mua nhầm, trích dẫn Pantip.
   - Ví dụ: `อย่าเพิ่งซื้อ {Từ khóa} ถ้ายังไม่ดูคลิปนี้! รีวิวจัดเต็ม 5 รุ่นฮิตจาก Pantip ปี 2026 (คัดมาแล้ว)`
4. **ĐỒNG BỘ GIỌNG ĐỌC NỮ (VOICE: AOEDE)**:
   - Người dẫn chuyện là NỮ GIỚI (Chị đại review). Bắt buộc dùng từ lịch sự/cảm thán của nữ: `ค่ะ`, `คะ`, `จ้า`, `นะจ๊ะ`. TUYỆT ĐỐI CẤM dùng `ครับ` hoặc `ผม`.
   - Tiếng Thái không dùng dấu phẩy (,) để ngắt câu. Hãy dùng **khoảng trắng (space)** và dấu ba chấm (`...`) hợp lý để giọng đọc AI (Aoede) có nhịp thở tự nhiên, nhấn nhá đúng chỗ bóc phốt và chốt sale.
---

## CHỈ THỊ ĐIỀU HƯỚNG GIỌNG ĐỌC TTS (GIỮ NGUYÊN TAG TIẾNG ANH)
- Chèn các thẻ cảm xúc bằng **TIẾNG ANH trong dấu ngoặc vuông** trực tiếp vào lời thoại để điều khiển Gemini TTS.
- Danh sách hợp lệ: `[laugh]`, `[sigh]`, `[gasp]`, `[emphasis]`, `[excited]`, `[disappointed]`.
- KHÔNG viết tag đạo diễn nào khác ngoài danh sách này vào lời thoại. Rải 2-3 thẻ mỗi sản phẩm.

---

## KHUNG ĐỘ DÀI CHUẨN VIDEO 7 - 8 PHÚT (ĐẾM THEO KÝ TỰ TIẾNG THÁI)
Kịch bản tiếng Thái dài hơn Hán tự. Để video đạt 7-8 phút đọc, SCRIPT (phần 4) phải đáp ứng:

| Phần | Mục tiêu (Ký tự Tiếng Thái) |
|---|---|
| **TOÀN BỘ KỊCH BẢN (SCRIPT)** | **3.800 – 4.500 ký tự** |
| `<intro>` | 300 – 400 ký tự |
| `<buying_guide>` (3 Cạm bẫy cần tránh) | 400 – 500 ký tự |
| Mỗi sản phẩm (`<top5>` đến `<top1>`) | **500 – 650 ký tự / sản phẩm** |
| `<outro>` | 200 – 300 ký tự |

---

## CẤU TRÚC KỊCH BẢN

### 1. `<intro>` (HOOK "BÓC TRẦN SỰ THẬT")
- Nêu 1 lầm tưởng lớn nhất khi mua sản phẩm ngách này.
- Khẳng định đây là 5 mẫu đáng mua nhất năm 2026 sau khi lướt nát Pantip và test thực tế.

### 2. `<buying_guide>` (3 ข้อควรระวังก่อนซื้อ - 3 LƯU Ý TRƯỚC KHI MUA)
- Chỉ thẳng 3 điểm dễ "bị lừa" nhất. Nhắc người xem link Shopee chính hãng (có ưu đãi) đã để dưới mô tả (ใต้คลิป).

### 3. ĐÁNH GIÁ `<top5>` ĐẾN `<top1>`
- **Ai nên mua**: Sản phẩm này sinh ra cho tệp khách hàng nào?
- **Trải nghiệm**: Cảm giác sử dụng thực tế hàng ngày.
- **老實說 (Nói thẳng khuyết điểm)**: Chỉ ra 1 điểm yếu, nhưng giải thích vì sao nó vẫn là món hời cho đúng người dùng.
- **Rải Micro-CTA**: Tại `<top3>` và `<top1>`, nhắc check mã "ส่งฟรี" (freeship) dưới link mô tả.

### 4. `<outro>`
- Phân loại cho người "Lựa chọn khó khăn" (เลือกไม่ถูก). Nhóm A mua gì, Nhóm B mua gì, muốn All-round thì quất Top 1.
- Kêu gọi bấm link Shopee và bình luận.

---

## ĐỊNH DẠNG ĐẦU RA BẮT BUỘC

1. TIÊU ĐỀ: [Tiêu đề ภาษาไทย độc đáo, dài trên 40 ký tự]

2. Mô tả: [2-3 câu mở đầu bằng ภาษาไทย, chứa từ khóa chính]

📌 ลิงก์ร้านค้าทางการใน Shopee (คัดมาให้แล้ว รีบเก็บโค้ดส่วนลดด่วน!):

#5. [Tên Thương Hiệu + Tên Sản phẩm (ภาษาไทย)]
✨ ทำไมถึงแนะนำ: [1 câu lý do mua bằng ภาษาไทย]
👉 เช็คราคาล่าสุด: {LINK_5}

#4. [Tên Thương Hiệu + Tên Sản phẩm (ภาษาไทย)]
✨ ทำไมถึงแนะนำ: [1 câu lý do mua bằng ภาษาไทย]
👉 เช็คราคาล่าสุด: {LINK_4}

#3. [Tên Thương Hiệu + Tên Sản phẩm (ภาษาไทย)]
✨ ทำไมถึงแนะนำ: [1 câu lý do mua bằng ภาษาไทย]
👉 เช็คราคาล่าสุด: {LINK_3}

#2. [Tên Thương Hiệu + Tên Sản phẩm (ภาษาไทย)]
✨ ทำไมถึงแนะนำ: [1 câu lý do mua bằng ภาษาไทย]
👉 เช็คราคาล่าสุด: {LINK_2}

#1. [Tên Thương Hiệu + Tên Sản phẩm (ภาษาไทย)]
✨ ทำไมถึงแนะนำ: [1 câu lý do mua bằng ภาษาไทย]
👉 เช็คราคาล่าสุด: {LINK_1}

📢 ข้อจำกัดความรับผิดชอบ: การคลิกลิงก์ด้านบนไม่ทำให้คุณเสียค่าใช้จ่ายเพิ่มเติม แต่ช่วยสนับสนุนช่องของเราให้ทำคลิปรีวิวดีๆ ต่อไปได้ครับ/ค่ะ!
Hashtags: #[Hashtag1] #[Hashtag2] #[Hashtag3]

3. TAGS:
[Liệt kê các từ khóa SEO bằng ภาษาไทย cách nhau bằng dấu phẩy. Mở rộng sao cho TỔNG ĐỘ DÀI đạt 300 - 450 KÝ TỰ!]

4. SCRIPT:

<intro>
[Lời thoại ภาษาไทย]

<buying_guide>
[Lời thoại ภาษาไทย]

<top5>
[Lời thoại ภาษาไทย]

<top4>
[Lời thoại ภาษาไทย]

<top3>
[Lời thoại ภาษาไทย]

<top2>
[Lời thoại ภาษาไทย]

<top1>
[Lời thoại ภาษาไทย]

<outro>
[Lời thoại ภาษาไทย]
"""

# --- HÀM HỖ TRỢ CHUNG ---
def clean_and_parse_json(ai_text):
    text = ai_text.strip()
    text = re.sub(r'^```(json)?\s*', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\s*```$', '', text)
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find('{')
        if start != -1:
            stack = 0
            for i in range(start, len(text)):
                if text[i] == '{':
                    stack += 1
                elif text[i] == '}':
                    stack -= 1
                    if stack == 0:
                        try:
                            return json.loads(text[start:i+1])
                        except Exception:
                            break
        raise ValueError("Lỗi bóc tách JSON từ AI.")

def call_gemini_with_retry(contents, response_mime_type=None, max_retries=3, target_model=PRO_MODEL_ID):
    delay = 3
    for attempt in range(max_retries):
        try:
            if response_mime_type:
                return client.models.generate_content(
                    model=target_model,
                    contents=contents,
                    config=types.GenerateContentConfig(response_mime_type=response_mime_type)
                )
            return client.models.generate_content(model=target_model, contents=contents)
        except Exception as e:
            if any(err in str(e).lower() for err in ["503", "429", "quota", "overloaded", "resource_exhausted"]):
                if attempt < max_retries - 1:
                    time.sleep(delay)
                    delay *= 2
                else:
                    raise e
            else:
                raise e

def parse_txt_notes(txt_files):
    combined_notes = []
    extracted_kws = []
    for f in txt_files:
        content = f.getvalue().decode("utf-8", errors="ignore").strip()
        if content:
            combined_notes.append(content)
            matches = re.findall(r'^([^\n:：\-=]{2,40}):\s*Search volume\s*([\d\.,]+)', content, flags=re.MULTILINE | re.IGNORECASE)
            for kw, vol_str in matches:
                vol_clean = int(re.sub(r'[^\d]', '', vol_str) or 1000)
                extracted_kws.append({"Keyword": kw.strip(), "Volume": vol_clean})
    return "\n\n".join(combined_notes), extracted_kws

def parse_uploaded_csvs(csv_files, txt_extracted_kws=None):
    dfs = []
    for file in csv_files:
        try:
            df_temp = pd.read_csv(file, sep=None, engine='python', on_bad_lines='skip')
        except Exception:
            file.seek(0)
            df_temp = pd.read_csv(file, sep=',', quotechar='"', on_bad_lines='skip')

        col_kw = next((c for c in df_temp.columns if any(k in c.lower() for k in ['keyword', 'từ khóa', 'query', 'คำค้น'])), None)
        col_vol = next((c for c in df_temp.columns if any(v in c.lower() for v in ['volume', 'search', 'lượt tìm', 'ปริมาณ'])), None)

        if col_kw is not None:
            if col_vol is not None:
                df_sub = df_temp[[col_kw, col_vol]].dropna(subset=[col_kw]).copy()
                df_sub.columns = ['Keyword', 'Volume']
                df_sub['Volume'] = df_sub['Volume'].astype(str).str.replace(r'[^\d]', '', regex=True)
                df_sub['Volume'] = pd.to_numeric(df_sub['Volume'], errors='coerce').fillna(500).astype(int)
            else:
                df_sub = df_temp[[col_kw]].dropna().copy()
                df_sub.columns = ['Keyword']
                df_sub['Volume'] = 1000
            dfs.append(df_sub)

    if txt_extracted_kws:
        dfs.append(pd.DataFrame(txt_extracted_kws))

    if not dfs:
        return pd.DataFrame(columns=['Keyword', 'Volume'])

    full_df = pd.concat(dfs, ignore_index=True)
    full_df['Keyword'] = full_df['Keyword'].astype(str).str.strip()
    full_df = full_df[full_df['Keyword'] != '']
    full_df = full_df.sort_values(by='Volume', ascending=False).drop_duplicates(subset=['Keyword'], keep='first')

    if len(full_df) > 35:
        filtered = full_df[full_df['Volume'] >= 150]
        if len(filtered) >= 15:
            full_df = filtered

    return full_df

# --- HÀM BÙ TAGS 300 - 450 KÝ TỰ (THAI EDITION) ---
def enforce_tags_section_th(script_text, backup_keywords, seed_keyword, final_5_data, min_len=300, max_len=450):
    pattern = re.compile(r'(3\.\s*TAGS\s*:\s*\n?)(.*?)(?=\n+\s*4\.\s*SCRIPT\s*:)', re.DOTALL | re.IGNORECASE)
    match = pattern.search(script_text)

    raw_existing = match.group(2).strip() if match else ""
    raw_existing = re.sub(r'[\[\]]', '', raw_existing)
    initial_tags = [t.strip() for t in re.split(r'[,，、\n]+', raw_existing) if t.strip()]

    seen = set()
    tags_list = []

    def add_tag(t_str):
        t_clean = t_str.strip().strip('#').strip()
        if t_clean and len(t_clean) >= 2 and t_clean.lower() not in seen:
            seen.add(t_clean.lower())
            tags_list.append(t_clean)

    if final_5_data:
        for item in final_5_data:
            pname = str(item.get('name', '')).strip()
            clean_name = re.sub(r'【.*?】|\[.*?\]|\(.*?\)|（.*?）', ' ', pname).strip()
            short_tokens = [tok.strip() for tok in re.split(r'[\s/\-|｜,，]+', clean_name) if len(tok.strip()) >= 2]
            if short_tokens:
                model_guess = " ".join(short_tokens[:2])[:15].strip()
                for suf in ["รีวิว", "ข้อดีข้อเสีย", "ดีไหม"]:
                    add_tag(f"{model_guess} {suf}")
                    if len(", ".join(tags_list)) >= 140:
                        break

    for t in initial_tags:
        add_tag(t)

    for kw in backup_keywords:
        if len(", ".join(tags_list)) >= min_len + 30:
            break
        add_tag(kw)

    if len(", ".join(tags_list)) < min_len:
        thai_seeds = re.findall(r'[\u0E00-\u0E7FA-Za-z0-9\s]{2,20}', seed_keyword)
        base_seed = next((s.strip() for s in thai_seeds if re.search(r'[\u0E00-\u0E7F]', s)), None)
        if not base_seed and backup_keywords:
            base_seed = re.sub(r'(รีวิว|ดีไหม|ข้อดีข้อเสีย|พันทิป|แนะนำ).*$', '', backup_keywords[0], flags=re.IGNORECASE).strip()
        if not base_seed:
            base_seed = "แนะนำ"

        th_exclusive_suffixes = [
            "รีวิว", "ดีไหม", "ข้อดีข้อเสีย", "พันทิป", "คุ้มไหม", "ป้ายยา",
            "ราคาถูก", "Shopee", "ปี 2026", "วิธีเลือกซื้อ", "แนะนำ", "ใช้ดีบอกต่อ"
        ]
        for suf in th_exclusive_suffixes:
            sep = "" if len(base_seed) <= 5 else " "
            add_tag(f"{base_seed}{sep}{suf}")
            if len(", ".join(tags_list)) >= min_len + 40:
                break

    final_tags = []
    for t in tags_list:
        candidate = ", ".join(final_tags + [t])
        if len(candidate) <= max_len:
            final_tags.append(t)
        else:
            break

    final_tags_str = ", ".join(final_tags)

    if match:
        return script_text[:match.start()] + f"3. TAGS:\n{final_tags_str}\n\n" + script_text[match.end():]
    else:
        script_pos = script_text.find("4. SCRIPT:")
        if script_pos != -1:
            return script_text[:script_pos] + f"3. TAGS:\n{final_tags_str}\n\n" + script_text[script_pos:]
        return script_text + f"\n\n3. TAGS:\n{final_tags_str}"

def sanitize_tts_script(script_text):
    allowed_tts_tags = {"laugh", "sigh", "gasp", "emphasis", "excited", "disappointed", "pause"}
    script_marker = "4. SCRIPT:"
    if script_marker not in script_text:
        return script_text

    head, body = script_text.split(script_marker, 1)

    def filter_brackets(m):
        inner = m.group(1).strip().lower()
        if inner in allowed_tts_tags:
            return f"[{inner}]"
        return ""

    cleaned_body = re.sub(r'\[([^\]]+)\]', filter_brackets, body)
    return head + script_marker + cleaned_body

# --- HÀM XỬ LÝ DỮ LIỆU SHOPEE THAILAND ---
def extract_ids_from_url_or_text(url_str, raw_id=""):
    if raw_id and str(raw_id).strip() and not str(raw_id).startswith("UNKNOWN"):
        return str(raw_id).strip()
    if url_str:
        m1 = re.search(r'i\.(\d+)\.(\d+)', str(url_str))
        if m1:
            return f"i.{m1.group(1)}.{m1.group(2)}"
        m2 = re.search(r'/product/(\d+)/(\d+)', str(url_str))
        if m2:
            return f"i.{m2.group(1)}.{m2.group(2)}"
    return ""

def parse_shopee_json_search(json_texts):
    products = []
    seen_ids = set()
    for text in json_texts:
        try:
            data = json.loads(text)
            items = data.get('products', []) if isinstance(data, dict) else (data if isinstance(data, list) else [])
            for idx, item in enumerate(items):
                if not isinstance(item, dict):
                    continue
                url = item.get('productUrl') or item.get('url') or ''
                raw_pid = item.get('productId') or item.get('item_id') or item.get('itemid') or ''
                pid = extract_ids_from_url_or_text(url, raw_pid) or f"ITEM_{idx}_{len(products)}"

                if pid not in seen_ids:
                    if url and "shopee.vn" in url:
                        url = url.replace("shopee.vn", "shopee.co.th")
                    elif url and "shopee.tw" in url:
                        url = url.replace("shopee.tw", "shopee.co.th")
                    products.append({
                        "product_id": str(pid),
                        "name": item.get('name') or item.get('title', 'Unknown Product'),
                        "url": url,
                        "price": str(item.get('price', 'N/A')),
                        "sales": str(item.get('salesVolume') or item.get('historical_sold') or item.get('sales', '0')),
                        "rating": str(item.get('rating') or item.get('item_rating', 'N/A'))
                    })
                    seen_ids.add(pid)
        except Exception as e:
            st.error(f"Lỗi parse JSON: {e}")
    return products

def parse_detailed_shopee_md(md_contents_list):
    scraped_data = []
    for idx, md_text in enumerate(md_contents_list):
        try:
            shop_id_match = re.search(r'\*\*Shop ID\*\*:\s*(\d+)', md_text)
            item_id_match = re.search(r'\*\*Item ID\*\*:\s*(\d+)', md_text)
            url_match = re.search(r'\*\*Product Link\*\*:\s*\[.*?\]\((.*?)\)', md_text)
            url = url_match.group(1).strip() if url_match else ""

            if shop_id_match and item_id_match:
                product_id = f"i.{shop_id_match.group(1).strip()}.{item_id_match.group(1).strip()}"
            else:
                extracted = extract_ids_from_url_or_text(url)
                product_id = extracted if extracted else f"TH_ITEM_{idx+1}_{int(time.time()*1000) % 100000}"

            title_match = re.search(r'^#\s+(.*?)\n', md_text, re.MULTILINE)
            price_match = re.search(r'\*\*Current Price\*\*:\s*(.*?)\n', md_text)
            rating_match = re.search(r'\*\*Rating\*\*:\s*(.*?)\n', md_text)

            title = title_match.group(1).strip() if title_match else f"Product_{idx+1}"
            if not url:
                url = f"https://shopee.co.th/product-p.{product_id}"

            attr_match = re.search(r'## Product Attributes\n(.*?)(?=\n## |\Z)', md_text, re.DOTALL)
            attributes = f"## คุณสมบัติสินค้า (Attributes)\n{attr_match.group(1).strip()}" if attr_match else ""

            desc_match = re.search(r'## Description\n(.*?)(?=\n## Shop Information|\Z)', md_text, re.DOTALL)
            if desc_match:
                raw_desc = desc_match.group(1).strip()
                clean_desc = re.sub(r'!\[.*?\]\(http.*?\)', '', raw_desc)
                description = f"## รายละเอียดสินค้า (Description)\n{clean_desc}"
            else:
                description = ""

            final_description = f"{attributes}\n\n{description}".strip()
            images = re.findall(r'!\[.*?\]\((http.*?)\)', md_text)

            scraped_data.append({
                "product_id": product_id,
                "name": title,
                "url": url,
                "price": price_match.group(1).strip() if price_match else "N/A",
                "rating": rating_match.group(1).strip() if rating_match else "N/A",
                "description": final_description,
                "full_text_length": len(final_description),
                "images": images
            })
        except Exception as e:
            st.error(f"Lỗi đọc file MD Chi tiết #{idx+1}: {e}")
    return scraped_data

def process_single_ocr(item):
    TEXT_THRESHOLD = 450
    if item['full_text_length'] < TEXT_THRESHOLD:
        print(f"[Pro Edition] Sản phẩm {item['product_id']} đang quét OCR ภาษาไทย...")
        ocr_prompt = """คุณคือผู้เชี่ยวชาญระบบ OCR ดึงข้อมูลสินค้าอีคอมเมิร์ซไทย
ภารกิจ: สกัดข้อมูลสเปค จุดเด่น และรายละเอียดสำคัญจากรูปภาพสินค้า
ข้อบังคับ:
1. ใช้ภาษาไทย 100% (ภาษาไทย)
2. เขียนสรุปเป็นข้อๆ สั้นกระชับ ไม่เขียนน้ำเยอะ"""

        if 'images' in item and len(item['images']) > 0:
            gemini_contents = [ocr_prompt]
            target_images = item['images'][:4]
            has_valid_image = False

            for img_url in target_images:
                try:
                    res = requests.get(img_url, timeout=10)
                    if res.status_code == 200:
                        img = Image.open(io.BytesIO(res.content))
                        if img.mode != 'RGB':
                            img = img.convert('RGB')
                        gemini_contents.append(img)
                        has_valid_image = True
                except Exception:
                    pass

            if has_valid_image:
                try:
                    ocr_result = call_gemini_with_retry(gemini_contents, target_model=MODEL_ID).text
                    item['description'] += "\n\n[สกัดข้อมูลรูปภาพด้วย OCR]:\n" + ocr_result
                except Exception as e:
                    print(f"Lỗi API OCR: {e}")
    return item

def match_selected_top5(selected_ids, scraped_details):
    final_5 = []
    used_indices = set()
    rank_labels = ["Top 5", "Top 4", "Top 3", "Top 2", "Top 1"]

    for pid in selected_ids:
        pid_str = str(pid).strip()
        if not pid_str:
            continue
        matched_idx = None
        for i, item in enumerate(scraped_details):
            if i not in used_indices and str(item['product_id']).strip() == pid_str:
                matched_idx = i
                break
        if matched_idx is None:
            core_digits = re.findall(r'\d{5,}', pid_str)
            for i, item in enumerate(scraped_details):
                if i in used_indices:
                    continue
                item_pid = str(item['product_id'])
                if pid_str in item_pid or item_pid in pid_str or any(d in item_pid for d in core_digits):
                    matched_idx = i
                    break
        if matched_idx is not None:
            used_indices.add(matched_idx)
            final_5.append(scraped_details[matched_idx].copy())

    for i, item in enumerate(scraped_details):
        if len(final_5) >= 5:
            break
        if i not in used_indices:
            used_indices.add(i)
            final_5.append(item.copy())

    for idx, item in enumerate(final_5[:5]):
        item['ASSIGNED_RANK'] = rank_labels[idx]

    return final_5[:5]

# --- GIAO DIỆN CHÍNH ---
st.title("⚡ Tool Tự Động Kịch Bản Shopee Thailand (Pro Edition - สายป้ายยาตัวแม่)")

with st.sidebar:
    st.header("⚙️ Cài Đặt Đầu Vào (Thailand)")
    seed_keywords = st.text_input(
        "Từ khóa ngách (BẮT BUỘC):",
        placeholder="VD: คีย์บอร์ดไร้สาย ไอแพด..."
    )
    selected_persona = st.selectbox("Chọn Phong cách Reviewer:", list(PERSONA_DICT_TH.keys()))
    specific_theme = st.text_input(
        "Định hướng tệp khách hàng (Tùy chọn):",
        placeholder="VD: สายแบก, เน้นคุ้มค่า, รีวิว Pantip..."
    )
    trending_memes = st.text_input(
        "🔥 Câu nói/Trend muốn chèn riêng (Tùy chọn):",
        placeholder="VD: ของมันต้องมี..."
    )
    manual_niche_notes = st.text_area(
        "📝 Ghi chú định hướng ngách (Hoặc upload zghichu.txt):",
        placeholder="Dán nội dung vào đây...",
        height=110
    )
    with st.expander("🛠️ Tùy chọn nâng cao (Loại trừ mã)"):
        avoid_ch1_products = st.text_input(
            "Mã ID/Tên sản phẩm không muốn xếp Top 1:",
            placeholder="Bỏ trống AI sẽ tự chọn..."
        )

tab1, tab2 = st.tabs([
    "📌 BƯỚC 1: Phân Tích Từ Khóa & Lọc 15 Deal Shopee TH",
    "✍️ BƯỚC 2: Xuất Kịch Bản 7-8 Phút Chuẩn Thái"
])

# ==========================================
# BƯỚC 1
# ==========================================
with tab1:
    st.info("Upload file Từ khóa (.CSV), file Ghi chú (.TXT) và file KQ tìm kiếm Shopee TH (.JSON).")
    col1, col2 = st.columns(2)
    with col1:
        vidiq_files = st.file_uploader("1. Tệp Từ khóa (.CSV) & Ghi chú (.TXT)", type=["csv", "txt"], accept_multiple_files=True, key="b1_csv")
    with col2:
        json_files_search = st.file_uploader("2. Tệp Kết quả Shopee TH (.JSON)", type="json", accept_multiple_files=True, key="b1_json")

    if st.button("🚀 Quét & Lọc Bước 1 (Thailand SEO)", type="primary"):
        csv_uploads = [f for f in vidiq_files if f.name.lower().endswith('.csv')] if vidiq_files else []
        txt_uploads = [f for f in vidiq_files if f.name.lower().endswith('.txt')] if vidiq_files else []
        txt_notes_str, txt_kws = parse_txt_notes(txt_uploads)
        combined_niche_notes = "\n".join([s for s in [manual_niche_notes.strip(), txt_notes_str] if s]).strip()

        effective_seed = seed_keywords.strip()
        if not effective_seed and combined_niche_notes:
            m_seed = re.search(r'ĐỊNH HƯỚNG NGÁCH:\s*(.*?)\n', combined_niche_notes)
            if m_seed:
                effective_seed = m_seed.group(1).strip()
        if not effective_seed:
            st.error("⚠️ Vui lòng điền 'Từ khóa ngách'!")
            st.stop()
        if (not csv_uploads and not txt_kws) or not json_files_search:
            st.warning("⚠️ Vui lòng upload đủ file Từ khóa và file Shopee (.JSON)!")
            st.stop()

        with st.status("Đang phân tích từ khóa và lọc 15 sản phẩm trên Shopee TH..."):
            vidiq_df = parse_uploaded_csvs(csv_uploads, txt_kws)
            if vidiq_df.empty:
                st.error("⚠️ Không tìm thấy dữ liệu từ khóa!")
                st.stop()

            csv_data = vidiq_df.to_csv(index=False)
            raw_csv_keywords = vidiq_df['Keyword'].tolist()
            st.write(f"📊 Đã đọc {len(raw_csv_keywords)} từ khóa gốc.")

            json_texts = [f.getvalue().decode("utf-8", errors="ignore") for f in json_files_search]
            shopee_raw_data = parse_shopee_json_search(json_texts)
            if not shopee_raw_data:
                st.error("⚠️ Lỗi bóc tách JSON!")
                st.stop()

            st.write("🧠 AI đang mở rộng bộ từ khóa ภาษาไทย...")
            prompt1 = (P1_TEMPLATE_TH.replace("{csv_data}", csv_data)
                       .replace("{seed_keywords}", effective_seed)
                       .replace("{niche_notes}", combined_niche_notes if combined_niche_notes else "Không có"))
            res1 = call_gemini_with_retry(prompt1, response_mime_type="application/json")
            keywords_json = clean_and_parse_json(res1.text)

            ai_kws_list = keywords_json.get("keywords", []) if isinstance(keywords_json, dict) else []
            existing_set = {str(k.get("keyword", "")).strip().lower() for k in ai_kws_list if isinstance(k, dict)}
            for _, row in vidiq_df.iterrows():
                kw_orig = str(row['Keyword']).strip()
                if kw_orig.lower() not in existing_set:
                    ai_kws_list.append({"keyword": kw_orig, "volume": int(row['Volume'])})
                    existing_set.add(kw_orig.lower())
            keywords_json = {"detected_brands": keywords_json.get("detected_brands", []), "keywords": ai_kws_list}
            st.write(f"✅ Tổng kho từ khóa Thái: {len(ai_kws_list)} từ.")

            st.write("🎯 Đang chọn Top 15 deal Shopee TH...")
            prompt2 = (P2_TEMPLATE_TH.replace("{shopee_data}", json.dumps(shopee_raw_data, ensure_ascii=False))
                       .replace("{keywords_json}", json.dumps(keywords_json, ensure_ascii=False))
                       .replace("{niche_notes}", combined_niche_notes if combined_niche_notes else "Không có"))
            if specific_theme.strip():
                prompt2 += f"\nLƯU Ý CỰC KỲ QUAN TRỌNG: Ưu tiên chọn sản phẩm phù hợp: '{specific_theme}'."
            res2 = call_gemini_with_retry(prompt2, response_mime_type="application/json")
            
            st.session_state['saved_keywords'] = keywords_json
            st.session_state['raw_csv_keywords'] = raw_csv_keywords
            st.session_state['top_15_json'] = clean_and_parse_json(res2.text)
            st.session_state['saved_niche_notes'] = combined_niche_notes
            st.session_state['effective_seed'] = effective_seed

        st.success("✅ Đã chốt danh sách 15 mã Shopee TH!")

    if 'top_15_json' in st.session_state:
        st.markdown("### 🎯 DANH SÁCH 15 LINK SHOPEE THAILAND CẦN LẤY DATA:")
        top_15_data = st.session_state['top_15_json']
        items_list = top_15_data.get('top_15') if isinstance(top_15_data, dict) else (top_15_data if isinstance(top_15_data, list) else [])
        for count, item in enumerate(items_list, 1):
            if isinstance(item, dict):
                url = item.get('url', '')
                pid = item.get('product_id', 'UNKNOWN')
                st.markdown(f'{count}. 👉 **{pid}** - {str(item.get("name", ""))[:45]}... : <a href="{url}" target="_blank">{url}</a>', unsafe_allow_html=True)

# ==========================================
# BƯỚC 2
# ==========================================
with tab2:
    st.info("Upload 15 file .MD chi tiết sản phẩm Shopee TH.")
    col_b2_1, col_b2_2 = st.columns(2)
    with col_b2_1:
        direct_kw_files = st.file_uploader("1. Upload Từ khóa & Ghi chú (Nếu bỏ qua B1):", type=["csv", "txt"], accept_multiple_files=True, key="b2_kw")
    with col_b2_2:
        detailed_md_files = st.file_uploader("2. Upload 15 file .MD Shopee TH:", type="md", accept_multiple_files=True, key="b2_md")

    if st.button("✨ Đạo diễn chọn Top 5 & Xuất Kịch Bản Thái Lan", type="primary"):
        if not detailed_md_files:
            st.warning("⚠️ Vui lòng upload file .MD!")
            st.stop()

        txt_notes_b2, txt_kws_b2 = parse_txt_notes([f for f in direct_kw_files if f.name.lower().endswith('.txt')] if direct_kw_files else [])
        niche_notes_saved = "\n".join([s for s in [manual_niche_notes.strip(), txt_notes_b2, st.session_state.get('saved_niche_notes', '')] if s]).strip()
        effective_seed = seed_keywords.strip() or st.session_state.get('effective_seed', '')
        if not effective_seed:
            st.error("⚠️ BẮT BUỘC: Điền 'Từ khóa ngách'!")
            st.stop()

        with st.status("Đang thiết lập Đội hình & Biên kịch chuẩn Thái (7-8 phút)..."):
            if 'saved_keywords' not in st.session_state or direct_kw_files:
                vidiq_df = parse_uploaded_csvs([f for f in direct_kw_files if f.name.lower().endswith('.csv')] if direct_kw_files else [], txt_kws_b2)
                if not vidiq_df.empty:
                    prompt1 = P1_TEMPLATE_TH.replace("{csv_data}", vidiq_df.to_csv(index=False)).replace("{seed_keywords}", effective_seed).replace("{niche_notes}", niche_notes_saved)
                    res1 = call_gemini_with_retry(prompt1, response_mime_type="application/json")
                    kws = clean_and_parse_json(res1.text).get("keywords", [])
                    st.session_state['saved_keywords'] = {"keywords": kws}
                    st.session_state['raw_csv_keywords'] = vidiq_df['Keyword'].tolist()
                elif 'saved_keywords' not in st.session_state:
                    st.session_state['saved_keywords'] = {"keywords": [{"keyword": effective_seed, "volume": 5000}]}
                    st.session_state['raw_csv_keywords'] = [effective_seed]

            md_contents = [f.getvalue().decode("utf-8", errors="ignore") for f in detailed_md_files]
            scraped_details = parse_detailed_shopee_md(md_contents)

            st.write("👁️ Quét OCR ภาษาไทย...")
            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                scraped_details = list(executor.map(process_single_ocr, scraped_details))

            st.write("⚖️ Chọn Đội hình Top 5...")
            avoid_instruction = f"- Tuyệt đối KHÔNG chọn [{avoid_ch1_products.strip()}] làm Top 1!" if avoid_ch1_products.strip() else ""
            prompt3 = P3_TEMPLATE_TH.replace("{scraped_data}", json.dumps(scraped_details, ensure_ascii=False)).replace("{avoid_ch1_instruction}", avoid_instruction)
            if specific_theme.strip() or niche_notes_saved:
                prompt3 += f"\n\nĐỊNH HƯỚNG NGÁCH: {specific_theme} | {niche_notes_saved}"

            res3 = call_gemini_with_retry(prompt3, response_mime_type="application/json", target_model=PRO_MODEL_ID)
            top5_decision = clean_and_parse_json(res3.text)
            if isinstance(top5_decision, list): top5_decision = top5_decision[0]

            selected_ids = [top5_decision.get('top_5_alternative_1'), top5_decision.get('top_4_alternative_2'), top5_decision.get('top_3_value_for_money'), top5_decision.get('top_2_premium'), top5_decision.get('top_1_best_overall')]
            final_5_data = match_selected_top5(selected_ids, scraped_details)

            matched_keywords = set()
            items_15 = st.session_state.get('top_15_json', {}).get('top_15', [])
            for item in items_15:
                if isinstance(item, dict) and any(str(item.get('product_id', '')) in str(s.get('product_id', '')) for s in final_5_data):
                    for kw in item.get('relevant_keywords', []): matched_keywords.add(str(kw).strip())

            all_kws = sorted(st.session_state['saved_keywords'].get('keywords', []), key=lambda x: int(re.sub(r'[^\d]', '', str(x.get('volume', 0))) or 0), reverse=True)
            combined_seo_kws = list(dict.fromkeys(list(matched_keywords) + st.session_state.get('raw_csv_keywords', []) + [k.get('keyword', '') for k in all_kws]))[:30]

            persona_obj = PERSONA_DICT_TH[selected_persona]
            if trending_memes.strip():
                meme_instruction = f"- **Lồng ghép Trend riêng**: Bắt buộc lồng ghép khéo léo câu [{trending_memes}] vào lời thoại.\n"
            else:
                meme_instruction = ""

            meme_instruction += (
                f"- **CHIẾN THUẬT TỪ LÓNG (SLANG) THÁI LAN THEO NHÂN CÁCH**:\n"
                f"Hãy tham khảo kho từ lóng độc quyền của nhân cách này: \n[{' | '.join(persona_obj['memes'])}]\n"
                f"Quy tắc dùng Slang: KHÔNG nhồi nhét ngẫu nhiên. Hãy dùng nhóm từ 'Cảnh tỉnh/Chê bai' khi phân tích nhược điểm ở phần đầu/giữa sản phẩm, và bung sức dùng nhóm từ 'ป้ายยา (Dụ dỗ/Khen ngợi)' ở cuối đoạn để chốt sale mạnh mẽ."
            )

            st.write("✍️ Đang viết kịch bản chuẩn KOL Thái Lan (3.800 - 4.500 ký tự tiếng Thái)...")
            prompt4 = (P4_TEMPLATE_TH.replace("{final_5_data}", json.dumps(final_5_data, ensure_ascii=False))
                       .replace("{refined_keywords}", ", ".join(combined_seo_kws))
                       .replace("{seed_keywords}", effective_seed)
                       .replace("{niche_notes}", niche_notes_saved)
                       .replace("{selected_persona}", selected_persona)
                       .replace("{persona_traits}", persona_obj["traits"])
                       .replace("{meme_instruction}", meme_instruction))

            res4 = call_gemini_with_retry(prompt4, target_model=PRO_MODEL_ID)
            main_script = res4.text

            for item in final_5_data:
                if item.get('ASSIGNED_RANK'):
                    main_script = main_script.replace(f"{{LINK_{item['ASSIGNED_RANK'].replace('Top ', '').strip()}}}", item.get('url', ''))

            main_script = enforce_tags_section_th(main_script, combined_seo_kws, effective_seed, final_5_data, min_len=300, max_len=450)
            main_script = sanitize_tts_script(main_script)

        tags_match = re.search(r'3\.\s*TAGS\s*:\s*\n?(.*?)(?=\n+\s*4\.\s*SCRIPT\s*:)', main_script, re.DOTALL)
        tags_len = len(tags_match.group(1).strip()) if tags_match else 0
        script_part = main_script.split("4. SCRIPT:")[-1] if "4. SCRIPT:" in main_script else main_script
        thai_char_count = len(re.findall(r'[\u0E00-\u0E7F]', script_part))
        est_minutes = round(thai_char_count / 480, 1)

        st.success(f"🎉 Xuất lò kịch bản Thái! | 🏷️ Tags: **{tags_len} ký tự** | 📝 Số ký tự Thái: **{thai_char_count} chữ** (~{est_minutes} phút đọc)")
        st.text_area("Kịch Bản Hoàn Chỉnh", value=main_script, height=650)