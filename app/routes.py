from flask import Blueprint, render_template, redirect, url_for, flash
from app.forms import MoodEntryForm
from app.models import MoodEntry
from app import db

main = Blueprint('main', __name__)

@main.route('/', methods=['GET', 'POST'])
def index():
    form = MoodEntryForm()
    if form.validate_on_submit():
        entry = MoodEntry(mood=form.mood.data, text=form.text.data)
        db.session.add(entry)
        db.session.commit()
        return redirect(url_for('main.index'))
    
    entries = MoodEntry.query.order_by(MoodEntry.timestamp.desc()).all()
    return render_template('index.html', form=form, entries=entries)
