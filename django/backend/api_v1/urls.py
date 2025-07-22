from django.urls import path
from api_v1.views_ver_2 import APIReceiveJsonFromFigma


urlpatterns = [
    path('figma/extract/', APIReceiveJsonFromFigma.as_view()),
]