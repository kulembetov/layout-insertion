from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from django_app.api_v1.services.filters.filter_settings import FilterMode
from django_app.api_v1.utils.helpers import json_dump

from log_utils import setup_logger, logs


logger = setup_logger(__name__)

class ReceiveFigmaJsonAPIView(APIView):
    """Receive data from Figma."""

    @logs(logger, on=True)
    def get(self, request):
        from .implemented import figma_instance

        try:
            file_id = request.data['file_id']
            logger.info(f'file_id: {file_id}')
        except KeyError:
            return Response(
                data={'message': "Request doesn't contain 'file_id'. Bad request."},
                status=status.HTTP_400_BAD_REQUEST
            )

        figma_instance.file_id = file_id
        data = figma_instance.extract()

        json_dump(data, 'output.json')
        return Response(data=data, status=status.HTTP_200_OK)
    

class FilterFigmaJson(APIView):
    """Filter data received from Figma and add it into database."""

    @logs(logger, on=True)
    def get(self, request):
        try:
            file_id = request.data['file_id']
            logger.info(f'file_id: {file_id}')
        except KeyError:
            return Response(
                data={'message': "Request doesn't contain 'file_id'. Bad request."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if request.data.get('filter'):
            from .implemented import filter_figma_instance

            filter_type: str = request.data.get('filter').get('type')
            filter_names: list[str] = request.data.get('filter').get('name')

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
                    raise ValueError(f'Unknown filter type: {filter_type}')
                
            return Response(data=data, status=status.HTTP_200_OK)


        return Response(
            data={'message': "Request doesn't contain 'filter'. Bad request."},
            status=status.HTTP_400_BAD_REQUEST
        )
