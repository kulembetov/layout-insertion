from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status


from api_v1.services.figma_api import FigmaAPI
from api_v1.services.filters.filter_settings import FilterMode
from config.settings import FIGMA_TOKEN

from log_utils import setup_logger, logs

from api_v1.redis.utils import gen_key, set_cached_request
from .services.filters.filter_service import FilterFigmaApi
from api_v1.utils.helpers import json_dump


logger = setup_logger(__name__)

class ReceiveFigmaJsonAPIView(APIView):
    figma = FigmaAPI(token=FIGMA_TOKEN)

    @logs(logger, on=True)
    def get(self, request):
        file_id = request.data['file_id']
        self.figma.file_id = file_id
        logger.info(f'file_id: {file_id}')

        if request.data.get('filter'):
            filter_mode = request.data.get('filter').get('mode')
            filter_params = request.data.get('filter').get('params')
            figma_filtered = FilterFigmaApi(
                token=FIGMA_TOKEN,
                filter_params=filter_params,
                file_id=file_id
            )

            match filter_mode:
                case FilterMode.SPECIFIC_SLIDES.value:
                    data = figma_filtered.extract_specific_slides()

                case FilterMode.SPECIFIC_BLOCKS.value:
                    data = figma_filtered.extract_specific_blocks()

                case FilterMode.BY_TYPE.value:
                    data = figma_filtered.extract_by_type()

                case FilterMode.READY_TO_DEV.value: 
                    data = figma_filtered.extract_ready_to_dev()
                
                case _:
                    raise Exception(f'Unknown filter mode: {filter_mode}')

            key = gen_key(file_id, filter_mode, filter_params)

        else:
            data = self.figma.extract()
            key = gen_key(file_id)


        json_dump(data, 'output.json')

        set_cached_request(key, data)
        return Response(data=data, status=status.HTTP_200_OK)
