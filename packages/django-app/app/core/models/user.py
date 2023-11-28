from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.utils.translation import gettext_lazy as _
from pgcrypto import fields

from common.models.crud_timestamps_mixin import CRUDTimestampsMixin
from common.models.soft_delete_timestamp_mixin import SoftDeleteTimestampMixin
from core.managers import UserManager


class User(CRUDTimestampsMixin,
           SoftDeleteTimestampMixin,
           AbstractBaseUser,
           PermissionsMixin):
    objects = UserManager()

    USERNAME_FIELD = 'nickname'

    nickname = models.CharField(
        max_length=100,
        db_index=True,
        unique=True,
        blank=False,
        null=False)

    is_staff = models.BooleanField(
        _('staff status'),
        default=False,
        help_text=_('Designates whether the user can log into this admin site.'))

    discord_username = fields.CharPGPSymmetricKeyField(
        max_length=255,
        db_index=True,
        unique=True,
        blank=True,
        null=True)

    discord_id = fields.CharPGPSymmetricKeyField(
        max_length=255,
        db_index=True,
        unique=True,
        blank=True,
        null=True)

    def __str__(self):
        return self.nickname

    class Meta:
        db_table = 'users'
        default_permissions = ()
        unique_together = []
        ordering = ('id',)
