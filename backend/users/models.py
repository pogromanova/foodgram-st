from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models import UniqueConstraint
from django.contrib.auth.validators import UnicodeUsernameValidator
from users.constants import (
    USER_USERNAME_MAX_LENGTH,
    USER_EMAIL_MAX_LENGTH,
    USER_FIRST_NAME_MAX_LENGTH,
    USER_LAST_NAME_MAX_LENGTH,
    USER_USERNAME_VERBOSE_NAME,
    USER_EMAIL_VERBOSE_NAME,
    USER_FIRST_NAME_VERBOSE_NAME,
    USER_LAST_NAME_VERBOSE_NAME,
    USER_AVATAR_VERBOSE_NAME,
    USER_AVATAR_UPLOAD_PATH,
    USER_META_VERBOSE_NAME,
    USER_META_VERBOSE_NAME_PLURAL,
    SUBSCRIPTION_USER_VERBOSE_NAME,
    SUBSCRIPTION_AUTHOR_VERBOSE_NAME,
    SUBSCRIPTION_META_VERBOSE_NAME,
    SUBSCRIPTION_META_VERBOSE_NAME_PLURAL,
    UNIQUE_SUBSCRIPTION_CONSTRAINT_NAME,
    PREVENT_SELF_SUBSCRIPTION_CONSTRAINT_NAME,
)


class User(AbstractUser):
    username = models.CharField(
        verbose_name=USER_USERNAME_VERBOSE_NAME,
        max_length=USER_USERNAME_MAX_LENGTH,
        unique=True,
        validators=[UnicodeUsernameValidator()],
        blank=False,
        null=False,
    )

    email = models.EmailField(
        verbose_name=USER_EMAIL_VERBOSE_NAME,
        max_length=USER_EMAIL_MAX_LENGTH,
        unique=True,
        blank=False,
        null=False,
    )

    first_name = models.CharField(
        verbose_name=USER_FIRST_NAME_VERBOSE_NAME,
        max_length=USER_FIRST_NAME_MAX_LENGTH,
        blank=False,
        null=False,
    )

    last_name = models.CharField(
        verbose_name=USER_LAST_NAME_VERBOSE_NAME,
        max_length=USER_LAST_NAME_MAX_LENGTH,
        blank=False,
        null=False,
    )

    avatar = models.ImageField(
        verbose_name=USER_AVATAR_VERBOSE_NAME,
        upload_to=USER_AVATAR_UPLOAD_PATH,
        blank=True,
        null=True
    )

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']

    class Meta:
        verbose_name = USER_META_VERBOSE_NAME
        verbose_name_plural = USER_META_VERBOSE_NAME_PLURAL
        ordering = ('username',)

    def __str__(self):
        return self.username


class Subscription(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='subscriptions',
        verbose_name=SUBSCRIPTION_USER_VERBOSE_NAME
    )
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='subscribers',
        verbose_name=SUBSCRIPTION_AUTHOR_VERBOSE_NAME
    )

    class Meta:
        verbose_name = SUBSCRIPTION_META_VERBOSE_NAME
        verbose_name_plural = SUBSCRIPTION_META_VERBOSE_NAME_PLURAL
        constraints = [
            UniqueConstraint(
                fields=['user', 'author'],
                name=UNIQUE_SUBSCRIPTION_CONSTRAINT_NAME
            ),
            models.CheckConstraint(
                check=~models.Q(user=models.F('author')),
                name=PREVENT_SELF_SUBSCRIPTION_CONSTRAINT_NAME
            )
        ]

    def __str__(self):
        return f'{self.user.username} подписан на {self.author.username}'
