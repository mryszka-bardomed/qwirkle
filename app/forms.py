from flask_wtf import FlaskForm
from wtforms import DateField, PasswordField, StringField, TextAreaField
from wtforms.validators import EqualTo, Length, Optional, ValidationError, DataRequired

from .models import User


class LoginForm(FlaskForm):
    username = StringField("Login", validators=[DataRequired()])
    password = PasswordField("Hasło", validators=[DataRequired()])


class RegisterForm(FlaskForm):
    username = StringField("Login", validators=[DataRequired(), Length(min=3, max=64)])
    password = PasswordField("Hasło", validators=[DataRequired(), Length(min=8)])
    confirm = PasswordField(
        "Powtórz hasło", validators=[DataRequired(), EqualTo("password", "Hasła się różnią.")]
    )

    def validate_username(self, field):
        if User.query.filter_by(username=field.data).first():
            raise ValidationError("Ten login jest już zajęty.")


class RecordForm(FlaskForm):
    name = StringField("Nazwa", validators=[DataRequired(), Length(max=200)])
    category = StringField("Kategoria", validators=[Optional(), Length(max=100)])
    date = DateField("Data", validators=[Optional()])
    description = TextAreaField("Opis", validators=[Optional()])
