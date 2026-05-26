from flask_wtf import FlaskForm
from wtforms import TextAreaField, SelectField, SubmitField, FloatField, IntegerField, StringField
from wtforms.validators import DataRequired, Optional, NumberRange

class MoodEntryForm(FlaskForm):
    mood = SelectField('Bugün nasıl hissediyorsun?', choices=[
        ('mutlu', 'Mutlu 😄'),
        ('sakin', 'Sakin 😌'),
        ('stresli', 'Stresli 😰'),
        ('uzgun', 'Üzgün 😢'),
        ('heyecanli', 'Heyecanlı 🤩')
    ], validators=[DataRequired()])
    text = TextAreaField('Neler düşünüyorsun?', validators=[DataRequired()])
    sleep_hours = FloatField('Uyku Süresi (Saat)', validators=[Optional(), NumberRange(min=0, max=24)])
    stress_level = IntegerField('Stres Seviyesi (1-10)', validators=[Optional(), NumberRange(min=1, max=10)])
    activities = StringField('Aktiviteler (virgülle ayırın)', validators=[Optional()])
    submit = SubmitField('Kaydet')
