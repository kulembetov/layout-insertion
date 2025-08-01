from django.urls import path
from django_app.api_v1.views import ReceiveFigmaJsonAPIView, FilterFigmaJson


urlpatterns = [
    path('figma/extract/', ReceiveFigmaJsonAPIView.as_view()),
    path('figma/filter/', FilterFigmaJson.as_view()),
]