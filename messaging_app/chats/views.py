from rest_framework import viewsets, status, filters
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from .models import User, Conversation, Message
from .serializers import ConversationSerializer, MessageSerializer
from .permissions import (
    IsParticipantOfConversation,
    IsMessageSenderOrParticipant,
)
from .filters import MessageFilter, ConversationFilter
from .pagination import MessagePagination, ConversationPagination


class ConversationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for listing and creating conversations.
    """
    serializer_class = ConversationSerializer
    permission_classes = [IsAuthenticated, IsParticipantOfConversation]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = ConversationFilter
    search_fields = ['participants__email', 'participants__first_name', 'participants__last_name']
    ordering_fields = ['created_at', 'participants__email']
    ordering = ['-created_at']
    pagination_class = ConversationPagination

    def get_queryset(self):
        """
        This view should return a list of all the conversations
        for the currently authenticated user.
        """
        return Conversation.objects.filter(participants=self.request.user).distinct()

    def create(self, request, *args, **kwargs):
        """
        Create a new conversation with a list of participant emails.
        Expects `participants` in request data, a list of emails.
        """
        participant_emails = request.data.get('participants', [])
        if not isinstance(participant_emails, list):
            return Response(
                {"error": "Participants must be a list of emails."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Add the current user's email to the set to ensure they are included
        all_emails = set(participant_emails)
        all_emails.add(request.user.email)

        participants = User.objects.filter(email__in=all_emails)

        # Optional: Check if all provided emails were found
        if len(participants) != len(all_emails):
            found_emails = {p.email for p in participants}
            missing_emails = all_emails - found_emails
            return Response(
                {"error": f"Users not found: {', '.join(missing_emails)}"},
                status=status.HTTP_404_NOT_FOUND
            )

        conversation = Conversation.objects.create()
        conversation.participants.set(participants)
        serializer = self.get_serializer(conversation)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def get_permissions(self):
        """
        Instantiates and returns the list of permissions that this view requires.
        """
        if self.action == 'create':
            # Only authenticated users can create conversations
            permission_classes = [IsAuthenticated]
        else:
            # For other actions, check if user is participant
            permission_classes = [IsAuthenticated, IsParticipantOfConversation]

        return [permission() for permission in permission_classes]


class MessageViewSet(viewsets.ModelViewSet):
    """
    ViewSet for listing and creating messages within a conversation.
    """
    serializer_class = MessageSerializer
    permission_classes = [IsAuthenticated, IsMessageSenderOrParticipant]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = MessageFilter
    search_fields = ['message_body', 'sender__email', 'sender__first_name', 'sender__last_name']
    ordering_fields = ['sent_at', 'sender__email']
    ordering = ['sent_at']
    pagination_class = MessagePagination

    def get_queryset(self):
        """
        Filter messages by a `conversation_id` from the URL.
        Ensures user is a participant of the conversation.
        """
        conversation_pk = self.kwargs.get('conversation_pk')
        if conversation_pk:
            return Message.objects.filter(
                conversation__conversation_id=conversation_pk,
                conversation__participants=self.request.user
            ).select_related('sender', 'conversation')
        return Message.objects.none()

    def perform_create(self, serializer):
        """
        Set the sender of the message to the current authenticated user.
        """
        conversation_pk = self.kwargs.get('conversation_pk')
        try:
            conversation = Conversation.objects.get(conversation_id=conversation_pk)
        except Conversation.DoesNotExist:
            raise ValidationError("Conversation does not exist.")

        if self.request.user not in conversation.participants.all():
            return Response(
                {"error": "You are not a participant of this conversation."},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer.save(sender=self.request.user, conversation=conversation)