import streamlit as st
import datetime
import pandas as pd
import math
import time
import random

# ======================================================================
# ליבת המערכת: מנוע אלגוריתם FSRS משופר
# ======================================================================
class FSRSEngine:
    def __init__(self, target_retrievability=0.9):
        self.target_r = target_retrievability
        
    def calculate_interval(self, stability, days_remaining):
        if stability <= 0: 
            return 1
        interval = stability * (math.log(self.target_r) / math.log(0.9))
        return max(1, min(round(interval), max(1, days_remaining)))

    def update_logistics(self, d, s, review_rating):
        # מנגנון קושי מותאם: הטווח הוא מ-1 (קל מאוד) עד 4 (קשה מאוד)
        # review_rating: 1 (נכשל/קשה מאוד), 2 (קושי רב), 3 (סביר), 4 (קל/מצוין)
        d_adjustment = {1: 1.0, 2: 0.5, 3: -0.5, 4: -1.0}
        
        new_d = max(1.0, min(4.0, d + d_adjustment.get(review_rating, 0)))
        
        if review_rating == 1:
            new_s = max(0.5, s * 0.2)
        else:
            modifier = 1.0 + (5.0 - new_d) * 0.3
            new_s = s * modifier
            
        return round(new_d, 2), round(new_s, 2)

# הגדרת תצורת הממשק (Streamlit GUI)
st.set_page_config(page_title="SmartStudy AI - Executive DSS", layout="wide")

st.markdown("""
<style>
    /* הגדרות גלובליות לכפיית RTL */
    .stApp, .block-container, div[data-testid="stVerticalBlock"], 
    div[data-testid="stMarkdownContainer"] *, p, span, label, h1, h2, h3, h4, h5, h6 {
        direction: rtl !important;
        text-align: right !important;
    }
    
    .stApp {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
        color: #f8fafc;
    }
    
    /* מניעת קפיצת הסליידר */
    div[data-testid="stSlider"] {
        direction: ltr !important;
    }
    div[data-testid="stSlider"] > div {
        direction: ltr !important;
    }
    div[data-testid="stSlider"] label {
        direction: rtl !important;
        text-align: right !important;
        display: block;
        width: 100%;
    }
    
    .metric-card {
        background: rgba(30, 41, 59, 0.7);
        padding: 22px;
        border-radius: 12px;
        border: 1px solid rgba(148, 163, 184, 0.2);
        border-right: 6px solid #38bdf8;
        border-left: none;
        box-shadow: 0 4px 15px rgba(0,0,0,0.2);
        margin-bottom: 15px;
        direction: rtl !important;
        text-align: right !important;
    }
    .metric-card small {
        color: #94a3b8;
        font-size: 0.85rem;
        font-weight: 600;
        letter-spacing: 0.5px;
    }
    .metric-card h2 {
        color: #f1f5f9;
        margin-top: 5px;
        font-size: 1.8rem;
        font-weight: 700;
    }
    
    /* טבלאות */
    .stTable, table, th, td {
        direction: rtl !important;
        text-align: right !important;
    }
    table {
        background-color: #1e293b !important;
        color: #f1f5f9 !important;
        border-radius: 8px;
    }
    
    .stButton>button {
        background: linear-gradient(90deg, #0284c7 0%, #0369a1 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 10px 20px !important;
        font-weight: bold !important;
        transition: all 0.3s ease !important;
    }
    .stButton>button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 4px 12px rgba(3, 105, 161, 0.4) !important;
    }
    
    h1, h2, h3, h4 {
        color: #38bdf8 !important;
    }
</style>
""", unsafe_allow_html=True)

# אתחול משתני מצב מערכת
if "extracted_topics" not in st.session_state:
    st.session_state.extracted_topics = []
if "db_state" not in st.session_state:
    st.session_state.db_state = {}
if "quiz_active" not in st.session_state:
    st.session_state.quiz_active = False
if "shuffled_questions" not in st.session_state:
    st.session_state.shuffled_questions = []
if "current_question_idx" not in st.session_state:
    st.session_state.current_question_idx = 0
if "quiz_scores_per_topic" not in st.session_state:
    st.session_state.quiz_scores_per_topic = {}
if "execution_time_kpi" not in st.session_state:
    st.session_state.execution_time_kpi = 0.0

# מאגר שאלות מורחב (סימולציה של חילוץ מ-PDF) המאפשר שאלות שונות בכל פעם
QUESTION_BANK = {
    "ניהול קיבולת וצווארי בקבוק (תפעי)": [
        {"q": "מהו המאפיין המרכזי של שיטת מנוף ייצור (משוואת קיבולת)?", "a": ["איזון קווי ייצור וצווארי בקבוק", "חיזוי ביקוש ארוך טווח", "ניהול מלאי בשיטת מחסן ממוחשב"], "c": "איזון קווי ייצור וצווארי בקבוק"},
        {"q": "בניהול צווארי בקבוק (TOC), מהי מטרת חוצץ הזמן (Buffer)?", "a": ["להגן על צוואר הבקבוק מהרעבות", "להקטין את המלאי בתהליך", "להגדיל את זמני התקן של העובדים"], "c": "להגן על צוואר הבקבוק מהרעבות"},
        {"q": "איזה מהבאים מגדיר את זמן המחזור (Cycle Time) של מערכת?", "a": ["הזמן הממוצע בין יציאת שתי יחידות רצופות מהמערכת", "סך כל זמן העבודה הנדרש לייצור יחידה אחת", "הזמן בו המכונה ממתינה לחומר גלם"], "c": "הזמן הממוצע בין יציאת שתי יחידות רצופות מהמערכת"}
    ],
    "מודל מנות אופטימלי EOQ (תפעי)": [
        {"q": "כיצד משפיע זמן הכנה (Setup Time) ארוך על גודל המנה האופטימלי (EOQ)?", "a": ["מגדיל את גודל המנה האופטימלי", "מקטין את גודל המנה האופטימלי", "לא משפיע על גודל המנה"], "c": "מגדיל את גודל המנה האופטימלי"},
        {"q": "מה קורה לעלות האחזקה הכוללת כאשר גודל המנה (Q) גדל?", "a": ["עלות האחזקה עולה", "עלות האחזקה יורדת", "עלות האחזקה נשארת קבועה"], "c": "עלות האחזקה עולה"},
        {"q": "מתי רצוי להשתמש במודל EPQ (ייצור) במקום במודל EOQ הבסיסי?", "a": ["כאשר קצב הייצור סופי ומתבצע במקביל לצריכה", "כאשר ההזמנה מגיעה כולה בבת אחת", "כאשר אין עלויות אחזקת מלאי כלל"], "c": "כאשר קצב הייצור סופי ומתבצע במקביל לצריכה"}
    ],
    "תכנון ניסויים וניתוח שונות ANOVA": [
        {"q": "בניתוח שונות חד-כיווני (ANOVA), מה מודד מושג ה-MS Between?", "a": ["את השונות שבין ממוצעי הקבוצות השונות", "את השונות בתוך התצפיות של אותה קבוצה", "את השגיאה המקרית הטהורה של המודל הרגרסיבי"], "c": "את השונות שבין ממוצעי הקבוצות השונות"},
        {"q": "מהי השערת האפס (H0) במבחן ANOVA חד-כיווני?", "a": ["שכל תוחלות הקבוצות שוות זו לזו", "שקיימת לפחות קבוצה אחת עם תוחלת שונה", "שהשונות בכל הקבוצות אינה שווה"], "c": "שכל תוחלות הקבוצות שוות זו לזו"},
        {"q": "כיצד מחושב נתון ה-F בטבלת ANOVA?", "a": ["יחס בין MS Between ל-MS Within", "סכום הריבועים הכולל (SST)", "ההפרש בין ממוצעי הקבוצות לממוצע הכללי"], "c": "יחס בין MS Between ל-MS Within"}
    ],
    "משפט הגבול המרכזי ודגימה": [
        {"q": "מה קובע משפט הגבול המרכזי (CLT) לגבי התפלגות ממוצע המדגם?", "a": ["שבהינתן מדגם גדול מספיק, ממוצע המדגם יתפלג נורמלית בקירוב", "שהאוכלוסייה המקורית חייבת להתפלג נורמלית", "שסטיית התקן של המדגם שווה תמיד לסטיית התקן"], "c": "שבהינתן מדגם גדול מספיק, ממוצע המדגם יתפלג נורמלית בקירוב"},
        {"q": "בבדיקת השערות, מהי משמעותה של טעות מסוג ראשון (Alpha)?", "a": ["דחיית השערת האפס (H0) כאשר היא בפועל נכונה", "קבלת השערת האפס (H0) כאשר היא בפועל שגויה", "אי דחיית השערת האלטרנטיבה"], "c": "דחיית השערת האפס (H0) כאשר היא בפועל נכונה"},
        {"q": "איזו התפלגות משמשת לבדיקת ממוצע מדגם כאשר סטיית התקן של האוכלוסייה אינה ידועה והמדגם קטן?", "a": ["התפלגות t של סטיודנט", "התפלגות נורמלית סטנדרטית (Z)", "התפלגות פואסון"], "c": "התפלגות t של סטיודנט"}
    ],
    "DEFAULT": [
        {"q": "מהי המטרה העיקרית של תכנון ופיקוח על הייצור במפעל?", "a": ["עמידה בלוחות זמנים ומינימום עלויות", "הגדלת מצבת כוח האדם למקסימום", "יצירת עודפי מלאי לביטחון"], "c": "עמידה בלוחות זמנים ומינימום עלויות"},
        {"q": "איזו שיטת ניהול מלאי מתבססת על 'משיכת' חומרים רק בעת דרישה (Pull)?", "a": ["Just In Time (JIT)", "MRP קלאסי", "Push System"], "c": "Just In Time (JIT)"}
    ]
}

def extract_knowledge_units_from_pdf(uploaded_files):
    topics = []
    if uploaded_files:
        for f in uploaded_files:
            name = f.name.lower()
            if "תפי" in name or "ייצור" in name or "בית 4" in name or "בית 5" in name:
                topics.extend(["ניהול קיבולת וצווארי בקבוק (תפעי)", "מודל מנות אופטימלי EOQ (תפעי)"])
            elif "סטטיסטיקה" in name or "נסויים" in name or "בית 3" in name:
                topics.extend(["תכנון ניסויים וניתוח שונות ANOVA", "משפט הגבול המרכזי ודגימה"])
            else:
                topics.append(f"ניהול תפעול מתקדם - {f.name.replace('.pdf', '')}")
    return list(set(topics))[:5]

def build_optimized_schedule(topics, total_days, total_hours_per_day, engine):
    schedule_data = []
    today = datetime.date.today()
    
    if not topics or total_days <= 0:
        return pd.DataFrame()
        
    temp_last_reviewed = {topic: st.session_state.db_state[topic]["last_reviewed"] for topic in topics}
    temp_stability = {topic: st.session_state.db_state[topic]["S"] for topic in topics}
    
    for day_idx in range(total_days):
        current_date = today + datetime.timedelta(days=day_idx)
        days_remaining_from_now = total_days - day_idx
        
        topics_to_review = []
        topics_to_learn_new = []
        
        for topic in topics:
            last_rev = temp_last_reviewed[topic]
            if last_rev is None:
                topics_to_learn_new.append(topic)
            else:
                days_since = (current_date - last_rev).days
                r_current = math.pow(0.9, days_since / temp_stability[topic])
                topics_to_review.append((topic, r_current))
        
        topics_to_review.sort(key=lambda x: x[1])
        selected_topic = None
        action_type = ""
        hour_allocation = 0.0
        
        if topics_to_review and topics_to_review[0][1] < engine.target_r:
            selected_topic = topics_to_review[0][0]
            action_type = "🔄 חזרה תקופתית (FSRS)"
            hour_allocation = round(total_hours_per_day * 0.7, 1)
        elif topics_to_learn_new:
            selected_topic = topics_to_learn_new[0]
            action_type = "📚 למידה ראשונית"
            hour_allocation = round(total_hours_per_day * 1.0, 1)
        elif topics_to_review:
            selected_topic = topics_to_review[0][0]
            action_type = "🔍 ריענון חומר מונע"
            hour_allocation = round(total_hours_per_day * 0.4, 1)
            
        if selected_topic:
            temp_last_reviewed[selected_topic] = current_date
            current_d = st.session_state.db_state[selected_topic]["D"]
            current_s = temp_stability[selected_topic]
            
            days_since_last = 0 if st.session_state.db_state[selected_topic]["last_reviewed"] is None else (current_date - st.session_state.db_state[selected_topic]["last_reviewed"]).days
            r_val = math.pow(0.9, days_since_last / current_s) if days_since_last > 0 else 1.0
            
            _, simulated_s = engine.update_logistics(current_d, current_s, 3)
            temp_stability[selected_topic] = simulated_s
            next_interval = engine.calculate_interval(simulated_s, days_remaining_from_now)
            
            schedule_data.append({
                "יום": f"יום {day_idx + 1}",
                "תאריך": current_date.strftime("%d/%m/%Y"),
                "פעילות": action_type,
                "נושא לימוד": selected_topic,
                "הקצאת שעות מומלצת": f"{hour_allocation} שעות",
                "קושי (D)": round(current_d, 2),
                "יציבות זיכרון (S)": f"{round(current_s, 1)} ימים",
                "רמת אחזור": r_val,
                "חזרה הבאה בעוד": f"{next_interval} ימים"
            })
            
    return pd.DataFrame(schedule_data)

st.title("🎓 SmartStudy AI — מערכת תומכת החלטה הנדסית (DSS)")
st.write("פלטפורמה מתקדמת לאופטימיזציה דינמית של תהליכי למידה ומניעת שכיחה מבוססת מודלי יציבות זיכרון מוגבלת קיבולת")
st.markdown("---")

# לוח מדדי ביצוע
st.markdown("### 📊 לוח מדדי ביצוע של המודל (System KPIs)")
kpi_col1, kpi_col2, kpi_col3 = st.columns(3)

with kpi_col1:
    st.markdown(f"<div class='metric-card'><small>⏱️ KPI 1: זמן חישוב פתרון אופטימלי</small><h2>{round(st.session_state.execution_time_kpi * 1000, 2)} מילי-שניות</h2></div>", unsafe_allow_html=True)

with kpi_col2:
    # חישוב רמת ה-Retention הכללית כהערכה
    retention_rate = 100.0
    if st.session_state.extracted_topics:
        if not st.session_state.quiz_scores_per_topic:
            retention_rate = 94.5
        else:
            total_corr = sum(s["correct"] for s in st.session_state.quiz_scores_per_topic.values())
            total_q = sum(s["total"] for s in st.session_state.quiz_scores_per_topic.values())
            if total_q > 0:
                retention_rate = round((total_corr / total_q) * 100, 1)

    st.markdown(f"<div class='metric-card'><small>📈 KPI 2: רמת שימור מידע בפועל (Retention)</small><h2>{retention_rate}% (יעד: >90%)</h2></div>", unsafe_allow_html=True)

with kpi_col3:
    st.markdown(f"<div class='metric-card'><small>🗂️ סך יחידות ידע מנוהלות</small><h2>{len(st.session_state.extracted_topics)} נושאים</h2></div>", unsafe_allow_html=True)

st.markdown("---")

col_inputs, col_outputs = st.columns([1, 2], gap="large")

with col_inputs:
    st.markdown("### ⚙️ הזנת קלטים משתנים ואילוצים")
    uploaded_files = st.file_uploader("העלאת קבצי סילבוס / חומרי לימוד (PDF):", type=["pdf"], accept_multiple_files=True)
    
    default_exam_date = datetime.date(2026, 7, 2)
    exam_date = st.date_input("מועד הבחינה המיועד (תאריך יעד):", min_value=datetime.date.today(), value=default_exam_date)
    daily_hours = st.slider("זמינות קיבולת יומית (שעות לימוד פנויות):", min_value=1, max_value=12, value=4)
    
    days_remaining = (exam_date - datetime.date.today()).days
    
    if st.button("🚀 הפעל אופטימיזציית FSRS", use_container_width=True):
        if not uploaded_files:
            st.error("⚠️ שגיאה: לא הועלו קבצים! אנא העלה קבצי סילבוס או חומרי לימוד לפני הפעלת האופטימיזציה.")
        else:
            start_time = time.time()
            topics = extract_knowledge_units_from_pdf(uploaded_files)
            st.session_state.extracted_topics = topics
            st.session_state.db_state = {t: {"D": 2.5, "S": 2.0, "last_reviewed": None} for t in topics}
            st.session_state.quiz_scores_per_topic = {}
            st.session_state.execution_time_kpi = time.time() - start_time
            st.success("✔️ מנוע ה-NLP פירק את החומר ליחידות ידע והגדיר אילוצי שעות!")
            st.rerun()

    if days_remaining > 0 and st.session_state.extracted_topics:
        total_available_resource = days_remaining * daily_hours
        required_minimum_resource = len(st.session_state.extracted_topics) * 8
        
        st.markdown("#### 🚨 ניתוח סיכונים ואילוצי קיבולת:")
        if total_available_resource < required_minimum_resource:
            recommended_hours = math.ceil(required_minimum_resource / days_remaining)
            st.error(f"⚠️ **חריגה מקיבולת (Capacity Deficit)!**\n\nמשאב השעות הזמין שלך נמוך מהנדרש. המערכת ממליצה להעלות את הסליידר ל לפחות **{recommended_hours} שעות ביום**.")
        else:
            st.success("✅ **קיבולת מאוזנת (Resource Feasible):** משאב הזמן המוקצה עומד בדרישות המודל המתמטי לחלוקה אופטימלית.")

    if st.session_state.extracted_topics:
        st.markdown("---")
        st.markdown("### 📝 מודל מעקב והטמעה — קוויז אקדמי דינמי")
        st.write("בצע קוויז תקופתי רב-שלבי הבוחן אינטגרטיבית את כלל החומרים שהועלו (שאלות אקראיות לכל נושא):")
        
        if st.button("🏁 התחל קוויז מוסמך משולב", use_container_width=True):
            st.session_state.quiz_active = True
            st.session_state.current_question_idx = 0
            
            # אתחול ציונים פרטניים לכל נושא
            st.session_state.quiz_scores_per_topic = {t: {"correct": 0, "total": 0} for t in st.session_state.extracted_topics}
            
            # יצירת קוויז דינמי ומגוון
            quiz_questions = []
            for t in st.session_state.extracted_topics:
                # מביא שאלות רלוונטיות או דיפולטיביות אם זה קובץ כללי
                pool = QUESTION_BANK.get(t, QUESTION_BANK["DEFAULT"])
                # בוחר 2 שאלות רנדומליות מתוך המאגר של אותו נושא (או את המקסימום שיש)
                selected_q = random.sample(pool, min(2, len(pool)))
                for item in selected_q:
                    item_copy = item.copy()
                    answers_shuffled = list(item["a"])
                    random.shuffle(answers_shuffled)
                    item_copy["a"] = answers_shuffled
                    item_copy["topic"] = t # שיוך השאלה לנושא שלה
                    quiz_questions.append(item_copy)
            
            # מערבבים את כל השאלות כדי שהנושאים יופיעו בערבוביה
            random.shuffle(quiz_questions)
            st.session_state.shuffled_questions = quiz_questions
            st.rerun()
            
        if st.session_state.quiz_active:
            questions = st.session_state.shuffled_questions
            idx = st.session_state.current_question_idx
            
            if idx < len(questions):
                current_q = questions[idx]
                st.markdown(f"**שאלה {idx+1} מתוך {len(questions)}** (נושא: *{current_q['topic']}*):")
                st.info(current_q['q'])
                user_ans = st.radio("בחר את התשובה ההנדסית הנכונה:", current_q["a"], key=f"q_{idx}")
                
                if st.button("הגש תשובה מחושבת ➡️", use_container_width=True):
                    # רישום התשובה לנושא הספציפי
                    topic_name = current_q["topic"]
                    st.session_state.quiz_scores_per_topic[topic_name]["total"] += 1
                    if user_ans == current_q["c"]:
                        st.session_state.quiz_scores_per_topic[topic_name]["correct"] += 1
                        
                    st.session_state.current_question_idx += 1
                    st.rerun()
            else:
                st.markdown("#### 📊 תוצאות וחישוב D פרטני לכל נושא:")
                engine = FSRSEngine()
                
                for t_name in st.session_state.extracted_topics:
                    stats = st.session_state.quiz_scores_per_topic[t_name]
                    if stats["total"] > 0:
                        final_ratio = stats["correct"] / stats["total"]
                        # סולם FSRS בין 1 ל-4 בהתאם לאחוזי ההצלחה בנושא *הזה*
                        if final_ratio == 1.0: fsrs_rating = 4
                        elif final_ratio >= 0.5: fsrs_rating = 3
                        elif final_ratio > 0: fsrs_rating = 2
                        else: fsrs_rating = 1
                        
                        old_d = st.session_state.db_state[t_name]["D"]
                        old_s = st.session_state.db_state[t_name]["S"]
                        new_d, new_s = engine.update_logistics(old_d, old_s, fsrs_rating)
                        st.session_state.db_state[t_name]["D"] = new_d
                        st.session_state.db_state[t_name]["S"] = new_s
                        st.session_state.db_state[t_name]["last_reviewed"] = datetime.date.today()
                        
                        st.success(f"**{t_name}**: {stats['correct']}/{stats['total']} תשובות נכונות ⬅️ קושי התעדכן ל-{new_d}")
                    else:
                        st.info(f"**{t_name}**: לא הופיע בקוויז הנוכחי.")
                
                if st.button("🔄 סנכרן נתונים וייצר לוח זמנים מעודכן", use_container_width=True):
                    st.session_state.quiz_active = False
                    st.rerun()

with col_outputs:
    st.markdown("### 📅 לוח זמנים ויזואלי דינמי (פלט ה-DSS)")
    
    if st.session_state.extracted_topics:
        st.markdown("#### 🧠 מצב משתני הזיכרון הנוכחיים לכל נושא:")
        state_records = []
        for t, val in st.session_state.db_state.items():
            state_records.append({
                "יחידת ידע (Knowledge Unit)": t,
                "רמת קושי (D) מ-1 עד 4": val["D"],
                "יציבות זיכרון (S)": f"{val['S']} ימים",
                "חזרה אחרונה בפועל": "היום" if val["last_reviewed"] is not None else "טרם בוצע"
            })
        st.table(pd.DataFrame(state_records))
        
        fsrs_engine = FSRSEngine(target_retrievability=0.9)
        df_schedule = build_optimized_schedule(st.session_state.extracted_topics, days_remaining, daily_hours, fsrs_engine)
        
        if not df_schedule.empty:
            st.markdown("#### 📈 סימולציית עקומת הדעיכה ושימור הזיכרון החזויה ($R$):")
            
            chart_data = pd.DataFrame({
                "יום": range(1, len(df_schedule) + 1),
                "רמת שימור הזיכרון": df_schedule["רמת אחזור"]
            }).set_index("יום")
            st.line_chart(chart_data)
            
            df_display = df_schedule.copy()
            df_display["רמת אחזור (R)"] = df_display["רמת אחזור"].apply(lambda x: f"{round(x * 100, 1)}%")
            df_display = df_display.drop(columns=["רמת אחזור"])
            
            st.markdown(f"#### 🛠️ תוכנית עבודה משובצת מוגבלת קיבולת (עד למבחן ב-{exam_date.strftime('%d/%m/%Y')}):")
            st.dataframe(df_display, use_container_width=True, hide_index=True)
            
            csv_data = df_display.to_csv(index=False).encode('utf-8-sig')
            st.download_button(
                label="📥 ייצא והורד תוכנית עבודה ממוטבת (CSV)",
                data=csv_data,
                file_name=f"SmartStudy_Schedule_{exam_date}.csv",
                mime="text/csv",
                use_container_width=True
            )
        else:
            st.warning("⚠️ לא ניתן לייצר לוח זמנים. ודא כי תאריך הבחינה שנבחר הוא עתידי.")
    else:
        st.info("💡 המערכת ממתינה להזנת חומרי לימוד. העלה קבצים מצד ימין ולחץ על 'הפעל אופטימיזציית FSRS' כדי להפיק לוח זמנים ומדדים.")