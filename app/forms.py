from flask_wtf import FlaskForm
from wtforms import TextAreaField, SelectField, SubmitField
from wtforms.validators import DataRequired

class MoodEntryForm(FlaskForm):
    mood = SelectField('Bugün nasıl hissediyorsun?', choices=[
        ('mutlu', 'Mutlu 😄'),
        ('sakin', 'Sakin 😌'),
        ('stresli', 'Stresli 😰'),
        ('uzgun', 'Üzgün 😢'),
        ('heyecanli', 'Heyecanlı 🤩')
    ], validators=[DataRequired()])
    text = TextAreaField('Neler düşünüyorsun?', validators=[DataRequired()])
    submit = SubmitField('Kaydet')
