from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from api_v1.services.filters.filter_settings import FilterMode
from api_v1.implemented import figma_instance

from log_utils import setup_logger, logs

from api_v1.redis.utils import gen_key, set_cached_request
from api_v1.utils.helpers import json_dump


logger = setup_logger(__name__)

class ReceiveFigmaJsonAPIView(APIView):
    @logs(logger, on=True)
    def get(self, request):
        file_id = request.data['file_id']
        figma_instance.file_id = file_id
        logger.info(f'file_id: {file_id}')

        if request.data.get('filter'):
            from api_v1.implemented import filter_figma_instance

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

            key = gen_key(file_id, filter_type, filter_names)

        else:
            data = figma_instance.extract()
            key = gen_key(file_id)

        json_dump(data, 'output.json')

        set_cached_request(key, data)
        return Response(data=data, status=status.HTTP_200_OK)
