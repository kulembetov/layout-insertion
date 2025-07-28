import json

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status


from api_v1.services.figma_api import FigmaAPI
from api_v1.services.filters.filter_settings import FilterMode
from config.settings import FIGMA_TOKEN

from log_utils import setup_logger

from .services.redis_utils import get_cached_request, set_cached_request
from .services.filters.filter_service import FilterFigmaApi


logg = setup_logger(__name__)

class ReceiveFigmaJsonAPIView(APIView):
    figma = FigmaAPI(token=FIGMA_TOKEN)

    def get(self, request):
        file_id = request.data['file_id']
        if get_cached_request(file_id):
            return Response(data=get_cached_request(file_id), status=status.HTTP_200_OK)

        self.figma.file_id = file_id
        logg.info(f'file_id: {file_id}')

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
                
                case _:
                    raise Exception(f'Unknown filter mode: {filter_mode}')

        else:
            data = self.figma.extract()

        with open("output.json", "w", encoding="utf-8") as outfile:
            json.dump(data, outfile, ensure_ascii=False, indent=4)

        set_cached_request(file_id, data)

        return Response(data=data, status=status.HTTP_200_OK)
