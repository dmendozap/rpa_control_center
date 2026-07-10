from flask_wtf import FlaskForm
from wtforms import (
    PasswordField,
    StringField,
    SubmitField,
)
from wtforms.validators import (
    DataRequired,
    Length,
)


class LoginForm(FlaskForm):
    identifier = StringField(
        "Usuario o correo",
        validators=[
            DataRequired(),
            Length(max=120),
        ],
    )

    password = PasswordField(
        "Contraseña",
        validators=[
            DataRequired(),
            Length(max=256),
        ],
    )

    submit = SubmitField("Ingresar")