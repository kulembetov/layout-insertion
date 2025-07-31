from api_v1.services.figma_api import FigmaAPI
from api_v1.services.filters.filter_service import FilterFigmaApi
from config.settings import FIGMA_TOKEN

figma_instance = FigmaAPI(token=FIGMA_TOKEN)
filter_figma_instance = FilterFigmaApi(token=FIGMA_TOKEN)
