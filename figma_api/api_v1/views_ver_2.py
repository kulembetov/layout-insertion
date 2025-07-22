from rest_framework.views import APIView
from rest_framework.response import Response
import json

from figma_api.backend.settings import FIGMA_TOKEN
from figma_api.script.figma_service_ver_2 import FilterConfig, FilterMode, EnhancedFigmaExtractor


class APIReceiveJsonFromFigma(APIView):
    """Returns JSON."""

    def get(self, request, *args, **kwargs):
        """Get JSON."""

        headers = {'X-Figma-Token': f'{FIGMA_TOKEN}'}
        file_id = request.data['file_id']

        if request.data.get('filter'):
            filter_mode = request.data.get('filter').get('mode')
            filter_params = request.data.get('filter').get('params')

            if filter_mode == FilterMode.SPECIFIC_SLIDES.value:
                filter_config = FilterConfig(mode=FilterMode.SPECIFIC_SLIDES, target_slides=filter_params)
                extractor = EnhancedFigmaExtractor(file_id, headers, filter_config=filter_config)
                result = extractor.extract()

                with open("output.json", "w", encoding="utf-8") as outfile:
                    json.dump(result, outfile, ensure_ascii=False, indent=4)

                return Response(result)
            
            elif filter_mode == FilterMode.BY_TYPE.value:
                # Корректируем фильтрацию по блокам, а не контейнерам
                filter_config = FilterConfig(mode=FilterMode.SPECIFIC_BLOCKS, target_block_types=filter_params)
                extractor = EnhancedFigmaExtractor(file_id, headers, filter_config=filter_config)
                result = extractor.extract()

                with open("output.json", "w", encoding="utf-8") as outfile:
                    json.dump(result, outfile, ensure_ascii=False, indent=4)

                return Response(result)
        
        else:
            extractor = EnhancedFigmaExtractor(file_id, headers)
            result = extractor.extract()

        return Response(result)
