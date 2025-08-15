from django.urls import path

from django_app.api_v1.views import DeletePresentationLayout, FilterFigmaJson, ReceiveFigmaJsonAPIView, ReceiveFigmaPresentationLayout, ReceiveFigmaPresentationLayoutFullData, ReceiveFigmaPresentationLayoutSlides

urlpatterns = [
    path("figma/extract/", ReceiveFigmaJsonAPIView.as_view()),
    path("figma/filter/", FilterFigmaJson.as_view()),
    path("figma/get/presentations/", ReceiveFigmaPresentationLayout.as_view()),
    path("figma/get/presentation_slides/<uuid:id>", ReceiveFigmaPresentationLayoutSlides.as_view()),
    path("figma/get/presentation_full_data/<uuid:id>", ReceiveFigmaPresentationLayoutFullData.as_view()),
    path("figma/delete/presentation/<uuid:id>", DeletePresentationLayout.as_view()),
]
