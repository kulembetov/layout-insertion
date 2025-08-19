from django.urls import path

from django_app.api_v1.views import DeletePresentationLayout, DeleteSlideLayout, FilterFigmaJson, ReceiveFigmaJsonAPIView, ReceiveFigmaPresentationLayout, ReceiveFigmaPresentationLayoutFullData, ReceiveFigmaPresentationLayoutSlides, ReceiveSlideLayoutFullData

urlpatterns = [
    # Figma API endpoints
    path("figma/extract/", ReceiveFigmaJsonAPIView.as_view()),
    path("figma/filter/", FilterFigmaJson.as_view()),
    # Presentation Layout endpoints
    path("figma/get/presentations/", ReceiveFigmaPresentationLayout.as_view()),
    path("figma/get/presentation_slides/<uuid:id>", ReceiveFigmaPresentationLayoutSlides.as_view()),
    path("figma/get/presentation_full_data/<uuid:id>", ReceiveFigmaPresentationLayoutFullData.as_view()),
    path("figma/delete/presentation/<uuid:id>", DeletePresentationLayout.as_view()),
    # Slide Layout endpoints
    path("figma/get/slide_full_data/<uuid:id>", ReceiveSlideLayoutFullData.as_view()),  # GET для одного слайда
    path("figma/get/slide_full_data/", ReceiveSlideLayoutFullData.as_view()),  # POST для нескольких слайдов
    path("figma/delete/slide/<uuid:id>", DeleteSlideLayout.as_view()),  # DELETE для одного слайда
    path("figma/delete/slide/", DeleteSlideLayout.as_view()),  # POST для нескольких слайдов
]
