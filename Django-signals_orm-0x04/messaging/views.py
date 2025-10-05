from django.db import models
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page

from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Prefetch

from .models import User, Conversation, Message, build_message_tree
from .serializers import ConversationSerializer, MessageSerializer
from .permissions import (
    IsParticipantOfConversation,
    IsMessageSenderOrParticipant
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

    @action(detail=False, methods=['delete'], url_path='delete-account')
    def delete_user_account(self, request):
        """
        Allow a user to delete their own account.
        This will trigger the post_delete signal to clean up related data.
        """
        user = request.user

        # Optional: Add confirmation check
        confirmation = request.data.get('confirm_deletion', False)
        if not confirmation:
            return Response(
                {"error": "Please confirm deletion by setting 'confirm_deletion' to true"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            user_email = user.email
            user.delete()  # This will trigger the post_delete signal
            return Response(
                {"message": f"User account {user_email} has been successfully deleted"},
                status=status.HTTP_204_NO_CONTENT
            )
        except Exception as e:
            return Response(
                {"error": f"Failed to delete account: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

@method_decorator(cache_page(60), name='list')
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
        Filter messages by conversation_id with optimized threading queries using select_related.
        """
        conversation_pk = self.kwargs.get('conversation_pk')
        if conversation_pk:
            # Use Message.objects.filter with select_related for optimization
            return Message.objects.filter(
                conversation__conversation_id=conversation_pk,
                conversation__participants=self.request.user
            ).select_related('sender', 'conversation', 'parent_message').prefetch_related(
                'replies__sender'
            ).order_by('sent_at')
        return Message.objects.none()

    @action(detail=False, methods=['get'], url_path='threaded')
    def get_threaded_view(self, request, conversation_pk=None):
        """
        Get messages in threaded format with optimized queries.
        """
        try:
            conversation = Conversation.objects.get(
                conversation_id=conversation_pk,
                participants=request.user
            )
        except Conversation.DoesNotExist:
            return Response(
                {"error": "Conversation not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        # Get all messages with optimized queries using Message.objects.filter and select_related
        messages = Message.objects.filter(
            conversation=conversation
        ).select_related('sender', 'parent_message').prefetch_related(
            'replies__sender'
        ).order_by('sent_at')

        # Build threaded structure
        threaded_messages = build_message_tree(messages)

        # Serialize the threaded data
        def serialize_thread(thread_node):
            message = thread_node['message']
            return {
                'message_id': str(message.message_id),
                'sender': {
                    'email': message.sender.email,
                    'first_name': message.sender.first_name,
                    'last_name': message.sender.last_name
                },
                'message_body': message.message_body,
                'sent_at': message.sent_at,
                'edited': message.edited,
                'parent_message_id': str(message.parent_message.message_id) if message.parent_message else None,
                'depth': message.get_thread_depth(),
                'replies': [serialize_thread(reply) for reply in thread_node['replies']]
            }

        serialized_data = [serialize_thread(thread) for thread in threaded_messages]

        return Response({
            'conversation_id': str(conversation.conversation_id),
            'threaded_messages': serialized_data
        })

    @action(detail=True, methods=['get'], url_path='thread')
    def get_message_thread(self, request, pk=None, conversation_pk=None):
        """
        Get a specific message and all its replies recursively.
        """
        try:
            # Verify conversation access
            conversation = Conversation.objects.get(
                conversation_id=conversation_pk,
                participants=request.user
            )

            # Get the message thread using Message.objects.filter with select_related
            thread_messages = Message.objects.filter(
                message_id=pk,
                conversation=conversation
            ).select_related('sender', 'parent_message').prefetch_related(
                'replies__sender',
                'replies__replies__sender'
            )

            if not thread_messages.exists():
                return Response(
                    {"error": "Message not found"},
                    status=status.HTTP_404_NOT_FOUND
                )

            # Serialize the thread
            serialized_messages = []
            for message in thread_messages:
                serialized_messages.append({
                    'message_id': str(message.message_id),
                    'sender': {
                        'email': message.sender.email,
                        'first_name': message.sender.first_name,
                        'last_name': message.sender.last_name
                    },
                    'message_body': message.message_body,
                    'sent_at': message.sent_at,
                    'edited': message.edited,
                    'parent_message_id': str(message.parent_message.message_id) if message.parent_message else None,
                    'depth': message.get_thread_depth()
                })

            return Response({
                'thread_messages': serialized_messages
            })

        except Conversation.DoesNotExist:
            return Response(
                {"error": "Conversation not found"},
                status=status.HTTP_404_NOT_FOUND
            )

    def perform_create(self, serializer):
        """
        Enhanced create method to handle reply creation with sender and receiver.
        """
        conversation_pk = self.kwargs.get('conversation_pk')
        parent_message_id = self.request.data.get('parent_message_id')
        receiver_email = self.request.data.get('receiver')

        try:
            conversation = Conversation.objects.get(conversation_id=conversation_pk)
        except Conversation.DoesNotExist:
            raise ValidationError("Conversation does not exist.")

        if self.request.user not in conversation.participants.all():
            raise ValidationError("You are not a participant of this conversation.")

        # Handle receiver - find the recipient user
        receiver = None
        if receiver_email:
            try:
                receiver = User.objects.get(email=receiver_email)
                if receiver not in conversation.participants.all():
                    raise ValidationError("Receiver is not a participant of this conversation.")
            except User.DoesNotExist:
                raise ValidationError("Receiver user not found.")
        else:
            # If no specific receiver, default to the first other participant
            other_participants = conversation.participants.exclude(id=self.request.user.id)
            if other_participants.exists():
                receiver = other_participants.first()

        # Handle parent message if this is a reply
        parent_message = None
        if parent_message_id:
            try:
                parent_message = Message.objects.get(
                    message_id=parent_message_id,
                    conversation=conversation
                )
            except Message.DoesNotExist:
                raise ValidationError("Parent message not found in this conversation.")

        serializer.save(
            sender=self.request.user,
            receiver=receiver,
            conversation=conversation,
            parent_message=parent_message
        )

    @action(detail=False, methods=['get'], url_path='my-messages')
    def get_user_messages(self, request, conversation_pk=None):
        """
        Get all messages sent by or received by the current user in a conversation.
        """
        try:
            conversation = Conversation.objects.get(
                conversation_id=conversation_pk,
                participants=request.user
            )
        except Conversation.DoesNotExist:
            return Response(
                {"error": "Conversation not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        # Use Message.objects.filter to get messages where user is sender or receiver
        user_messages = Message.objects.filter(
            conversation=conversation
        ).filter(
            models.Q(sender=request.user) | models.Q(receiver=request.user)
        ).select_related('sender', 'receiver', 'conversation').order_by('sent_at')

        serializer = MessageSerializer(user_messages, many=True)
        return Response({
            'conversation_id': str(conversation.conversation_id),
            'user_messages': serializer.data
        })

    @action(detail=False, methods=['get'], url_path='unread')
    def get_unread_messages(self, request, conversation_pk=None):
        """
        Get all unread messages for the current user in a specific conversation.
        """
        try:
            conversation = Conversation.objects.get(
                conversation_id=conversation_pk,
                participants=request.user
            )
        except Conversation.DoesNotExist:
            return Response(
                {"error": "Conversation not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        # Use custom manager's unread_for_user method with additional .only() optimization
        unread_messages = Message.unread.unread_for_user(request.user).filter(
            conversation=conversation
        ).only(
            'message_id',
            'message_body',
            'sent_at',
            'sender__email',
            'sender__first_name',
            'sender__last_name',
            'conversation__conversation_id',
            'read'
        )

        serializer = MessageSerializer(unread_messages, many=True)
        return Response({
            'conversation_id': str(conversation.conversation_id),
            'unread_messages': serializer.data,
            'unread_count': unread_messages.count()
        })

    @action(detail=False, methods=['get'], url_path='unread-count')
    def get_unread_count(self, request, conversation_pk=None):
        """
        Get the count of unread messages for the current user.
        """
        if conversation_pk:
            try:
                conversation = Conversation.objects.get(
                    conversation_id=conversation_pk,
                    participants=request.user
                )
                # Use custom manager's unread_for_user method with .only() for count queries
                unread_count = Message.unread.unread_for_user(request.user).filter(
                    conversation=conversation
                ).only('message_id').count()
            except Conversation.DoesNotExist:
                return Response(
                    {"error": "Conversation not found"},
                    status=status.HTTP_404_NOT_FOUND
                )
        else:
            # Use custom manager's unread_count_for_user method
            unread_count = Message.unread.unread_count_for_user(request.user)

        return Response({
            'unread_count': unread_count
        })

    @action(detail=False, methods=['post'], url_path='mark-read')
    def mark_messages_read(self, request, conversation_pk=None):
        """
        Mark messages as read for the current user.
        """
        message_ids = request.data.get('message_ids', [])

        try:
            conversation = Conversation.objects.get(
                conversation_id=conversation_pk,
                participants=request.user
            )
        except Conversation.DoesNotExist:
            return Response(
                {"error": "Conversation not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        # Use custom manager to mark messages as read
        updated_count = Message.unread.mark_as_read(
            user=request.user,
            message_ids=message_ids if message_ids else None
        )

        return Response({
            'message': f'Marked {updated_count} messages as read',
            'updated_count': updated_count
        })