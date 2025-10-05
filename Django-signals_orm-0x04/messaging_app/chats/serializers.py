from rest_framework import serializers
from .models import User, Conversation, Message


class UserSerializer(serializers.ModelSerializer):
    """
    Serializer for the User model.
    """
    full_name = serializers.SerializerMethodField()
    display_name = serializers.CharField(source='get_full_name', read_only=True)

    class Meta:
        model = User
        fields = ['user_id', 'first_name', 'last_name', 'email', 'phone_number', 'role', 'full_name', 'display_name']
        read_only_fields = ['user_id', 'role']

    def get_full_name(self, obj):
        """
        Return the user's full name.
        """
        return f"{obj.first_name} {obj.last_name}".strip()

    def validate_email(self, value):
        """
        Validate email format and uniqueness.
        """
        if not value:
            raise serializers.ValidationError("Email is required.")
        return value


class MessageSerializer(serializers.ModelSerializer):
    """
    Serializer for the Message model.
    The sender is represented by their email address.
    """
    sender = serializers.SlugRelatedField(
        read_only=True,
        slug_field='email'
    )
    sender_name = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = ['message_id', 'conversation', 'sender', 'sender_name', 'message_body', 'sent_at']
        read_only_fields = ['message_id', 'sent_at', 'conversation']

    def get_sender_name(self, obj):
        """
        Return the sender's full name.
        """
        return f"{obj.sender.first_name} {obj.sender.last_name}".strip()

    def validate_message_body(self, value):
        """
        Validate message body is not empty.
        """
        if not value or not value.strip():
            raise serializers.ValidationError("Message body cannot be empty.")
        return value.strip()


class ConversationSerializer(serializers.ModelSerializer):
    """
    Serializer for the Conversation model.
    Includes nested serialization participants and messages.
    """
    messages = MessageSerializer(many=True, read_only=True)
    participants = UserSerializer(many=True, read_only=True)
    participant_count = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = ['conversation_id', 'participants', 'participant_count', 'messages', 'last_message', 'created_at']
        read_only_fields = ['conversation_id', 'participants', 'messages', 'created_at']

    def get_participant_count(self, obj):
        """
        Return the number of participants in the conversation.
        """
        return obj.participants.count()

    def get_last_message(self, obj):
        """
        Return the last message in the conversation.
        """
        last_message = obj.messages.last()
        if last_message:
            return MessageSerializer(last_message).data
        return None

    def validate(self, data):
        """
        Validate conversation data.
        """
        if hasattr(self, 'initial_data'):
            participants = self.initial_data.get('participants', [])
            if len(participants) < 2:
                raise serializers.ValidationError("A conversation must have at least 2 participants.")
        return data