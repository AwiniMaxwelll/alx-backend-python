from django.db import models
import uuid
from django.conf import settings
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.validators import RegexValidator
from django.db import models
from django.db.models import Q, Count

# Custom User Manager
class UserManager(BaseUserManager):
    """
    Custom user model manager with email as the unique identifier for authentication.
    """
    def _normalize_and_validate_email(self, email):
        """Normalize and validate email."""
        if not email:
            raise ValueError('The Email must be set')
        return self.normalize_email(email)

    def create_user(self, email, password=None, **extra_fields):
        """
        Create and save a User with the given email and password.
        """
        email = self._normalize_and_validate_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save()
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        """
        Create and save a SuperUser with the given email and password.
        """
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        return self.create_user(email, password, **extra_fields)

    def create_users(self, user_data_list):
        """
        Bulk create users for efficiency.
        """
        users = [
            self.model(
                email=self._normalize_and_validate_email(data['email']),
                **{k: v for k, v in data.items() if k != 'email' and k != 'password'}
            ) for data in user_data_list
        ]
        for user, data in zip(users, user_data_list):
            if data.get('password'):
                user.set_password(data['password'])
        return self.model.objects.bulk_create(users)

# Custom User Model
class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = 'admin', 'Admin'
        GUEST = 'guest', 'Guest'
        HOST = 'host', 'Host'

    user_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    first_name = models.CharField(max_length=150, blank=False)
    last_name = models.CharField(max_length=150, blank=False)
    email = models.EmailField(unique=True, blank=False)
    phone_number = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        validators=[RegexValidator(r'^\+?1?\d{9,15}$', 'Invalid phone number')]
    )
    role = models.CharField(max_length=6, choices=Role.choices, default=Role.GUEST)
    created_at = models.DateTimeField(auto_now_add=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    username = None  # Remove username field
    USERNAME_FIELD = 'email'  # Use email as the unique identifier
    REQUIRED_FIELDS = ['first_name', 'last_name']  # Required for superuser creation

    objects = UserManager()

    def __str__(self):
        """Cached string representation."""
        if not hasattr(self, '_str_cache'):
            self._str_cache = self.email
        return self._str_cache

    class Meta:
        indexes = [
            models.Index(fields=['role']),
            models.Index(fields=['phone_number'], condition=Q(phone_number__isnull=False))
        ]

# Conversation Model
class Conversation(models.Model):
    conversation_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    participants = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='conversations')
    created_at = models.DateTimeField(auto_now_add=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        """String representation with participant emails."""
        participants = ', '.join(self.participants.values_list('email', flat=True)[:3])  # Limit for performance
        return f"Conversation {self.conversation_id} ({participants})"

    @classmethod
    def get_or_create_conversation(cls, participant_ids):
        """
        Get or create a conversation for a set of participants.
        """
        conversations = cls.objects.filter(participants__in=participant_ids).annotate(
            num_participants=Count('participants')
        ).filter(num_participants=len(participant_ids))
        for conv in conversations:
            if set(conv.participants.values_list('user_id', flat=True)) == set(participant_ids):
                return conv
        conv = cls.objects.create()
        conv.participants.add(*User.objects.filter(user_id__in=participant_ids))
        return conv

    class Meta:
        indexes = [models.Index(fields=['participants'])]

# Message Model
class Message(models.Model):
    class Status(models.TextChoices):
        SENT = 'sent', 'Sent'
        DELIVERED = 'delivered', 'Delivered'
        READ = 'read', 'Read'

    message_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.ForeignKey(Conversation, related_name='messages', on_delete=models.CASCADE)
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='sent_messages', on_delete=models.CASCADE)
    message_body = models.TextField(max_length=10000)
    sent_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.SENT)
    deleted_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        """Optimized string representation."""
        return f"Message {self.message_id} by {self.sender_id} in {self.conversation_id}"

    class Meta:
        ordering = ['sent_at']
        indexes = [models.Index(fields=['conversation', 'sent_at'])]