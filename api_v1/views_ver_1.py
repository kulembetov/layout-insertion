from rest_framework.views import APIView
from rest_framework.response import Response
import json

from config.settings import FIGMA_TOKEN
from django_script.figma_service_ver_1 import FilterConfig, FilterMode, EnhancedFigmaExtractor


class APIReceiveJsonFromFigma(APIView):
    """Returns Json."""

    def get(self, request, *args, **kwargs):
        """Get Json."""

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
                filter_config = FilterConfig(mode=FilterMode.BY_TYPE, target_container_types=filter_params)
                extractor = EnhancedFigmaExtractor(file_id, headers, filter_config=filter_config)
                result = extractor.extract()

                with open("output.json", "w", encoding="utf-8") as outfile:
                    json.dump(result, outfile, ensure_ascii=False, indent=4)

                return Response(result)
        
        else:
            extractor = EnhancedFigmaExtractor(file_id, headers)
            result = extractor.extract()

            with open("output.json", "w", encoding="utf-8") as outfile:
                json.dump(result, outfile, ensure_ascii=False, indent=4)

            return Response(result[0:1000])





        

        # Экстрактор без фильтрации (режим ALL)
        # extractor = EnhancedFigmaExtractor(file_id, headers)
        # result = extractor.extract()
        # print(result)
        
        # Фильтрация по конкретным слайдам (режим SPECIFIC_SLIDES)
        # filter_config = FilterConfig(mode=FilterMode.SPECIFIC_SLIDES, target_slides=['1cols',])
        # extractor = EnhancedFigmaExtractor(file_id, headers, filter_config=filter_config)
        # result = extractor.extract()
        # print(result)

        # Фильтрация по типу контейнера (режим BY_TYPE)
        # filter_config = FilterConfig(mode=FilterMode.BY_TYPE, target_container_types=['FRAME','GROUP',])
        # extractor = EnhancedFigmaExtractor(file_id, headers, filter_config=filter_config)
        # result = extractor.extract()
        # print(result)

        return Response()
