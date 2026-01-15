from factory import Faker, PostGenerationMethodCall  # type: ignore[attr-defined]
from factory.django import DjangoModelFactory

from core.models import User

TEST_PASSWORD = "password123"


class UserFactory(DjangoModelFactory):
    password = PostGenerationMethodCall("set_password", TEST_PASSWORD)

    nickname = Faker("user_name")

    discord_username = Faker("ssn")

    ombi_uid = Faker("ssn")

    is_active = True
    is_staff = False

    class Meta:
        model = User
