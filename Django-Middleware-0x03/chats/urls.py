from django.urls import path, include
from rest_framework import routers
from rest_framework_nested import routers as nested_routers

from .views import ConversationViewSet, MessageViewSet

router = routers.DefaultRouter()
router.register(r'conversations', ConversationViewSet, basename='conversation')

# Create nested router for messages within conversations
conversations_router = nested_routers.NestedDefaultRouter(router, r'conversations', lookup='conversation')
conversations_router.register(r'messages', MessageViewSet, basename='conversation-messages')

urlpatterns = [
    path('', include(router.urls)),
    path('', include(conversations_router.urls)),
]