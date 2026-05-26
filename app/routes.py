import json
from datetime import datetime, timedelta
from flask import Blueprint, render_template, redirect, url_for, flash, request
from app.forms import MoodEntryForm
from app.models import MoodEntry
from app import db

main = Blueprint('main', __name__)

MOOD_VALUES = {
    'heyecanli': 5,
    'mutlu': 4,
    'sakin': 3,
    'stresli': 2,
    'uzgun': 1
}

SUGGESTIONS = {
    'heyecanli': 'Harika bir enerji! Bu enerjiyi yaratıcı bir hobiye veya spora yönlendirmeyi dene.',
    'mutlu': 'Bu anı bir kutlama ile taçlandır! Kendine sevdiğin bir içecek ısmarla veya en sevdiğin şarkıyı dinle.',
    'sakin': 'Bu huzurlu anın tadını çıkar. Birkaç sayfa kitap okumak veya kısa bir yürüyüş için harika bir zaman.',
    'stresli': 'Derin bir nefes al... Omuzlarını serbest bırak. Gözlerini kapatıp 2 dakika sadece durmayı dene.',
    'uzgun': 'Bir bardak su iç ve kendine sarıl. Duygularını hissetmek tamamen normal, geçici olduklarını unutma.'
}

def analyze_journal_entry(mood, text):
    words = text.lower().replace('.', '').replace(',', '').split() if text else []
    stop_words = ['bir', 've', 'ile', 'çok', 'için', 'daha', 'bu', 'şu', 'o', 'ama', 'fakat']
    keywords_list = [w for w in words if w not in stop_words and len(w) > 3][:3]
    keywords = ", ".join(keywords_list) if keywords_list else mood
    
    if not text or len(text.strip()) < 5:
        sentiment = "Nötr"
        score = 5
        analysis = f"{mood.capitalize()} bir ruh hali içindesin."
        advice = "Daha fazla detay yazarsan sana özel yapay zeka tavsiyeleri verebilirim."
    else:
        if mood in ['uzgun', 'stresli']:
            sentiment = "Negatif"
            score = 3 if mood == 'uzgun' else 4
            analysis = "Yazdıklarında belirgin bir yoğunluk seziyorum."
            advice = "Belki de şu an kendine biraz daha şefkat göstermelisin. 5 dakikalık bir nefes egzersizi iyi gelebilir."
        elif mood in ['mutlu', 'heyecanli']:
            sentiment = "Pozitif"
            score = 9 if mood == 'mutlu' else 8
            analysis = "Harika! Bu pozitif anın tadını çıkardığın yazdıklarından belli."
            advice = "Bu enerjiyi çevrendekilerle paylaşabilir veya bu anın neden güzel olduğunu not edebilirsin."
        else:
            sentiment = "Nötr"
            score = 6
            analysis = "Dengeli ve merkezinde görünüyorsun."
            advice = "Günün geri kalanında bu dengeyi korumak için kısa bir yürüyüş yapabilirsin."
            
    return sentiment, score, keywords, analysis, advice

def analyze_data(entries):
    if not entries:
        return "Yeterli veri yok. Analiz için daha fazla günlük girmelisin."
    
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
        insights.append(f"'{best_act.title()}' yaptığın günlerde mutluluk ortalaman %{int(best_diff)} daha yüksek.")
        
    high_sleep_moods = [MOOD_VALUES.get(e.mood, 3) for e in entries if e.sleep_hours and e.sleep_hours >= 7]
    low_sleep_moods = [MOOD_VALUES.get(e.mood, 3) for e in entries if e.sleep_hours and e.sleep_hours < 7]
    
    if high_sleep_moods and low_sleep_moods:
        avg_high = sum(high_sleep_moods) / len(high_sleep_moods)
        avg_low = sum(low_sleep_moods) / len(low_sleep_moods)
        if avg_high > avg_low:
            insights.append("7 saat ve üzeri uyuduğunda kendini daha pozitif hissediyorsun.")
            
    high_stress = [e for e in entries if e.stress_level and e.stress_level >= 7]
    if high_stress:
        insights.append("Bazı günlerde stres seviyen yüksek çıkmış, nefes egzersizlerini artırabilirsin.")
        
    if not insights:
        return "Henüz belirgin bir korelasyon bulamadım, günlüğünü doldurmaya devam et!"
        
    return " ".join(insights)

def get_mood_history():
    thirty_days_ago = datetime.utcnow() - timedelta(days=29)
    recent_entries = MoodEntry.query.filter(MoodEntry.timestamp >= thirty_days_ago).order_by(MoodEntry.timestamp.asc()).all()
    
    daily_data = {}
    for e in recent_entries:
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
            ai_keywords=keywords
        )
        db.session.add(entry)
        db.session.commit()
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
        current_suggestion = SUGGESTIONS.get(entries[0].mood, "Bugün kendine iyi davranmayı unutma.")

    # Strategy 1: Duygu Haritası Grafiği Verisi (Son 7 Gün)
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    recent_entries = MoodEntry.query.filter(MoodEntry.timestamp >= seven_days_ago).order_by(MoodEntry.timestamp.asc()).all()
    
    daily_moods = {}
    for e in recent_entries:
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
        count = sum(1 for e in entries_for_stats if e.timestamp.strftime('%Y-%m-%d') == date_str)
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
