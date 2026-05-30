from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import TextAreaField, SelectField, SubmitField, FloatField, IntegerField, StringField, PasswordField
from wtforms.fields import TimeField
from wtforms.validators import DataRequired, Optional, NumberRange, Email, EqualTo
from flask_babel import lazy_gettext as _l

class MoodEntryForm(FlaskForm):
    mood = SelectField(_l('Bugün nasıl hissediyorsun?'), choices=[
        ('mutlu', _l('Mutlu 😄')),
        ('sakin', _l('Sakin 😌')),
        ('odaklanmis', _l('Odaklanmış 🎯')),
        ('yaratici', _l('Yaratıcı 🎨')),
        ('heyecanli', _l('Heyecanlı 🤩')),
        ('stresli', _l('Stresli 😰')),
        ('bitkin', _l('Bitkin 😫')),
        ('uzgun', _l('Üzgün 😢'))
    ], validators=[DataRequired()])
    text = TextAreaField(_l('Neler düşünüyorsun?'), validators=[DataRequired()])
    mini_journal = StringField(_l('Günün Özeti'), validators=[Optional()])
    free_writing = TextAreaField(_l('Duygularını Dök'), validators=[Optional()])
    sleep_hours = FloatField(_l('Uyku Süresi (Saat)'), validators=[Optional(), NumberRange(min=0, max=24)])
    stress_level = IntegerField(_l('Stres Seviyesi (1-10)'), validators=[Optional(), NumberRange(min=1, max=10)])
    activities = StringField(_l('Aktiviteler (virgülle ayırın)'), validators=[Optional()])
    
    activity_type = SelectField(_l('Aktivite Türü'), choices=[
        ('', _l('Belirtilmedi')), 
        ('Spor', _l('Spor 🏃‍♂️')), 
        ('Sosyal', _l('Sosyal 👥')), 
        ('Ders/İş', _l('Ders/İş 💻')), 
        ('Oyun', _l('Oyun 🎮')), 
        ('Meditasyon', _l('Meditasyon 🧘‍♀️')), 
        ('Müzik', _l('Müzik 🎵')), 
        ('Doğa Yürüyüşü', _l('Doğa Yürüyüşü 🌲'))
    ], validators=[Optional()])
    
    # Uyku ve Alışkanlıklar
    bedtime = TimeField(_l('Uykuya Dalış Saati'), validators=[Optional()])
    wakeup_time = TimeField(_l('Uyanış Saati'), validators=[Optional()])
    sleep_quality = SelectField(_l('Uyku Kalitesi (1-5)'), choices=[
        ('', 'Belirtilmedi'), ('1', '1 - Çok Kötü'), ('2', '2 - Kötü'), 
        ('3', '3 - İdare Eder'), ('4', '4 - İyi'), ('5', '5 - Çok İyi')
    ], validators=[Optional()])
    dream_note = TextAreaField(_l('Rüya Notları'), validators=[Optional()])
    caffeine_intake = IntegerField(_l('Kafein (Fincan/Kupa)'), validators=[Optional(), NumberRange(min=0)])
    screen_time = IntegerField(_l('Ekran Süresi (Saat)'), validators=[Optional(), NumberRange(min=0)])
    
    submit = SubmitField(_l('Kaydet'))

class ProfileForm(FlaskForm):
    username = StringField(_l('Ad Soyad / Kullanıcı Adı'), validators=[DataRequired()])
    email = StringField(_l('E-posta'), validators=[DataRequired(), Email()])
    avatar = FileField(_l('Avatar Yükle'), validators=[
        FileAllowed(['jpg', 'jpeg', 'png', 'gif', 'webp'], _l('Sadece resim dosyaları yüklenebilir!'))
    ])
    submit = SubmitField(_l('Profili Güncelle'))

class ChangePasswordForm(FlaskForm):
    old_password = PasswordField(_l('Mevcut Şifre'), validators=[DataRequired()])
    new_password = PasswordField(_l('Yeni Şifre'), validators=[DataRequired()])
    confirm_password = PasswordField(_l('Yeni Şifre (Tekrar)'), validators=[
        DataRequired(),
        EqualTo('new_password', message=_l('Şifreler eşleşmiyor.'))
    ])
    submit = SubmitField(_l('Şifreyi Değiştir'))

class ForgotPasswordForm(FlaskForm):
    email = StringField(_l('E-posta'), validators=[DataRequired(), Email(message=_l('Geçerli bir e-posta adresi giriniz.'))])
    submit = SubmitField(_l('Şifre Sıfırlama Linki Gönder'))

class ResetPasswordForm(FlaskForm):
    password = PasswordField(_l('Yeni Şifre'), validators=[DataRequired()])
    confirm_password = PasswordField(_l('Şifre Tekrar'), validators=[
        DataRequired(),
        EqualTo('password', message=_l('Şifreler eşleşmiyor.'))
    ])
    submit = SubmitField(_l('Şifreyi Sıfırla'))
