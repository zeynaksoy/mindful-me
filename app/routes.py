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
    """
    AI Günlük Analisti için placeholder fonksiyon.
    İleride OpenAI API'si ile entegre edilebilir.
    """
    if not text or len(text.strip()) < 5:
        analysis = f"{mood.capitalize()} bir ruh hali içindesin."
        advice = "Daha fazla detay yazarsan sana özel yapay zeka tavsiyeleri verebilirim."
    else:
        if mood in ['uzgun', 'stresli']:
            analysis = f"Yazdıklarında belirgin bir yoğunluk seziyorum. İçini dökmen çok değerli."
            advice = "Belki de şu an kendine biraz daha şefkat göstermelisin. 5 dakikalık bir nefes egzersizi iyi gelebilir."
        elif mood in ['mutlu', 'heyecanli']:
            analysis = f"Harika! Bu pozitif anın tadını çıkardığın yazdıklarından da belli."
            advice = "Bu enerjiyi çevrendekilerle paylaşabilir veya bu anın neden bu kadar güzel olduğunu günlüğüne not edebilirsin."
        else:
            analysis = "Dengeli ve merkezinde görünüyorsun."
            advice = "Günün geri kalanında bu dengeyi korumak için küçük yürüyüşler yapabilir veya sevdiğin bir müziği dinleyebilirsin."
            
    return analysis, advice

@main.route('/', methods=['GET', 'POST'])
def index():
    form = MoodEntryForm()
    if form.validate_on_submit():
        analysis, advice = analyze_journal_entry(form.mood.data, form.text.data)
        entry = MoodEntry(
            mood=form.mood.data, 
            text=form.text.data,
            ai_analysis=analysis,
            ai_advice=advice
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
    
    return render_template('index.html', form=form, entries=entries, suggestion=current_suggestion, chart_json=json.dumps(chart_json), search_query=search_query, sort_order=sort_order)

@main.route('/delete/<int:id>', methods=['POST'])
def delete_entry(id):
    entry = MoodEntry.query.get_or_404(id)
    db.session.delete(entry)
    db.session.commit()
    return redirect(url_for('main.index'))
