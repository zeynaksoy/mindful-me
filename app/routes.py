import json
import os
from datetime import datetime, timedelta
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, session, current_app
from werkzeug.utils import secure_filename
from app.forms import MoodEntryForm, ProfileForm, ForgotPasswordForm, ResetPasswordForm, ChangePasswordForm
from app.models import MoodEntry, User
from app import db, mail
from flask_mail import Message
from itsdangerous import URLSafeTimedSerializer
from flask_babel import gettext as _, lazy_gettext as _l
from app.email import send_password_reset_email

main = Blueprint('main', __name__)

MOOD_VALUES = {
    'heyecanli': 5,
    'mutlu': 4,
    'sakin': 3,
    'stresli': 2,
    'uzgun': 1
}

SUGGESTIONS = {
    'heyecanli': _l('Harika bir enerji! Bu enerjiyi yaratıcı bir hobiye veya spora yönlendirmeyi dene.'),
    'mutlu': _l('Bu anı bir kutlama ile taçlandır! Kendine sevdiğin bir içecek ısmarla veya en sevdiğin şarkıyı dinle.'),
    'sakin': _l('Bu huzurlu anın tadını çıkar. Birkaç sayfa kitap okumak veya kısa bir yürüyüş için harika bir zaman.'),
    'stresli': _l('Derin bir nefes al... Omuzlarını serbest bırak. Gözlerini kapatıp 2 dakika sadece durmayı dene.'),
    'uzgun': _l('Bir bardak su iç ve kendine sarıl. Duygularını hissetmek tamamen normal, geçici olduklarını unutma.')
}

def analyze_journal_entry(mood, text):
    words = text.lower().replace('.', '').replace(',', '').split() if text else []
    stop_words = ['bir', 've', 'ile', 'çok', 'için', 'daha', 'bu', 'şu', 'o', 'ama', 'fakat']
    keywords_list = [w for w in words if w not in stop_words and len(w) > 3][:3]
    keywords = ", ".join(keywords_list) if keywords_list else mood
    
    if not text or len(text.strip()) < 5:
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

def calculate_insights(entries):
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

@main.route('/', methods=['GET', 'POST'])
def index():
    form = MoodEntryForm()
    if form.validate_on_submit():
        sentiment, score, keywords, analysis, advice = analyze_journal_entry(form.mood.data, form.text.data)
        entry = MoodEntry(
            mood=form.mood.data, 
            text=form.text.data,
            sleep_hours=form.sleep_hours.data,
            stress_level=form.stress_level.data,
            activities=form.activities.data,
            ai_analysis=analysis,
            ai_advice=advice,
            ai_sentiment=sentiment,
            ai_score=score,
            ai_keywords=keywords,
            bedtime=form.bedtime.data,
            wakeup_time=form.wakeup_time.data,
            sleep_quality=int(form.sleep_quality.data) if form.sleep_quality.data else None,
            dream_note=form.dream_note.data,
            caffeine_intake=form.caffeine_intake.data,
            screen_time=form.screen_time.data
        )
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
    
    return render_template('index.html', form=form, entries=entries, suggestion=current_suggestion, 
                           chart_json=json.dumps(chart_json), search_query=search_query, sort_order=sort_order,
                           smart_insight=smart_insight, correlation_chart_json=correlation_chart_json, 
                           heatmap_json=heatmap_json, mood_history=mood_history)

@main.route('/delete/<int:id>', methods=['POST'])
def delete_entry(id):
    entry = MoodEntry.query.get_or_404(id)
    db.session.delete(entry)
    db.session.commit()
    return redirect(url_for('main.index'))

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
    try:
        # Varsayılan kullanıcıyı al ya da oluştur
        user = User.query.first()
        if not user:
            user = User(username=_('Mindful Kullanıcı'), email='user@mindful.me', avatar_file='default.png')
            db.session.add(user)
            db.session.commit()

        form = ProfileForm()
        if form.validate_on_submit():
            user.username = form.username.data
            user.email = form.email.data
            file = form.avatar.data
            if file and file.filename:
                filename  = secure_filename(file.filename)
                # Benzersiz dosya adı: user_id + orijinal uzantı
                ext       = os.path.splitext(filename)[1].lower() if '.' in filename else ''
                save_name = f"avatar_{user.id}{ext}"
                os.makedirs(AVATARS_DIR, exist_ok=True)
                file.save(os.path.join(AVATARS_DIR, save_name))
                user.avatar_file = save_name
            db.session.commit()
            flash(_('Profil başarıyla güncellendi! 🎉'), 'success')
            return redirect(url_for('main.profile'))
        elif request.method == 'GET':
            form.username.data = user.username
            form.email.data = user.email

        # İstatistikler
        total_entries  = MoodEntry.query.count()
        mood_counts    = {}
        for e in MoodEntry.query.all():
            mood_counts[e.mood] = mood_counts.get(e.mood, 0) + 1
        best_mood      = max(mood_counts, key=mood_counts.get) if mood_counts else None
        avatar_url     = url_for('static', filename=f'avatars/{user.avatar_file}') \
                         if user.avatar_file and user.avatar_file != 'default.png' \
                         else None

        # Rozet Mantığı
        badges = []
        streak = getattr(user, 'streak_count', 0) or 0
        if streak >= 3:
            badges.append({'name': _('Başlangıç'), 'icon': '🌱', 'desc': _('3 Günlük Seri')})
        if streak >= 7:
            badges.append({'name': _('İstikrarlı'), 'icon': '🔥', 'desc': _('7 Günlük Seri')})
        if streak >= 30:
            badges.append({'name': _('Zen Ustası'), 'icon': '👑', 'desc': _('30 Günlük Seri')})

        # İçgörüler
        all_entries = MoodEntry.query.all()
        insights = calculate_insights(all_entries)

        return render_template('profile.html', user=user, form=form,
                               total_entries=total_entries, mood_counts=mood_counts,
                               best_mood=best_mood, avatar_url=avatar_url, badges=badges,
                               insights=insights)
    except Exception as e:
        db.session.rollback()
        flash(_('Profil işlemlerinde geçici bir hata oluştu.'), 'danger')
        return redirect(url_for('main.index'))

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
