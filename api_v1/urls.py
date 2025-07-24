from django.urls import path
from api_v1.views import ReceiveFigmaJsonAPIView


urlpatterns = [
    path('figma/extract/wip/', ReceiveFigmaJsonAPIView.as_view()),
]