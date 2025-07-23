import json

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from api_v1.services.figma_api import FigmaAPI
from api_v1.services.filter_service import FilterMode, FilterConfig
from config.settings import FIGMA_TOKEN

from logger import setup_logger


logg = setup_logger(__name__)

class ReceiveFigmaJsonAPIView(APIView):
    figma = FigmaAPI(token=FIGMA_TOKEN)

    def get(self, request):
        file_id = request.data['file_id']
        self.figma.file_id = file_id
        logg.info(f'file_id: {file_id}')

        if request.data.get('filter'):
            filter_mode = request.data.get('filter').get('mode')
            filter_params = request.data.get('filter').get('params')

            match filter_mode:
                case FilterMode.ALL.value:
                    filter_config = FilterConfig(
                        mode=FilterMode.ALL
                    )

                case FilterMode.SPECIFIC_SLIDES.value:
                    filter_config = FilterConfig(
                        mode=FilterMode.SPECIFIC_SLIDES,
                        target_slides=filter_params,
                        require_z_index=True
                    )

                case FilterMode.SPECIFIC_BLOCKS.value:
                    filter_config = FilterConfig(
                        mode=FilterMode.SPECIFIC_BLOCKS,
                        target_block_types=filter_params,
                    )

                case FilterMode.BY_TYPE.value:
                    filter_config = FilterConfig(
                        mode=FilterMode.BY_TYPE,
                        target_containers=filter_params
                    )

                case _:
                    raise Exception(f'Unknown filter mode: {filter_mode}')

            data = self.figma.extract(filter_config=filter_config)

        else:
            data = self.figma.extract()

        with open("output.json", "w", encoding="utf-8") as outfile:
            json.dump(data, outfile, ensure_ascii=False, indent=4)

        return Response(data=data, status=status.HTTP_200_OK)
