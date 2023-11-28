from django.core.exceptions import ValidationError

from common.repositories.base_repository import BaseRepository
from core.models import User


class UserRepository(BaseRepository):
    model = User

    @classmethod
    def get_by_filter(cls, filter_input: dict = None):
        if filter_input:
            objects = cls.get_queryset().filter(**filter_input)
        else:
            objects = cls.get_queryset().all()
        return objects

    @classmethod
    def create(cls, data: dict) -> 'User':
        user = cls.model.objects.create(**data)
        return user

    @classmethod
    def get_or_create(cls, *, data: dict):
        if 'discord_id' not in data and 'discord_username' not in data:
            raise ValidationError("Input must include `discord_id` or `discord_username`")

        user = None
        if 'discord_id' in data:
            user = cls.get_by_discord_id(data['discord_id'])
        if not user and 'discord_username' in data:
            user = cls.get_by_discord_username(data['discord_username'])

        if not user:
            if 'nickname' not in data:
                data['nickname'] = data.get('discord_username') or data.get('discord_id')
            user = cls.create(data)

        return user

    @classmethod
    def update(cls, *, pk=None, obj: 'User' = None, data: dict) -> 'User':
        user = obj or cls.get(pk=pk)

        if data.get('is_active'):
            user.is_active = data['is_active']

        user.save()
        return user

    @classmethod
    def get_by_discord_id(cls, discord_id):
        try:
            user = cls.model.objects.get(discord_id=discord_id)
        except cls.model.DoesNotExist:
            return None

        return user

    @classmethod
    def get_by_discord_username(cls, discord_username):
        try:
            user = cls.model.objects.get(discord_username=discord_username)
        except cls.model.DoesNotExist:
            return None

        return user
