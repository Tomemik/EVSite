from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import check_password
from django.contrib.auth.password_validation import password_changed, validate_password
from django.core.exceptions import ValidationError
from rest_framework import serializers

User = get_user_model()

EMPTY_PASSWORD_ERRORS = {"blank": "Password cannot be empty"}

class UserRegisterSerializer(serializers.ModelSerializer):
    password2 = serializers.CharField(
        style={"input_type": "password"},
        write_only=True,
        error_messages=EMPTY_PASSWORD_ERRORS,
    )

    class Meta:
        model = User
        fields = ["username", "password", "password2"]
        extra_kwargs = {
            "password": {"write_only": True, "error_messages": EMPTY_PASSWORD_ERRORS}
        }

    def validate(self, data):
        data = super().validate(data)
        password = data["password"]
        password2 = data["password2"]

        if password != password2:
            raise serializers.ValidationError({"password2": "Hasła nie są takie same"})

        try:
            validate_password(password)
        except ValidationError as error:
            raise ValidationError({"password": error.error_list})

        return data

    def save(self):
        account = User(username=self.validated_data["username"])
        account.set_password(self.validated_data["password"])
        account.save()

        return account


class UserSerializer(serializers.ModelSerializer):

    class Meta:
        model = User
        fields = [
            "username", "groups"
        ]


class UserSettingsSerializer(serializers.ModelSerializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)
    new_password2 = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = [
            "username",
            "first_name",
            "last_name",
            "email",
            "old_password",
            "new_password",
            "new_password2",
        ]

    def validate_old_password(self, old_password):
        if not check_password(old_password, self.context["request"].user.password):
            raise serializers.ValidationError(
                {"old_password": "Podane hasło jest niepoprawne"}
            )
        return old_password

    def _is_changing_password(self, data):
        return "new_password" in data and "new_password2"

    def _validate_passwords(self, data):
        if self._is_changing_password(data):
            new_password = data["new_password"]
            new_password2 = data["new_password2"]

            if new_password != new_password2:
                raise serializers.ValidationError(
                    {"new_password2": "Hasła nie są takie same"}
                )

            try:
                validate_password(new_password, self.context["request"].user)
            except ValidationError as error:
                raise ValidationError({"new_password": error.error_list})

    def validate(self, data):
        data = super().validate(data)
        self._validate_passwords(data)
        return data

    def save(self):
        user = super().save()

        if self._is_changing_password(self.validated_data):
            new_password = self.validated_data["new_password"]
            user.set_password(new_password)
            password_changed(new_password, user)
            user.save()
        return user