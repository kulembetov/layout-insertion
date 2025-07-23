from django.urls import path
from api_v1.views_ver_2 import APIReceiveJsonFromFigma
from api_v1.views import ReceiveFigmaJsonAPIView


urlpatterns = [
    path('figma/extract/', APIReceiveJsonFromFigma.as_view()),
    path('figma/extract/wip/', ReceiveFigmaJsonAPIView.as_view()),
]