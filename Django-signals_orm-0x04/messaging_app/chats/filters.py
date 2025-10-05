import django_filters
from django.db import models
from .models import Message, Conversation


class MessageFilter(django_filters.FilterSet):
    """
    Filter class for Message model to enable filtering by various criteria.
    """
    # Filter by sender email
    sender = django_filters.CharFilter(
        field_name='sender__email',
        lookup_expr='icontains',
        help_text='Filter messages by sender email (case-insensitive partial match)'
    )

    # Filter by message content
    message_body = django_filters.CharFilter(
        field_name='message_body',
        lookup_expr='icontains',
        help_text='Filter messages by content (case-insensitive partial match)'
    )

    # Filter by date range
    sent_after = django_filters.DateTimeFilter(
        field_name='sent_at',
        lookup_expr='gte',
        help_text='Filter messages sent after this datetime (YYYY-MM-DD HH:MM:SS)'
    )

    sent_before = django_filters.DateTimeFilter(
        field_name='sent_at',
        lookup_expr='lte',
        help_text='Filter messages sent before this datetime (YYYY-MM-DD HH:MM:SS)'
    )

    # Filter by specific date
    sent_date = django_filters.DateFilter(
        field_name='sent_at',
        lookup_expr='date',
        help_text='Filter messages sent on specific date (YYYY-MM-DD)'
    )

    # Filter by sender role
    sender_role = django_filters.ChoiceFilter(
        field_name='sender__role',
        choices=[
            ('admin', 'Admin'),
            ('host', 'Host'),
            ('guest', 'Guest'),
        ],
        help_text='Filter messages by sender role'
    )

    class Meta:
        model = Message
        fields = {
            'sender__email': ['exact', 'icontains'],
            'message_body': ['icontains'],
            'sent_at': ['exact', 'gte', 'lte', 'date'],
            'sender__role': ['exact'],
        }


class ConversationFilter(django_filters.FilterSet):
    """
    Filter class for Conversation model to enable filtering by participants.
    """
    # Filter conversations with specific participants
    participant = django_filters.CharFilter(
        field_name='participants__email',
        lookup_expr='icontains',
        help_text='Filter conversations by participant email (case-insensitive partial match)'
    )

    # Filter conversations with specific participant (exact match)
    participant_exact = django_filters.CharFilter(
        field_name='participants__email',
        lookup_expr='exact',
        help_text='Filter conversations by exact participant email'
    )

    # Filter by creation date range
    created_after = django_filters.DateTimeFilter(
        field_name='created_at',
        lookup_expr='gte',
        help_text='Filter conversations created after this datetime'
    )

    created_before = django_filters.DateTimeFilter(
        field_name='created_at',
        lookup_expr='lte',
        help_text='Filter conversations created before this datetime'
    )

    # Filter by number of participants
    min_participants = django_filters.NumberFilter(
        method='filter_min_participants',
        help_text='Filter conversations with at least this many participants'
    )

    max_participants = django_filters.NumberFilter(
        method='filter_max_participants',
        help_text='Filter conversations with at most this many participants'
    )

    def filter_min_participants(self, queryset, name, value):
        """Filter conversations with minimum number of participants."""
        if value is not None:
            return queryset.annotate(
                participant_count=models.Count('participants')
            ).filter(participant_count__gte=value)
        return queryset

    def filter_max_participants(self, queryset, name, value):
        """Filter conversations with maximum number of participants."""
        if value is not None:
            return queryset.annotate(
                participant_count=models.Count('participants')
            ).filter(participant_count__lte=value)
        return queryset

    class Meta:
        model = Conversation
        fields = {
            'participants__email': ['exact', 'icontains'],
            'created_at': ['exact', 'gte', 'lte'],
        }