
import uuid

from django.conf import settings
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models

from .managers import UnreadMessagesManager

# Create your models here.

class UserManager(BaseUserManager):
    """
    Custom user model manager where email is the unique identifier
    for authentication instead of usernames.
    """
    def create_user(self, email, password=None, **extra_fields):
        """
        Create and save a User with the given email and password.
        """
        if not email:
            raise ValueError('The Email must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
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


class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = 'admin', 'Admin'
        GUEST = 'guest', 'Guest'
        HOST = 'host', 'Host'

    user_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, db_index=True)
    first_name = models.CharField(max_length=250, blank=False)
    last_name = models.CharField(max_length=250, blank=False)
    email = models.EmailField(unique=True, blank=False)
    phone_number = models.CharField(max_length=20, null=True, blank=True)
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.GUEST)
    created_at = models.DateTimeField(auto_now_add=True)

    username = None  # Remove username field
    USERNAME_FIELD = 'email'  # Use email as the unique identifier
    REQUIRED_FIELDS = ['first_name', 'last_name']  # Fields required when creating a superuser

    objects = UserManager()

    def __str__(self):
        return self.email

class ThreadedMessageManager(models.Manager):
    def get_threaded_messages(self, conversation):
        """
        Get all messages in a conversation with optimized queries for threading.
        Uses select_related and prefetch_related for efficiency.
        """
        return self.select_related(
            'sender', 'conversation', 'parent_message'
        ).prefetch_related(
            'replies__sender',
            'replies__replies__sender'
        ).filter(conversation=conversation).order_by('sent_at')

    def get_root_messages(self, conversation):
        """Get only root messages (not replies) in a conversation"""
        return self.get_threaded_messages(conversation).filter(parent_message=None)

    def get_message_with_replies(self, message_id):
        """
        Get a specific message with all its replies recursively.
        Uses recursive CTE for PostgreSQL or fallback for other databases.
        """
        from django.db import connection

        if 'postgresql' in connection.settings_dict['ENGINE']:
            # Use recursive CTE for PostgreSQL
            return self.raw("""
                            WITH RECURSIVE message_tree AS (SELECT message_id,
                                                                   conversation_id,
                                                                   sender_id,
                                                                   parent_message_id,
                                                                   message_body,
                                                                   sent_at,
                                                                   edited,
                                                                   0 as depth
                                                            FROM messaging_message
                                                            WHERE message_id = %s

                                                            UNION ALL

                                                            SELECT m.message_id,
                                                                   m.conversation_id,
                                                                   m.sender_id,
                                                                   m.parent_message_id,
                                                                   m.message_body,
                                                                   m.sent_at,
                                                                   m.edited,
                                                                   mt.depth + 1
                                                            FROM messaging_message m
                                                                     INNER JOIN message_tree mt ON m.parent_message_id = mt.message_id)
                            SELECT *
                            FROM message_tree
                            ORDER BY depth, sent_at
                            """, [message_id])
        else:
            # Fallback for other databases - get message and prefetch replies
            try:
                message = self.select_related('sender', 'parent_message').prefetch_related(
                    'replies__sender',
                    'replies__replies__sender',
                    'replies__replies__replies__sender'
                ).get(message_id=message_id)
                return [message]
            except self.model.DoesNotExist:
                return []

class Conversation(models.Model):
    conversation_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, db_index=True)
    participants = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='conversations')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Conversation {self.conversation_id}"


class Message(models.Model):
    message_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, db_index=True)
    conversation = models.ForeignKey(Conversation, related_name='messages', on_delete=models.CASCADE)
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='sent_messages', on_delete=models.CASCADE)
    receiver = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='received_messages', on_delete=models.CASCADE)
    parent_message = models.ForeignKey('self', related_name='replies', on_delete=models.CASCADE, null=True, blank=True)
    message_body = models.TextField()
    sent_at = models.DateTimeField(auto_now_add=True)
    edited = models.BooleanField(default=False)
    read = models.BooleanField(default=False)  # New field for tracking read status

    objects = models.Manager()  # Default manager
    threaded = ThreadedMessageManager()  # Custom manager for threaded messages
    unread = UnreadMessagesManager()  # Custom manager for unread messages

    def __str__(self):
        return f"Message {self.message_id} in Conversation {self.conversation.conversation_id} by {self.sender.email}"

    class Meta:
        ordering = ['sent_at']

    def is_reply(self):
        """Check if this message is a reply to another message"""
        return self.parent_message is not None

    def get_thread_depth(self):
        """Calculate the depth of this message in the thread"""
        depth = 0
        current = self.parent_message
        while current:
            depth += 1
            current = current.parent_message
        return depth

    def mark_as_read(self):
        """Mark this message as read"""
        if not self.read:
            self.read = True
            self.save(update_fields=['read'])

class Notification(models.Model):
    notification_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, db_index=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='notifications', on_delete=models.CASCADE)
    receiver = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='received_notifications', on_delete=models.CASCADE)
    message = models.ForeignKey(Message, related_name='notifications', on_delete=models.CASCADE)
    content = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    timestamp = models.DateTimeField(auto_now=True)  # Updates on every save

    def __str__(self):
        return f"Notification {self.notification_id} for {self.receiver.email} - {self.content[:50]}"

    class Meta:
        ordering = ['-created_at']


class MessageHistory(models.Model):
    history_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    message = models.ForeignKey(Message, related_name='edit_history', on_delete=models.CASCADE)
    old_content = models.TextField()
    edited_by = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='edited_messages', on_delete=models.SET_NULL, null=True)
    edited_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"History for Message {self.message.message_id} - {self.edited_at}"

    class Meta:
        ordering = ['-edited_at']


def build_message_tree(messages):
    """
    Build a nested dictionary structure representing the message thread tree.
    """
    message_dict = {}
    root_messages = []

    # First pass: create a dictionary of all messages
    for message in messages:
        message_dict[str(message.message_id)] = {
            'message': message,
            'replies': []
        }

    # Second pass: build the tree structure
    for message in messages:
        if message.parent_message:
            parent_id = str(message.parent_message.message_id)
            if parent_id in message_dict:
                message_dict[parent_id]['replies'].append(
                    message_dict[str(message.message_id)]
                )
        else:
            root_messages.append(message_dict[str(message.message_id)])

    return root_messages
