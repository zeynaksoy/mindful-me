import json
import os
from datetime import datetime, timedelta
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, session, current_app
from werkzeug.utils import secure_filename
from app.forms import MoodEntryForm, ProfileForm, ForgotPasswordForm, ResetPasswordForm, ChangePasswordForm
from app.models import MoodEntry, User
from app import db, mail, scheduler
from flask_mail import Message
from itsdangerous import URLSafeTimedSerializer
from flask_babel import gettext as _, lazy_gettext as _l
from app.email import send_password_reset_email

main = Blueprint('main', __name__)

@main.before_request
def check_pending_notifications():
    try:
        user = User.query.first()
        if user:
            user.last_login = datetime.utcnow()
            if getattr(user, 'pending_notification', None):
                flash(user.pending_notification)
                user.pending_notification = None
            db.session.commit()
    except Exception:
        db.session.rollback()

@scheduler.task('cron', id='check_daily_moods', hour=20, minute=0)
def check_daily_moods():
    with scheduler.app.app_context():
        users = User.query.all()
        today = datetime.utcnow().date()
        yesterday = today - timedelta(days=1)
        for user in users:
            if getattr(user, 'last_login', None) and (datetime.utcnow() - user.last_login).days <= 2:
                # Bugunun kaydi var mi? (Tek kullanicili sistem oldugu icin genel kontrol)
                today_entry = MoodEntry.query.filter(db.func.date(MoodEntry.timestamp) == today).first()
                if not today_entry:
                    yesterday_entry = MoodEntry.query.filter(db.func.date(MoodEntry.timestamp) == yesterday).first()
                    if yesterday_entry and (getattr(yesterday_entry, 'stress_level', 0) > 7 or yesterday_entry.mood in ['stresli', 'uzgun']):
                        user.pending_notification = _l("Dün kötü hissettiğini belirtmiştin, bugün nasılsın?")
                    else:
                        user.pending_notification = _l("Bugünkü ruh halini kaydetmek ister misin?")
        db.session.commit()

@main.context_processor
def inject_moods():
    return dict(MOOD_DATA=[
        {'value': 'mutlu', 'label': _('Mutlu'), 'emoji': '😄'},
        {'value': 'sakin', 'label': _('Sakin'), 'emoji': '😌'},
        {'value': 'odaklanmis', 'label': _('Odaklanmış'), 'emoji': '🎯'},
        {'value': 'yaratici', 'label': _('Yaratıcı'), 'emoji': '🎨'},
        {'value': 'heyecanli', 'label': _('Heyecanlı'), 'emoji': '🤩'},
        {'value': 'stresli', 'label': _('Stresli'), 'emoji': '😰'},
        {'value': 'bitkin', 'label': _('Bitkin'), 'emoji': '😫'},
        {'value': 'uzgun', 'label': _('Üzgün'), 'emoji': '😢'}
    ])

MOOD_VALUES = {
    'heyecanli': 5,
    'mutlu': 4,
    'odaklanmis': 4,
    'yaratici': 4,
    'sakin': 3,
    'stresli': 2,
    'bitkin': 1,
    'uzgun': 1
}

SUGGESTIONS = {
    'heyecanli': _l('Harika bir enerji! Bu enerjiyi yaratıcı bir hobiye veya spora yönlendirmeyi dene.'),
    'mutlu': _l('Bu anı bir kutlama ile taçlandır! Kendine sevdiğin bir içecek ısmarla veya en sevdiğin şarkıyı dinle.'),
    'odaklanmis': _l('Zihnin çok berrak. Önemli bir görevi bitirmek veya yeni bir şey öğrenmek için mükemmel bir zaman.'),
    'yaratici': _l('İlham perilerin seninle! Bir şeyler çizmeyi, yazmayı veya yeni bir fikir üretmeyi dene.'),
    'sakin': _l('Bu huzurlu anın tadını çıkar. Birkaç sayfa kitap okumak veya kısa bir yürüyüş için harika bir zaman.'),
    'stresli': _l('Derin bir nefes al... Omuzlarını serbest bırak. Gözlerini kapatıp 2 dakika sadece durmayı dene.'),
    'bitkin': _l('Vücudunun dinlenmeye ihtiyacı var. Belki kısa bir şekerleme yapabilir veya sadece uzanıp müzik dinleyebilirsin.'),
    'uzgun': _l('Bir bardak su iç ve kendine sarıl. Duygularını hissetmek tamamen normal, geçici olduklarını unutma.')
}

def analyze_journal_entry(mood, text, free_writing=None):
    analysis_text = free_writing if free_writing and len(free_writing.strip()) > 5 else text
    words = analysis_text.lower().replace('.', '').replace(',', '').split() if analysis_text else []
    stop_words = ['bir', 've', 'ile', 'çok', 'için', 'daha', 'bu', 'şu', 'o', 'ama', 'fakat']
    keywords_list = [w for w in words if w not in stop_words and len(w) > 3][:3]
    keywords = ", ".join(keywords_list) if keywords_list else mood
    
    if not analysis_text or len(analysis_text.strip()) < 5:
        sentiment = _("Nötr")
        score = 5
        translated_mood = _(mood.capitalize())
        analysis = _("%(mood)s bir ruh hali içindesin.", mood=translated_mood)
        advice = _("Daha fazla detay yazarsan sana özel yapay zeka tavsiyeleri verebilirim.")
    else:
        if mood in ['uzgun', 'stresli']:
            sentiment = _("Negatif")
            score = 3 if mood == 'uzgun' else 4
            analysis = _("Yazdıklarında belirgin bir yoğunluk seziyorum.")
            advice = _("Belki de şu an kendine biraz daha şefkat göstermelisin. 5 dakikalık bir nefes egzersizi iyi gelebilir.")
        elif mood in ['mutlu', 'heyecanli']:
            sentiment = _("Pozitif")
            score = 9 if mood == 'mutlu' else 8
            analysis = _("Harika! Bu pozitif anın tadını çıkardığın yazdıklarından belli.")
            advice = _("Bu enerjiyi çevrendekilerle paylaşabilir veya bu anın neden güzel olduğunu not edebilirsin.")
        else:
            sentiment = _("Nötr")
            score = 6
            analysis = _("Dengeli ve merkezinde görünüyorsun.")
            advice = _("Günün geri kalanında bu dengeyi korumak için kısa bir yürüyüş yapabilirsin.")
            
    return sentiment, score, keywords, analysis, advice

def analyze_data(entries):
    try:
        if not entries:
            return _("Yeterli veri yok. Analiz için daha fazla günlük girmelisin.")
        
        activity_moods = {}
        total_moods = []
        
        for entry in entries:
            val = MOOD_VALUES.get(entry.mood, 3)
            total_moods.append(val)
            if entry.activities:
                acts = [a.strip().lower() for a in entry.activities.split(',')]
                for act in acts:
                    if act:
                        if act not in activity_moods:
                            activity_moods[act] = []
                        activity_moods[act].append(val)
                        
        avg_total = sum(total_moods) / len(total_moods) if total_moods else 3
        insights = []
        
        best_act = None
        best_diff = 0
        for act, moods in activity_moods.items():
            if len(moods) >= 1:
                avg_act = sum(moods) / len(moods)
                diff = ((avg_act - avg_total) / avg_total) * 100 if avg_total > 0 else 0
                if diff > best_diff:
                    best_diff = diff
                    best_act = act
                    
        if best_act and best_diff > 0:
            insights.append(_("'%(act)s' yaptığın günlerde mutluluk ortalaman %(diff)s daha yüksek.", act=best_act.title(), diff=f"%{int(best_diff)}"))
            
        high_sleep_moods = [MOOD_VALUES.get(e.mood, 3) for e in entries if e.sleep_hours and e.sleep_hours >= 7]
        low_sleep_moods = [MOOD_VALUES.get(e.mood, 3) for e in entries if e.sleep_hours and e.sleep_hours < 7]
        
        if high_sleep_moods and low_sleep_moods:
            avg_high = sum(high_sleep_moods) / len(high_sleep_moods)
            avg_low = sum(low_sleep_moods) / len(low_sleep_moods)
            if avg_high > avg_low:
                insights.append(_("7 saat ve üzeri uyuduğunda kendini daha pozitif hissediyorsun."))
                
        high_stress = [e for e in entries if e.stress_level and e.stress_level >= 7]
        if high_stress:
            insights.append(_("Bazı günlerde stres seviyen yüksek çıkmış, nefes egzersizlerini artırabilirsin."))
            
        if not insights:
            return _("Henüz belirgin bir korelasyon bulamadım, günlüğünü doldurmaya devam et!")
            
        return " ".join(insights)
    except Exception as e:
        return _("Analiz kısmında küçük bir pürüz oluştu, yeni kayıtlar ekledikçe düzelecektir.")

def get_mood_history():
    try:
        thirty_days_ago = datetime.utcnow() - timedelta(days=29)
        recent_entries = MoodEntry.query.filter(MoodEntry.timestamp >= thirty_days_ago).order_by(MoodEntry.timestamp.asc()).all()
        
        daily_data = {}
        for e in recent_entries:
            if not e.timestamp: continue
            date_str = e.timestamp.strftime('%Y-%m-%d')
            daily_data[date_str] = {
                'mood': e.mood,
                'text': (e.text[:50] + '...') if len(e.text) > 50 else e.text,
                'date': e.timestamp.strftime('%d %b')
            }
            
        history = []
        for i in range(29, -1, -1):
            day = datetime.utcnow() - timedelta(days=i)
            date_str = day.strftime('%Y-%m-%d')
            if date_str in daily_data:
                history.append(daily_data[date_str])
            else:
                history.append({
                    'mood': None,
                    'text': 'Kayıt yok',
                    'date': day.strftime('%d %b')
                })
                
        return history
    except Exception as e:
        return []

def check_badges(user):
    if not user: return
    recent_entries = MoodEntry.query.order_by(MoodEntry.timestamp.desc()).limit(3).all()
    if len(recent_entries) == 3:
        all_good = True
        for e in recent_entries:
            if getattr(e, 'sleep_hours', None) is None or float(e.sleep_hours) < 8:
                all_good = False
                break
        if all_good and not getattr(user, 'has_sleep_master_badge', False):
            user.has_sleep_master_badge = True
            try:
                db.session.commit()
            except Exception:
                db.session.rollback()

def get_lifestyle_feedback():
    recent_entries = MoodEntry.query.order_by(MoodEntry.timestamp.desc()).limit(6).all()
    if len(recent_entries) >= 6:
        latest = recent_entries[:3]
        previous = recent_entries[3:]
        
        def avg_screen(entries):
            vals = [e.screen_time for e in entries if getattr(e, 'screen_time', None) is not None]
            return sum(vals)/len(vals) if vals else 0
            
        def avg_sleep_q(entries):
            vals = [int(e.sleep_quality) for e in entries if getattr(e, 'sleep_quality', None) is not None and str(e.sleep_quality).isdigit()]
            return sum(vals)/len(vals) if vals else 0
            
        latest_screen = avg_screen(latest)
        prev_screen = avg_screen(previous)
        latest_sleep = avg_sleep_q(latest)
        prev_sleep = avg_sleep_q(previous)
        
        if latest_screen > prev_screen and latest_sleep < prev_sleep and prev_sleep > 0:
            decrease_percent = ((prev_sleep - latest_sleep) / prev_sleep) * 100
            return _("Son 3 gündür ekran süren arttığı için uyku kaliten %% %(pct)d düşmüş. Bugün ekranı 2 saat erken kapatmaya ne dersin?", pct=int(decrease_percent))
    return None

def get_best_feeling_activities(entries):
    activity_scores = {}
    activity_counts = {}
    for e in entries:
        if getattr(e, 'activity_type', None):
            score = MOOD_VALUES.get(e.mood, 3)
            act = e.activity_type
            activity_scores[act] = activity_scores.get(act, 0) + score
            activity_counts[act] = activity_counts.get(act, 0) + 1
            
    averages = {}
    for act, total_score in activity_scores.items():
        averages[act] = total_score / activity_counts[act]
        
    sorted_acts = sorted(averages.items(), key=lambda item: item[1], reverse=True)
    
    top_3 = []
    emojis = {
        'Spor': '🏃‍♂️', 'Sosyal': '👥', 'Ders/İş': '💻', 
        'Oyun': '🎮', 'Meditasyon': '🧘‍♀️', 'Müzik': '🎵', 
        'Doğa Yürüyüşü': '🌲'
    }
    for act, avg in sorted_acts[:3]:
        top_3.append({
            'name': act,
            'icon': emojis.get(act, '⭐'),
            'score': round(avg, 1)
        })
    return top_3

def calculate_lifestyle_insights(entries):
    insights = []
    if not entries:
        return [{'icon': '📊', 'text': _('Yeterli veri biriktiğinde kişisel içgörüleriniz burada görünecek.')}]
        
    low_sleep_stress = []
    caffeine_sleep = []
    high_quality_mood = []
    
    for e in entries:
        sq = getattr(e, 'sleep_quality', None)
        sq_val = int(sq) if sq and str(sq).isdigit() else None
        cf = getattr(e, 'caffeine_intake', None)
        stress = getattr(e, 'stress_level', None)
        sleep_h = getattr(e, 'sleep_hours', None)
        
        if sleep_h is not None and stress is not None:
            if sleep_h < 6:
                low_sleep_stress.append(stress)
                
        if cf is not None and sq_val is not None:
            if cf >= 3:
                caffeine_sleep.append(sq_val)
                
        if sq_val is not None and sq_val >= 4:
            high_quality_mood.append(e.mood)
            
    if low_sleep_stress and sum(low_sleep_stress)/len(low_sleep_stress) >= 6:
        insights.append({'icon': '⚠️', 'text': _('6 saatten az uyuduğunuz günlerde stres seviyeniz genel olarak yüksek.')})
        
    if caffeine_sleep and sum(caffeine_sleep)/len(caffeine_sleep) <= 3:
        insights.append({'icon': '☕', 'text': _('3 fincandan fazla kafein aldığınızda uyku kaliteniz genelde düşüyor.')})
        
    if high_quality_mood:
        good_moods = [m for m in high_quality_mood if m in ['mutlu', 'heyecanli', 'sakin']]
        if len(good_moods) / len(high_quality_mood) > 0.5:
            insights.append({'icon': '✨', 'text': _('İyi uyuduğunuz günlerde ruh haliniz belirgin şekilde daha pozitif!')})
            
    if not insights:
        insights.append({'icon': '📊', 'text': _('İçgörü oluşturmak için birkaç gün daha veri girmeye devam edin.')})
        
    return insights

def analyze_patterns(entries=None):
    if not entries:
        try:
            thirty_days_ago = datetime.utcnow() - timedelta(days=30)
            entries = MoodEntry.query.filter(MoodEntry.timestamp >= thirty_days_ago).all()
        except:
            return []

    patterns = []
    if len(entries) < 3:
        return patterns

    day_stress = {i: [] for i in range(7)}
    day_names = [_('Pazartesi'), _('Salı'), _('Çarşamba'), _('Perşembe'), _('Cuma'), _('Cumartesi'), _('Pazar')]
    
    high_screen_moods = []
    low_screen_moods = []
    
    high_caf_sleep_q = []
    low_caf_sleep_q = []

    for e in entries:
        if not e.timestamp: continue
        
        # 1. Zaman Analizi (Haftalık Döngü)
        day_idx = e.timestamp.weekday()
        if getattr(e, 'stress_level', None) is not None:
            day_stress[day_idx].append(e.stress_level)

        # 2. Tetikleyici Analizi (Ekran Süresi)
        scr = getattr(e, 'screen_time', None)
        if scr is not None:
            score = MOOD_VALUES.get(e.mood, 3)
            if scr > 5:
                high_screen_moods.append(score)
            else:
                low_screen_moods.append(score)

        # 3. İçerik Analizi (Kafein - Uyku)
        sq = getattr(e, 'sleep_quality', None)
        cf = getattr(e, 'caffeine_intake', None)
        if sq is not None and str(sq).isdigit() and cf is not None:
            if cf >= 3:
                high_caf_sleep_q.append(int(sq))
            else:
                low_caf_sleep_q.append(int(sq))

    # Zaman
    for day_idx, stresses in day_stress.items():
        if len(stresses) >= 2:
            avg_stress = sum(stresses) / len(stresses)
            if avg_stress >= 7:
                patterns.append(_("Zaman Analizi: %(day)s günleri stres seviyeniz belirgin şekilde yükseliyor.", day=day_names[day_idx]))

    # Ekran
    if len(high_screen_moods) >= 2 and len(low_screen_moods) >= 2:
        avg_high = sum(high_screen_moods) / len(high_screen_moods)
        avg_low = sum(low_screen_moods) / len(low_screen_moods)
        if avg_high < avg_low - 0.5:
            patterns.append(_("Tetikleyici Analizi: Ekran süreniz 5 saati geçtiğinde mutluluk skorunuz düşüyor."))

    # Kafein
    if len(high_caf_sleep_q) >= 2 and len(low_caf_sleep_q) >= 2:
        avg_high_caf = sum(high_caf_sleep_q) / len(high_caf_sleep_q)
        avg_low_caf = sum(low_caf_sleep_q) / len(low_caf_sleep_q)
        if avg_high_caf < avg_low_caf - 0.5:
            patterns.append(_("İçerik Analizi: Kafein sonrası uyku kalitesi düşüyor."))

    return patterns

def generate_comprehensive_report(entries):
    report = {
        'insights': [],
        'sleep_vs_stress': {'labels': [], 'data': []},
        'caffeine_sleep_stress': [],
        'screen_time_vs_stress': {'labels': [_('0-2 saat'), _('2-5 saat'), _('5+ saat')], 'data': [0, 0, 0]}
    }
    if not entries:
        return json.dumps(report)
        
    sleep_stress = {1: [], 2: [], 3: [], 4: [], 5: []}
    caffeine_sleep_stress_list = []
    screen_time_stress = {'0-2': [], '2-5': [], '5+': []}
    
    for e in entries:
        st = getattr(e, 'stress_level', None)
        if st is None: continue
            
        sq = getattr(e, 'sleep_quality', None)
        if sq is not None and str(sq).isdigit() and int(sq) in sleep_stress:
            sleep_stress[int(sq)].append(st)
            
        cf = getattr(e, 'caffeine_intake', None)
        sh = getattr(e, 'sleep_hours', None)
        if cf is not None and sh is not None:
            caffeine_sleep_stress_list.append({
                'x': cf,
                'y': sh,
                'r': st * 3, # Bubble size
                'stress': st
            })
            
        scr = getattr(e, 'screen_time', None)
        if scr is not None:
            if scr <= 2: screen_time_stress['0-2'].append(st)
            elif scr <= 5: screen_time_stress['2-5'].append(st)
            else: screen_time_stress['5+'].append(st)
            
    for i in range(1, 6):
        report['sleep_vs_stress']['labels'].append(_('Kalite %(num)s', num=i))
        if sleep_stress[i]:
            report['sleep_vs_stress']['data'].append(round(sum(sleep_stress[i])/len(sleep_stress[i]), 1))
        else:
            report['sleep_vs_stress']['data'].append(0)
            
    if screen_time_stress['0-2']: report['screen_time_vs_stress']['data'][0] = round(sum(screen_time_stress['0-2'])/len(screen_time_stress['0-2']), 1)
    if screen_time_stress['2-5']: report['screen_time_vs_stress']['data'][1] = round(sum(screen_time_stress['2-5'])/len(screen_time_stress['2-5']), 1)
    if screen_time_stress['5+']: report['screen_time_vs_stress']['data'][2] = round(sum(screen_time_stress['5+'])/len(screen_time_stress['5+']), 1)
        
    report['caffeine_sleep_stress'] = caffeine_sleep_stress_list
    
    high_caf_low_sleep = [item['stress'] for item in caffeine_sleep_stress_list if item['x'] > 3 and item['y'] < 6]
    low_caf_good_sleep = [item['stress'] for item in caffeine_sleep_stress_list if item['x'] <= 3 and item['y'] >= 7]
    
    if high_caf_low_sleep and low_caf_good_sleep:
        avg_bad = sum(high_caf_low_sleep)/len(high_caf_low_sleep)
        avg_good = sum(low_caf_good_sleep)/len(low_caf_good_sleep)
        if avg_bad > avg_good:
            diff = avg_bad - avg_good
            report['insights'].append(_('Yüksek kafein alıp az uyuduğunuz günlerde stres seviyeniz, iyi uyuduğunuz günlere kıyasla ortalama %(diff).1f puan daha yüksek.', diff=diff))

    return json.dumps(report)


@main.route('/', methods=['GET', 'POST'])
def index():
    form = MoodEntryForm()
    if form.validate_on_submit():
        sentiment, score, keywords, analysis, advice = analyze_journal_entry(form.mood.data, form.text.data, form.free_writing.data)
        entry = MoodEntry(
            mood=form.mood.data, 
            text=form.text.data,
            mini_journal=form.mini_journal.data,
            free_writing=form.free_writing.data,
            sleep_hours=form.sleep_hours.data,
            stress_level=form.stress_level.data,
            activities=form.activities.data,
            activity_type=form.activity_type.data,
            ai_analysis=analysis,
            ai_advice=advice,
            ai_sentiment=sentiment,
            ai_score=score,
            ai_keywords=keywords,
            bedtime=form.bedtime.data,
            wakeup_time=form.wakeup_time.data,
            sleep_quality=int(form.sleep_quality.data) if form.sleep_quality.data and str(form.sleep_quality.data).isdigit() else None,
            dream_note=form.dream_note.data,
            caffeine_intake=form.caffeine_intake.data,
            screen_time=form.screen_time.data
        )
        
        # Uyku analizi (sleep_hours 6'dan az ise uyarı ekle)
        if entry.sleep_hours and float(entry.sleep_hours) < 6:
            entry.ai_advice = "Uykunu 6 saatin altında aldığında stres seviyenin arttığını fark ettim. Bugün biraz daha erken yatmaya ne dersin?"
            
        db.session.add(entry)
        
        # Streak (Seri) Hesaplama
        try:
            user = User.query.first()
            if user:
                today = datetime.utcnow().date()
                last_date = getattr(user, 'last_entry_date', None)
                current_streak = getattr(user, 'streak_count', 0) or 0
                
                if last_date:
                    diff = (today - last_date).days
                    if diff == 1:
                        user.streak_count = current_streak + 1
                    elif diff > 1:
                        user.streak_count = 1
                else:
                    user.streak_count = 1
                user.last_entry_date = today
            db.session.commit()
        except Exception:
            db.session.rollback()
        return redirect(url_for('main.index'))
    
    search_query = request.args.get('search', '')
    sort_order = request.args.get('sort', 'desc')
    
    query = MoodEntry.query
    if search_query:
        query = query.filter(MoodEntry.text.ilike(f'%{search_query}%') | MoodEntry.mood.ilike(f'%{search_query}%'))
        
    if sort_order == 'asc':
        query = query.order_by(MoodEntry.timestamp.asc())
    else:
        query = query.order_by(MoodEntry.timestamp.desc())
        
    entries = query.all()
    
    # Duygusal Destek Merkezi Kontrolü
    show_emotional_support = False
    motivation_quote = ""
    if entries:
        latest = entries[0]
        text_to_check = f"{latest.text or ''} {getattr(latest, 'mini_journal', '') or ''} {getattr(latest, 'free_writing', '') or ''}".lower()
        if (latest.ai_score is not None and latest.ai_score < 5) or any(w in text_to_check for w in ['stresli', 'yorgun']):
            show_emotional_support = True
            import random
            quotes = [
                _("Nefes al, bu sadece kötü bir an, kötü bir hayat değil."),
                _("Senin değerin hissettiğin stresten çok daha büyük."),
                _("Şu an her şey üstüne geliyor gibi olabilir, sadece dur ve derin bir nefes al."),
                _("Zor zamanlar güçlü insanlar yaratır, yapabilirsin."),
                _("Bugün sadece kendine iyi davranmaya odaklan.")
            ]
            motivation_quote = random.choice(quotes)
    
    # Strategy 2: Görev Motoru (Son kayda göre dinamik öneri)
    current_suggestion = None
    if entries:
        current_suggestion = SUGGESTIONS.get(entries[0].mood, _("Bugün kendine iyi davranmayı unutma."))

    # Strategy 1: Duygu Haritası Grafiği Verisi (Son 7 Gün)
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    recent_entries = MoodEntry.query.filter(MoodEntry.timestamp >= seven_days_ago).order_by(MoodEntry.timestamp.asc()).all()
    
    daily_moods = {}
    for e in recent_entries:
        if not e.timestamp: continue
        date_str = e.timestamp.strftime('%d %b')
        val = MOOD_VALUES.get(e.mood, 3)
        if date_str not in daily_moods:
            daily_moods[date_str] = []
        daily_moods[date_str].append(val)
        
    chart_labels = []
    chart_data = []
    
    for i in range(6, -1, -1):
        day = datetime.utcnow() - timedelta(days=i)
        date_str = day.strftime('%d %b')
        chart_labels.append(date_str)
        if date_str in daily_moods:
            avg = sum(daily_moods[date_str]) / len(daily_moods[date_str])
            chart_data.append(round(avg, 1))
        else:
            chart_data.append(None) # Veri olmayan günleri atla (spanGaps: true ile birleşecek)
            
    chart_json = {
        'labels': chart_labels,
        'data': chart_data
    }
    
    # Akıllı Analiz
    entries_for_stats = MoodEntry.query.order_by(MoodEntry.timestamp.desc()).all()
    smart_insight = analyze_data(entries_for_stats)

    # Activity Correlation Data
    activity_counts = {}
    activity_mood_sum = {}
    for e in entries_for_stats:
        if e.activities:
            acts = [a.strip().lower() for a in e.activities.split(',')]
            for act in acts:
                if act:
                    activity_counts[act] = activity_counts.get(act, 0) + 1
                    activity_mood_sum[act] = activity_mood_sum.get(act, 0) + MOOD_VALUES.get(e.mood, 3)
                    
    act_labels = []
    act_data = []
    for act, count in sorted(activity_counts.items(), key=lambda x: x[1], reverse=True)[:5]: # top 5
        act_labels.append(act.title())
        act_data.append(round(activity_mood_sum[act] / count, 1))
        
    correlation_chart_json = json.dumps({'labels': act_labels, 'data': act_data})
    
    # Heatmap Data (Last 7 days intensity)
    heatmap_data = []
    for i in range(6, -1, -1):
        day = datetime.utcnow() - timedelta(days=i)
        date_str = day.strftime('%Y-%m-%d')
        count = sum(1 for e in entries_for_stats if e.timestamp and e.timestamp.strftime('%Y-%m-%d') == date_str)
        heatmap_data.append({'x': day.strftime('%d %b'), 'y': 'Kayıt', 'v': count})
        
    heatmap_json = json.dumps(heatmap_data)
    
    mood_history = get_mood_history()
    comp_report = generate_comprehensive_report(entries_for_stats)
    
    return render_template('index.html', form=form, entries=entries, suggestion=current_suggestion, 
                           chart_json=json.dumps(chart_json), search_query=search_query, sort_order=sort_order,
                           smart_insight=smart_insight, correlation_chart_json=correlation_chart_json, 
                           heatmap_json=heatmap_json, mood_history=mood_history, comp_report=comp_report,
                           show_emotional_support=show_emotional_support, motivation_quote=motivation_quote)

@main.route('/delete/<int:id>', methods=['POST'])
def delete_entry(id):
    entry = MoodEntry.query.get_or_404(id)
    db.session.delete(entry)
    db.session.commit()
    return redirect(url_for('main.index'))

@main.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit_entry(id):
    entry = MoodEntry.query.get_or_404(id)
    form = MoodEntryForm(obj=entry)
    
    if form.validate_on_submit():
        entry.mood = form.mood.data
        entry.text = form.text.data
        entry.mini_journal = form.mini_journal.data
        entry.free_writing = form.free_writing.data
        entry.sleep_hours = form.sleep_hours.data
        entry.stress_level = form.stress_level.data
        entry.activities = form.activities.data
        
        # Need to re-analyze AI stats because text changed
        sentiment, score, keywords, analysis, advice = analyze_journal_entry(entry.mood, entry.text, entry.free_writing)
        entry.ai_sentiment = sentiment
        entry.ai_score = score
        entry.ai_keywords = keywords
        entry.ai_analysis = analysis
        entry.ai_advice = advice

        db.session.commit()
        flash(_('Günlüğünüz başarıyla güncellendi! ✏️'), 'success')
        return redirect(url_for('main.index'))
        
    return render_template('edit_entry.html', form=form, entry=entry)

# ── Hızlı Kayıt ──────────────────────────────────────────────
@main.route('/quick_entry', methods=['POST'])
def quick_entry():
    mood = request.form.get('mood')
    if mood:
        entry = MoodEntry(mood=mood, text=_('Hızlı giriş yapıldı.'))
        db.session.add(entry)
        db.session.commit()
        flash(_('Hızlı kayıt başarıyla eklendi!'), 'success')
    return redirect(url_for('main.index'))

@main.route('/journal')
def journal():
    return redirect(url_for('main.index', _anchor='entries-section'))

@main.route('/stats')
def stats():
    return redirect(url_for('main.profile'))

@main.route('/support')
def support():
    return render_template('support.html')

@main.route('/export_pdf')
def export_pdf():
    # Son 30 günün kayıtlarını alalım veya tümünü alalım (kullanıcıya özel)
    entries = MoodEntry.query.order_by(MoodEntry.timestamp.desc()).all()
    
    # Tarih aralığını bulalım
    if entries:
        start_date = entries[-1].timestamp.strftime('%d.%m.%Y')
        end_date = entries[0].timestamp.strftime('%d.%m.%Y')
        date_range = f"{start_date} - {end_date}"
    else:
        date_range = _("Kayıt Yok")
        
    ai_patterns = analyze_patterns(entries)
    
    return render_template('pdf_report.html', entries=entries, date_range=date_range, ai_patterns=ai_patterns)

# ── API v1 ────────────────────────────────────────────────
@main.route('/api/v1/entries', methods=['GET'])
def api_entries():
    """JSON API: tüm günlük kayıtlarını döndürür."""
    limit  = request.args.get('limit',  type=int)
    mood   = request.args.get('mood',   type=str)
    query  = MoodEntry.query.order_by(MoodEntry.timestamp.desc())
    if mood:
        query = query.filter(MoodEntry.mood == mood)
    if limit:
        query = query.limit(limit)
        
    entries = query.all()
    return jsonify({
        'status':  'ok',
        'count':   len(entries),
        'entries': [e.to_dict() for e in entries]
    })

# ── Profil ────────────────────────────────────────────────
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
AVATARS_DIR = os.path.join(os.path.dirname(__file__), 'static', 'avatars')

@main.route('/profile', methods=['GET', 'POST'])
def profile():
    # 1. Kullanıcıyı güvenli çekme
    try:
        user = User.query.first()
        if not user:
            user = User(username=_('Mindful Kullanıcı'), email='user@mindful.me', avatar_file='default.png')
            db.session.add(user)
            db.session.commit()
    except Exception:
        db.session.rollback()
        # Veritabanı User tablosu uyumsuzsa sahte kullanıcı (mock) oluştur
        class DummyUser:
            id = 1
            username = 'Mindful Kullanıcı'
            email = 'user@mindful.me'
            avatar_file = 'default.png'
            streak_count = 0
        user = DummyUser()
        user.has_sleep_master_badge = False

    check_badges(user)
    smart_coach_feedback = get_lifestyle_feedback()

    form = ProfileForm()
    if form.validate_on_submit():
        try:
            user.username = form.username.data
            user.email = form.email.data
            file = form.avatar.data
            if file and file.filename:
                filename  = secure_filename(file.filename)
                ext       = os.path.splitext(filename)[1].lower() if '.' in filename else ''
                save_name = f"avatar_{user.id}{ext}"
                os.makedirs(AVATARS_DIR, exist_ok=True)
                file.save(os.path.join(AVATARS_DIR, save_name))
                user.avatar_file = save_name
            db.session.commit()
            flash(_('Profil başarıyla güncellendi! 🎉'), 'success')
        except Exception:
            db.session.rollback()
            flash(_('Profil güncellenirken hata oluştu (Veritabanı şema sorunu).'), 'danger')
        return redirect(url_for('main.profile'))
    elif request.method == 'GET':
        form.username.data = getattr(user, 'username', '')
        form.email.data = getattr(user, 'email', '')

    # 2. İstatistikleri güvenli çekme
    try:
        total_entries  = MoodEntry.query.count()
        all_entries = MoodEntry.query.all()
    except Exception:
        db.session.rollback()
        total_entries = 0
        all_entries = []

    mood_counts    = {}
    for e in all_entries:
        if getattr(e, 'mood', None):
            mood_counts[e.mood] = mood_counts.get(e.mood, 0) + 1
            
    best_mood      = max(mood_counts, key=mood_counts.get) if mood_counts else None
    
    avatar_file = getattr(user, 'avatar_file', 'default.png')
    avatar_url     = url_for('static', filename=f'avatars/{avatar_file}') \
                     if avatar_file and avatar_file != 'default.png' \
                     else None

    streak = getattr(user, 'streak_count', 0) or 0
    badges = [
        {'name': _('Başlangıç'), 'icon': '🌱', 'desc': _('3 Günlük Seri'), 'earned': streak >= 3},
        {'name': _('İstikrarlı'), 'icon': '🔥', 'desc': _('7 Günlük Seri'), 'earned': streak >= 7},
        {'name': _('Zen Ustası'), 'icon': '👑', 'desc': _('30 Günlük Seri'), 'earned': streak >= 30}
    ]
    if getattr(user, 'has_sleep_master_badge', False):
        badges.append({'name': _('Uyku Ustası'), 'icon': '💤', 'desc': _('3 Gün Üst Üste 8+ Saat Uyku'), 'earned': True})
    else:
        badges.append({'name': _('Uyku Ustası'), 'icon': '💤', 'desc': _('3 Gün Üst Üste 8+ Saat Uyku'), 'earned': False})
        
    insights = calculate_lifestyle_insights(all_entries)
    top_activities = get_best_feeling_activities(all_entries)

    # Destek Kartı Kontrolü
    show_support_card = False
    motivation_quote = ""
    try:
        latest_entry = MoodEntry.query.order_by(MoodEntry.timestamp.desc()).first()
        if latest_entry:
            score = MOOD_VALUES.get(latest_entry.mood, 3)
            bad_words = ['kötü', 'stresli', 'üzgün', 'uzgun', 'kotu']
            text_to_check = f"{latest_entry.text or ''} {getattr(latest_entry, 'mini_journal', '') or ''} {getattr(latest_entry, 'free_writing', '') or ''}".lower()
            has_bad_word = any(word in text_to_check for word in bad_words)
            if score < 3 or has_bad_word:
                show_support_card = True
                import random
                quotes = [
                    _("Zor zamanlar geçicidir, ama güçlü insanlar kalıcıdır."),
                    _("Her yeni gün, yeni bir başlangıçtır."),
                    _("İçindeki güce güven, sen bundan daha güçlüsün."),
                    _("Küçük adımlar, büyük değişimlere yol açar. Sadece devam et."),
                    _("Kendine şefkat göster, bugün elinden gelenin en iyisini yapıyorsun.")
                ]
                motivation_quote = random.choice(quotes)
    except Exception:
        pass

    ai_patterns = analyze_patterns()

    return render_template('profile.html', user=user, form=form,
                           total_entries=total_entries, mood_counts=mood_counts,
                           best_mood=best_mood, avatar_url=avatar_url, badges=badges,
                           insights=insights, smart_coach_feedback=smart_coach_feedback,
                           top_activities=top_activities, show_support_card=show_support_card,
                           motivation_quote=motivation_quote, ai_patterns=ai_patterns)

@main.route('/change_password', methods=['GET', 'POST'])
def change_password():
    user = User.query.first()
    if not user:
        return redirect(url_for('main.index'))
    form = ChangePasswordForm()
    if form.validate_on_submit():
        # Check if password_hash is set (default user might not have one)
        if not user.password_hash or user.check_password(form.old_password.data):
            user.set_password(form.new_password.data)
            db.session.commit()
            flash(_('Şifreniz başarıyla değiştirildi!'), 'success')
            return redirect(url_for('main.profile'))
        else:
            flash(_('Mevcut şifreniz yanlış.'), 'danger')
    return render_template('change_password.html', form=form)

@main.route('/set_language/<language>')
def set_language(language):
    session['language'] = language
    return redirect(request.referrer or url_for('main.index'))

# ── Şifre Sıfırlama (Forgot Password) ──────────────────────
def get_reset_token(user, expires_sec=1800):
    s = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    return s.dumps({'user_id': user.id}, salt='password-reset-salt')

def verify_reset_token(token, expires_sec=1800):
    s = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    try:
        user_id = s.loads(token, salt='password-reset-salt', max_age=expires_sec)['user_id']
    except:
        return None
    return User.query.get(user_id)

def send_reset_email(user):
    token = get_reset_token(user)
    msg = Message(_('Şifre Sıfırlama İsteği - Mindful-Me'),
                  sender=current_app.config['MAIL_DEFAULT_SENDER'],
                  recipients=[user.email])
    msg.body = _('''Şifrenizi sıfırlamak için aşağıdaki bağlantıya tıklayın:
%(url)s

Eğer bu isteği siz yapmadıysanız bu e-postayı görmezden gelebilirsiniz.
''', url=url_for('main.reset_password', token=token, _external=True))
    mail.send(msg)

@main.route('/reset_password_request', methods=['GET', 'POST'])
def reset_password_request():
    form = ForgotPasswordForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            send_reset_email(user)
        flash(_('Şifre sıfırlama talimatları e-posta adresinize gönderildi.'), 'info')
        return redirect(url_for('main.index'))
    return render_template('reset_password_request.html', form=form)

@main.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    user = verify_reset_token(token)
    if not user:
        flash(_('Geçersiz veya süresi dolmuş bir link.'), 'warning')
        return redirect(url_for('main.index'))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        db.session.commit()
        flash(_('Şifreniz başarıyla güncellendi!'), 'success')
        return redirect(url_for('main.index'))
    return render_template('reset_password.html', form=form)

import io
from flask import send_file

@main.route('/export_pdf_legacy')
def export_pdf_legacy():
    try:
        from fpdf import FPDF
    except ImportError:
        flash(_('PDF oluşturma modülü (fpdf) yüklü değil.'), 'danger')
        return redirect(url_for('main.index'))
        
    entries = MoodEntry.query.order_by(MoodEntry.timestamp.desc()).all()
    
    pdf = FPDF()
    pdf.add_page()
    
    pdf.set_font('Helvetica', 'B', 16)
    pdf.cell(0, 10, 'Mindful-Me Gunluk Kayitlari', ln=True, align='C')
    pdf.ln(10)
    
    for e in entries:
        date_str = e.timestamp.strftime('%Y-%m-%d %H:%M') if e.timestamp else 'Bilinmiyor'
        pdf.set_font('Helvetica', 'B', 12)
        pdf.cell(0, 10, f"Tarih: {date_str} - Ruh Hali: {e.mood.capitalize()}", ln=True)
        
        pdf.set_font('Helvetica', '', 11)
        
        def sanitize(text):
            if not text: return ""
            replacements = {'ı':'i', 'İ':'I', 'ğ':'g', 'Ğ':'G', 'ü':'u', 'Ü':'U', 'ş':'s', 'Ş':'S', 'ö':'o', 'Ö':'O', 'ç':'c', 'Ç':'C'}
            for tr, en in replacements.items():
                text = text.replace(tr, en)
            return text.encode('latin-1', 'replace').decode('latin-1')

        text = sanitize(e.text)
        pdf.multi_cell(0, 8, f"Not: {text}")
        
        if e.mini_journal:
            mj = sanitize(e.mini_journal)
            pdf.multi_cell(0, 8, f"Ozet: {mj}")
            
        if e.free_writing:
            fw = sanitize(e.free_writing)
            pdf.multi_cell(0, 8, f"Duygular: {fw}")
            
        pdf.ln(5)
        
    pdf_bytes = pdf.output(dest='S')
    if isinstance(pdf_bytes, str):
        pdf_bytes = pdf_bytes.encode('latin-1')
        
    return send_file(
        io.BytesIO(pdf_bytes),
        mimetype='application/pdf',
        as_attachment=True,
        download_name='mindful-me-gunlukler.pdf'
    )
