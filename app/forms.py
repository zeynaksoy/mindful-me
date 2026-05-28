from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import TextAreaField, SelectField, SubmitField, FloatField, IntegerField, StringField, PasswordField
from wtforms.validators import DataRequired, Optional, NumberRange, Email, EqualTo

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

class ProfileForm(FlaskForm):
    avatar = FileField('Avatar Yükle', validators=[
        FileAllowed(['jpg', 'jpeg', 'png', 'gif', 'webp'], 'Sadece resim dosyaları yüklenebilir!')
    ])
    submit = SubmitField('Profili Güncelle')

class ForgotPasswordForm(FlaskForm):
    email = StringField('E-posta', validators=[DataRequired(), Email(message='Geçerli bir e-posta adresi giriniz.')])
    submit = SubmitField('Şifre Sıfırlama Linki Gönder')

class ResetPasswordForm(FlaskForm):
    password = PasswordField('Yeni Şifre', validators=[DataRequired()])
    confirm_password = PasswordField('Şifre Tekrar', validators=[
        DataRequired(),
        EqualTo('password', message='Şifreler eşleşmiyor.')
    ])
    submit = SubmitField('Şifreyi Sıfırla')
