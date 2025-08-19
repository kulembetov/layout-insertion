from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from db_work.services import PresentationLayoutManager, SlideLayoutManager
from django_app.api_v1.services.filters.filter_settings import FilterMode
from django_app.api_v1.utils.helpers import json_dump
from log_utils import logs, setup_logger

logger = setup_logger(__name__)


class ReceiveFigmaJsonAPIView(APIView):
    """Receive data from Figma."""

    @logs(logger, on=True)
    def get(self, request):
        from .implemented import figma_instance

        try:
            file_id = request.data["file_id"]
            logger.info(f"file_id: {file_id}")
        except KeyError:
            return Response(data={"message": "Request doesn't contain 'file_id'. Bad request."}, status=status.HTTP_400_BAD_REQUEST)

        figma_instance.file_id = file_id
        data = figma_instance.extract()

        json_dump(data, "output.json")
        return Response(data=data, status=status.HTTP_200_OK)


class FilterFigmaJson(APIView):
    """Filter data received from Figma and add it into database."""

    @logs(logger, on=True)
    def get(self, request) -> Response:
        try:
            file_id = request.data["file_id"]
            logger.info(f"file_id: {file_id}")
        except KeyError:
            return Response(data={"message": "Request doesn't contain 'file_id'. Bad request."}, status=status.HTTP_400_BAD_REQUEST)

        if request.data.get("filter"):
            from .implemented import filter_figma_instance

            filter_type: str = request.data.get("filter").get("type", "")
            filter_names: list[int | str] = request.data.get("filter").get("name", [])

            filter_figma_instance.file_id = file_id
            filter_figma_instance.filter_names = filter_names

            match filter_type:
                case FilterMode.SLIDE_GROUP.value:
                    data = filter_figma_instance.extract_slide_group()

                case FilterMode.SLIDE_NAME.value:
                    data = filter_figma_instance.extract_slide_name()

                case FilterMode.STATUS.value:
                    data = filter_figma_instance.extract_status()

                case _:
                    raise ValueError(f"Unknown filter type: {filter_type}")

            return Response(data=data, status=status.HTTP_200_OK)

        return Response(data={"message": "Request doesn't contain 'filter'. Bad request."}, status=status.HTTP_400_BAD_REQUEST)


class ReceiveFigmaPresentationLayout(APIView):
    """API endpoint to retrieve all presentation layout names from the database."""

    @logs(logger, on=True)
    def get(self, request) -> Response:
        presentation_manager = PresentationLayoutManager()
        names = presentation_manager.get_presentation_layout_ids_names()

        return Response(names if names is not None else [])


class ReceiveFigmaPresentationLayoutSlides(APIView):
    """API endpoint to retrieve slides for a specific presentation layout by ID."""

    @logs(logger, on=True)
    def get(self, request, id=None) -> Response:
        if not id:
            return Response(data={"message": "Presentation layout ID is required"}, status=status.HTTP_400_BAD_REQUEST)

        logger.info(f"Retrieving slides for presentation layout ID: {id}")

        slide_manager = SlideLayoutManager()
        slides = slide_manager.get_slides_by_presentation_layout_id(str(id))

        return Response(slides if slides is not None else [])


class ReceiveFigmaPresentationLayoutFullData(APIView):
    """API endpoint to retrieve presentation layout structure by ID with all related tables.

    GET method returns structure with IDs only for understanding table relationships.
    """

    @logs(logger, on=True)
    def get(self, request, id=None) -> Response:
        if not id:
            return Response(data={"message": "Presentation layout ID is required"}, status=status.HTTP_400_BAD_REQUEST)

        logger.info(f"Retrieving structure for presentation layout ID: {id}")

        presentation_manager = PresentationLayoutManager()

        try:
            # Получаем структуру связей presentation layout
            structure_data = presentation_manager.get_presentation_layout_structure(str(id))

            if structure_data is None:
                return Response(data={"message": f"Presentation layout with ID {id} not found"}, status=status.HTTP_404_NOT_FOUND)

            logger.info(f"Successfully retrieved structure for presentation layout ID: {id}")

            # Получаем output_dir из query параметров (опционально)
            output_dir = request.GET.get("output_dir", "my_output")

            # Автоматически сохраняем структуру в файл
            try:
                filepath = presentation_manager.save_presentation_layout_structure_to_file(str(id), output_dir=output_dir)

                if filepath:
                    # Получаем информацию о файле
                    import os

                    file_size = os.path.getsize(filepath)
                    filename = os.path.basename(filepath)

                    # Добавляем информацию о сохраненном файле в ответ
                    structure_data["file_info"] = {"filepath": filepath, "filename": filename, "file_size_bytes": file_size, "file_size_human": f"{file_size:,} байт", "saved_at": structure_data["metadata"]["extracted_at"]}

                    logger.info(f"Structure automatically saved to file: {filepath}")
                else:
                    logger.warning("Failed to save structure to file, but continuing with response")

            except Exception as file_error:
                logger.warning(f"Failed to save to file: {str(file_error)}, continuing with response")
                # Не прерываем выполнение, просто логируем ошибку сохранения

            return Response(data=structure_data, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error retrieving presentation layout structure: {str(e)}")
            return Response(data={"message": f"Internal server error: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class DeletePresentationLayout(APIView):
    """API endpoint to delete a presentation layout with all related data."""

    @logs(logger, on=True)
    def delete(self, request, id=None) -> Response:
        if not id:
            return Response(data={"message": "Presentation layout ID is required"}, status=status.HTTP_400_BAD_REQUEST)

        logger.info(f"Deleting presentation layout ID: {id}")

        presentation_manager = PresentationLayoutManager()

        try:
            # Получаем сводку перед удалением (опционально)
            summary = presentation_manager.get_deletion_summary(str(id))
            if summary is None:
                return Response(data={"message": f"Presentation layout with ID {id} not found"}, status=status.HTTP_404_NOT_FOUND)

            # Выполняем удаление
            deletion_result = presentation_manager.delete_presentation_layout_structure(str(id))

            if deletion_result:
                logger.info(f"Successfully deleted presentation layout ID: {id}")
                return Response(data={"message": f"Presentation layout {id} and all related data successfully deleted", "deleted_presentation_id": str(id), "deletion_summary": summary}, status=status.HTTP_200_OK)
            else:
                logger.error(f"Failed to delete presentation layout ID: {id}")
                return Response(data={"message": f"Failed to delete presentation layout {id}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        except Exception as e:
            logger.error(f"Error deleting presentation layout {id}: {str(e)}")
            return Response(data={"message": f"Internal server error: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ReceiveSlideLayoutFullData(APIView):
    """API endpoint to retrieve slide layout structure by IDs with all related tables.

    Supports both single ID via URL parameter and multiple IDs via POST request body.
    """

    @logs(logger, on=True)
    def get(self, request, id=None) -> Response:
        """GET method for single slide layout ID via URL parameter."""
        if not id:
            return Response(data={"message": "Slide layout ID is required"}, status=status.HTTP_400_BAD_REQUEST)

        logger.info(f"Retrieving structure for slide layout ID: {id}")

        slide_manager = SlideLayoutManager()

        try:
            # Получаем структуру связей slide layout (передаем как список)
            structure_data = slide_manager.get_slide_layout_structure([str(id)])

            if structure_data is None:
                return Response(data={"message": f"Slide layout with ID {id} not found"}, status=status.HTTP_404_NOT_FOUND)

            logger.info(f"Successfully retrieved structure for slide layout ID: {id}")
            return Response(data=structure_data, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error retrieving slide layout structure: {str(e)}")
            return Response(data={"message": f"Internal server error: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @logs(logger, on=True)
    def post(self, request) -> Response:
        """POST method for multiple slide layout IDs via request body."""
        slide_ids = request.data.get("slide_ids", [])

        if not slide_ids or not isinstance(slide_ids, list):
            return Response(data={"message": "slide_ids array is required in request body"}, status=status.HTTP_400_BAD_REQUEST)

        logger.info(f"Retrieving structure for {len(slide_ids)} slide layouts")

        slide_manager = SlideLayoutManager()

        try:
            # Получаем структуру связей slide layouts
            structure_data = slide_manager.get_slide_layout_structure(slide_ids)

            if structure_data is None:
                return Response(data={"message": "No slide layouts found"}, status=status.HTTP_404_NOT_FOUND)

            logger.info(f"Successfully retrieved structure for {len(slide_ids)} slide layouts")
            return Response(data=structure_data, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error retrieving slide layouts structure: {str(e)}")
            return Response(data={"message": f"Internal server error: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class DeleteSlideLayout(APIView):
    """API endpoint to delete slide layouts with all related data.

    Supports both single ID via URL parameter and multiple IDs via POST request body.
    """

    @logs(logger, on=True)
    def delete(self, request, id=None) -> Response:
        """DELETE method for single slide layout ID via URL parameter."""
        if not id:
            return Response(data={"message": "Slide layout ID is required"}, status=status.HTTP_400_BAD_REQUEST)

        logger.info(f"Deleting slide layout ID: {id}")

        slide_manager = SlideLayoutManager()

        try:
            # Выполняем удаление (передаем как список)
            deletion_result = slide_manager.delete_slide_layout_structure([str(id)])

            if deletion_result["success"]:
                logger.info(f"Successfully deleted slide layout ID: {id}")
                return Response(data={"message": f"Slide layout {id} and all related data successfully deleted", "deletion_result": deletion_result}, status=status.HTTP_200_OK)
            else:
                logger.error(f"Failed to delete slide layout ID: {id}")
                return Response(data={"message": f"Failed to delete slide layout {id}", "deletion_result": deletion_result}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        except Exception as e:
            logger.error(f"Error deleting slide layout {id}: {str(e)}")
            return Response(data={"message": f"Internal server error: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @logs(logger, on=True)
    def post(self, request) -> Response:
        """POST method for multiple slide layout IDs via request body."""
        slide_ids = request.data.get("slide_ids", [])

        if not slide_ids or not isinstance(slide_ids, list):
            return Response(data={"message": "slide_ids array is required in request body"}, status=status.HTTP_400_BAD_REQUEST)

        logger.info(f"Deleting {len(slide_ids)} slide layouts")

        slide_manager = SlideLayoutManager()

        try:
            # Выполняем удаление
            deletion_result = slide_manager.delete_slide_layout_structure(slide_ids)

            if deletion_result["success"]:
                logger.info(f"Successfully deleted {deletion_result['total_deleted']} slide layouts")
                return Response(data={"message": f"Successfully deleted {deletion_result['total_deleted']} out of {deletion_result['total_requested']} slide layouts", "deletion_result": deletion_result}, status=status.HTTP_200_OK)
            else:
                logger.error(f"Failed to delete slide layouts: {deletion_result['message']}")
                return Response(data={"message": f"Failed to delete slide layouts: {deletion_result['message']}", "deletion_result": deletion_result}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        except Exception as e:
            logger.error(f"Error deleting slide layouts: {str(e)}")
            return Response(data={"message": f"Internal server error: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
