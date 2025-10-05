rom django.contrib import admin
from .models import User, Conversation, Message, Notification, MessageHistory


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ['email', 'first_name', 'last_name', 'role', 'created_at']
    list_filter = ['role', 'created_at']
    search_fields = ['email', 'first_name', 'last_name']


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ['conversation_id', 'created_at']
    list_filter = ['created_at']


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ['message_id', 'conversation', 'sender', 'receiver', 'parent_message', 'sent_at', 'edited', 'read']
    list_filter = ['sent_at', 'edited', 'read']
    search_fields = ['message_body', 'sender__email', 'receiver__email']
    raw_id_fields = ['parent_message']

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'sender', 'receiver', 'conversation', 'parent_message'
        )

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['notification_id', 'user', 'message', 'is_read', 'created_at']
    list_filter = ['is_read', 'created_at']
    search_fields = ['user__email', 'content']


@admin.register(MessageHistory)
class MessageHistoryAdmin(admin.ModelAdmin):
    list_display = ['history_id', 'message', 'edited_by', 'edited_at']
    list_filter = ['edited_at']
    search_fields = ['message__message_body', 'edited_by__email', 'old_content']