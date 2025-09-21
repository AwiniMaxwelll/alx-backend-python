from django.shortcuts import render
from rest_framework import viewsets, status, filters
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.throttling import UserRateThrottle
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Prefetch

from .models import User, Conversation, Message
from .serializers import ConversationSerializer, MessageSerializer


class ConversationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for listing, retrieving, and creating conversations.
    Optimized for performance with prefetching and pagination.
    """
    serializer_class = ConversationSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = LimitOffsetPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['participants__email']
    ordering_fields = ['created_at']
    ordering = ['-created_at']
    throttle_classes = [UserRateThrottle]  # Prevent abuse

    def get_queryset(self):
        """
        Return conversations for the authenticated user, excluding soft-deleted ones.
        Prefetch participants and last message for efficiency.
        """
        return Conversation.objects.filter(
            participants=self.request.user,
            deleted_at__isnull=True
        ).prefetch_related(
            'participants',
            Prefetch('messages', queryset=Message.objects.select_related('sender').filter(deleted_at__isnull=True).order_by('-sent_at')[:1], to_attr='last_messages')
        )

    def create(self, request, *args, **kwargs):
        """
        Create a new conversation with participant emails.
        Uses model's get_or_create_conversation for deduplication.
        """
        participant_emails = request.data.get('participants', [])
        if not isinstance(participant_emails, list) or len(participant_emails) < 1:
            return Response(
                {"error": "Participants must be a non-empty list of emails."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Include current user
        all_emails = set(participant_emails)
        all_emails.add(request.user.email)

        # Fetch users, excluding soft-deleted
        participants = User.objects.filter(email__in=all_emails, deleted_at__isnull=True)

        if len(participants) != len(all_emails):
            found_emails = {p.email for p in participants}
            missing_emails = all_emails - found_emails
            return Response(
                {"error": f"Users not found or deleted: {', '.join(missing_emails)}"},
                status=status.HTTP_404_NOT_FOUND
            )

        # Use model's method to avoid duplicates
        conversation = Conversation.get_or_create_conversation([p.user_id for p in participants])
        serializer = self.get_serializer(conversation)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def retrieve(self, request, *args, **kwargs):
        """
        Retrieve a single conversation with optimized queryset.
        """
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)


class MessageViewSet(viewsets.ModelViewSet):
    """
    ViewSet for listing and creating messages within a conversation.
    Nested under conversations via conversation_pk.
    """
    serializer_class = MessageSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = LimitOffsetPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['message_body', 'sender__email']
    ordering_fields = ['sent_at']
    ordering = ['sent_at']
    throttle_classes = [UserRateThrottle]  # Prevent spam

    def get_queryset(self):
        """
        Filter messages by conversation_id from URL.
        Ensures user is a participant and excludes soft-deleted messages.
        """
        conversation_pk = self.kwargs.get('conversation_pk')
        if conversation_pk:
            return Message.objects.filter(
                conversation__conversation_id=conversation_pk,
                conversation__participants=self.request.user,
                conversation__deleted_at__isnull=True,
                deleted_at__isnull=True
            ).select_related('sender')
        return Message.objects.none()

    def perform_create(self, serializer):
        """
        Create a message, setting sender to current user.
        Validate participation and update status if needed.
        """
        conversation_pk = self.kwargs.get('conversation_pk')
        try:
            conversation = Conversation.objects.get(
                conversation_id=conversation_pk,
                deleted_at__isnull=True
            )
        except Conversation.DoesNotExist:
            raise ValidationError("Conversation does not exist or is deleted.")

        if self.request.user not in conversation.participants.all():
            raise ValidationError("You are not a participant of this conversation.")

        serializer.save(sender=self.request.user, conversation=conversation)
        # Optional: Update message status to 'sent' (already default in model)
        # Trigger async notification if needed (e.g., via Celery)

    def list(self, request, *args, **kwargs):
        """
        List messages with pagination and optimized queryset.
        """
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
