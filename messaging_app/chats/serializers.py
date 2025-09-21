from rest_framework import serializers
from django.core.exceptions import ValidationError
from django.core.cache import cache
from django.db.models import Q
from .models import User, Conversation, Message
import bleach


class UserSerializer(serializers.ModelSerializer):
    """
    Serializer for the User model, optimized for nested use in conversations.
    """
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['user_id', 'email', 'full_name', 'role']  # Reduced fields for nested use
        read_only_fields = ['user_id', 'role', 'full_name']

    def get_full_name(self, obj):
        """Return cached full name."""
        cache_key = f'user_full_name_{obj.user_id}'
        full_name = cache.get(cache_key)
        if not full_name:
            full_name = f"{obj.first_name} {obj.last_name}".strip()
            cache.set(cache_key, full_name, timeout=3600)
        return full_name

    def validate_email(self, value):
        """Validate email format, uniqueness, and normalize to lowercase."""
        if not value:
            raise serializers.ValidationError("Email is required.")
        value = value.lower()
        if self.instance is None or self.instance.email != value:
            if User.objects.filter(email=value).exists():
                raise serializers.ValidationError("A user with this email already exists.")
        return value

    def validate_phone_number(self, value):
        """Rely on model validation for phone number."""
        return value or None

    def update(self, instance, validated_data):
        """Support partial updates and invalidate cache."""
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        cache.delete(f'user_full_name_{instance.user_id}')
        return instance


class MessageSerializer(serializers.ModelSerializer):
    """
    Serializer for the Message model, optimized for nested use in conversations.
    """
    sender = serializers.SlugRelatedField(
        slug_field='email',
        queryset=User.objects.all(),
        write_only=False
    )
    sender_name = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = ['message_id', 'conversation', 'sender', 'sender_name', 'message_body', 'sent_at', 'status']
        read_only_fields = ['message_id', 'sent_at', 'sender_name', 'status']
        extra_kwargs = {
            'conversation': {'write_only': True},
            'message_body': {'trim_whitespace': False},
        }

    def get_sender_name(self, obj):
        """Return cached sender's full name."""
        cache_key = f'user_full_name_{obj.sender_id}'
        sender_name = cache.get(cache_key)
        if not sender_name:
            sender_name = f"{obj.sender.first_name} {obj.sender.last_name}".strip()
            cache.set(cache_key, sender_name, timeout=3600)
        return sender_name

    def validate_message_body(self, value):
        """Validate and sanitize message body."""
        if not value or not value.strip():
            raise serializers.ValidationError("Message body cannot be empty.")
        return bleach.clean(value, tags=['p', 'b', 'i', 'strong', 'em'], strip=True)


class ConversationSerializer(serializers.ModelSerializer):
    """
    Serializer for the Conversation model, with optimized nested messages and participants.
    """
    participants = UserSerializer(many=True, read_only=True)
    messages = serializers.SerializerMethodField()
    participant_count = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = ['conversation_id', 'participants', 'participant_count', 'messages', 'last_message', 'created_at']
        read_only_fields = ['conversation_id', 'participants', 'participant_count', 'messages', 'last_message', 'created_at']

    def get_participant_count(self, obj):
        """Return cached participant count."""
        cache_key = f'conversation_participant_count_{obj.conversation_id}'
        count = cache.get(cache_key)
        if count is None:
            count = obj.participants.count()
            cache.set(cache_key, count, timeout=3600)
        return count

    def get_messages(self, obj):
        """
        Return paginated messages, filtered by status or date if specified.
        """
        request = self.context.get('request')
        limit = int(request.query_params.get('message_limit', 50)) if request else 50
        status = request.query_params.get('message_status') if request else None
        date_from = request.query_params.get('date_from') if request else None

        queryset = obj.messages.select_related('sender').filter(deleted_at__isnull=True)
        if status:
            queryset = queryset.filter(status=status)
        if date_from:
            queryset = queryset.filter(sent_at__gte=date_from)
        queryset = queryset.order_by('-sent_at')[:limit]

        return MessageSerializer(queryset, many=True, context=self.context).data

    def get_last_message(self, obj):
        """Return the last non-deleted message."""
        last_message = obj.messages.select_related('sender').filter(deleted_at__isnull=True).order_by('-sent_at').first()
        return MessageSerializer(last_message, context=self.context).data if last_message else None

    def validate(self, data):
        """Validate conversation data, ensuring valid participants."""
        participants = self.initial_data.get('participants', [])
        if len(participants) < 2:
            raise serializers.ValidationError("A conversation must have at least 2 participants.")
        if not User.objects.filter(user_id__in=participants, deleted_at__isnull=True).count() == len(participants):
            raise serializers.ValidationError("One or more participant IDs are invalid or deleted.")
        return data

    def create(self, validated_data):
        """Create a conversation using optimized model method."""
        participants = self.initial_data.get('participants', [])
        conversation = Conversation.get_or_create_conversation(participants)
        cache.delete(f'conversation_participant_count_{conversation.conversation_id}')
        return conversation