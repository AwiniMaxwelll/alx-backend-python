from rest_framework import permissions
from .models import Conversation, Message


class IsParticipantOfConversation(permissions.BasePermission):
    """
    Custom permission to only allow participants of a conversation to access it.
    """

    def has_permission(self, request, view):
        """
        Check if user is authenticated and has permission to access the conversation.
        """
        if not request.user.is_authenticated:
            return False

        # For conversation endpoints
        if hasattr(view, 'kwargs') and 'pk' in view.kwargs:
            try:
                conversation = Conversation.objects.get(conversation_id=view.kwargs['pk'])
                return request.user in conversation.participants.all()
            except Conversation.DoesNotExist:
                return False

        # For nested message endpoints
        if hasattr(view, 'kwargs') and 'conversation_pk' in view.kwargs:
            try:
                conversation = Conversation.objects.get(
                    conversation_id=view.kwargs['conversation_pk']
                )
                return request.user in conversation.participants.all()
            except Conversation.DoesNotExist:
                return False

        return True

    def has_object_permission(self, request, view, obj):
        """
        Check if user has permission to access specific object.
        """
        if not request.user.is_authenticated:
            return False

        # For Conversation objects
        if isinstance(obj, Conversation):
            return request.user in obj.participants.all()

        # For Message objects
        if isinstance(obj, Message):
            return request.user in obj.conversation.participants.all()

        return False


class IsMessageSenderOrParticipant(permissions.BasePermission):
    """
    Custom permission to allow message operations based on user role.
    - Any participant can view messages
    - Only message sender can update/delete their own messages
    """

    def has_permission(self, request, view):
        """
        Check if user is authenticated and participant of conversation.
        """
        if not request.user.is_authenticated:
            return False

        if hasattr(view, 'kwargs') and 'conversation_pk' in view.kwargs:
            try:
                conversation = Conversation.objects.get(
                    conversation_id=view.kwargs['conversation_pk']
                )
                return request.user in conversation.participants.all()
            except Conversation.DoesNotExist:
                return False

        return True

    def has_object_permission(self, request, view, obj):
        """
        Check specific permissions for message operations.
        """
        if not request.user.is_authenticated:
            return False

        # Must be participant of conversation
        if not (request.user in obj.conversation.participants.all()):
            return False

        # GET (view) - any participant can view
        if request.method in permissions.SAFE_METHODS:
            return True

        # PUT, PATCH, DELETE - only message sender
        if request.method in ['PUT', 'PATCH', 'DELETE']:
            return obj.sender == request.user

        return False


class IsOwnerOrParticipant(permissions.BasePermission):
    """
    Enhanced permission to ensure users can only access their own conversations and messages.
    """

    def has_permission(self, request, view):
        """
        Check if user is authenticated.
        """
        return request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        """
        Check if user has permission to access the object.
        """
        if not request.user.is_authenticated:
            return False

        # For Conversation objects
        if isinstance(obj, Conversation):
            return request.user in obj.participants.all()

        # For Message objects
        if isinstance(obj, Message):
            is_participant = request.user in obj.conversation.participants.all()

            # For safe methods (GET, HEAD, OPTIONS), any participant can access
            if request.method in permissions.SAFE_METHODS:
                return is_participant

            # For unsafe methods (PUT, PATCH, DELETE), only sender can modify
            if request.method in ['PUT', 'PATCH', 'DELETE']:
                return obj.sender == request.user and is_participant

            return is_participant

        return False


class IsConversationParticipant(permissions.BasePermission):
    """
    Permission to check if user is a participant in the conversation.
    Enhanced version with better error handling.
    """

    def has_permission(self, request, view):
        """
        Check if user is authenticated and participant of conversation.
        """
        if not request.user.is_authenticated:
            return False

        if hasattr(view, 'kwargs') and 'conversation_pk' in view.kwargs:
            try:
                conversation = Conversation.objects.get(
                    conversation_id=view.kwargs['conversation_pk']
                )
                return request.user in conversation.participants.all()
            except Conversation.DoesNotExist:
                return False
        return True

    def has_object_permission(self, request, view, obj):
        """
        Check object-level permissions.
        """
        if not request.user.is_authenticated:
            return False

        if isinstance(obj, Message):
            return request.user in obj.conversation.participants.all()

        return False