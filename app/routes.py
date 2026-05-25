import json
from datetime import datetime, timedelta
from flask import Blueprint, render_template, redirect, url_for, flash
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

@main.route('/', methods=['GET', 'POST'])
def index():
    form = MoodEntryForm()
    if form.validate_on_submit():
        entry = MoodEntry(mood=form.mood.data, text=form.text.data)
        db.session.add(entry)
        db.session.commit()
        return redirect(url_for('main.index'))
    
    entries = MoodEntry.query.order_by(MoodEntry.timestamp.desc()).all()
    
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
    
    return render_template('index.html', form=form, entries=entries, suggestion=current_suggestion, chart_json=json.dumps(chart_json))
