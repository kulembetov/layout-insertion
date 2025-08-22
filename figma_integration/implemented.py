from configuration import figma_settings
from figma_integration.base import FigmaSession
from figma_integration.figma_extractor import FigmaExtractor
from figma_integration.figma_integrator import FigmaToSQLIntegrator

figma_session = FigmaSession(token=figma_settings.FIGMA_TOKEN)
figma_filter_session = FigmaSession(token=figma_settings.FIGMA_TOKEN)

figma_api = FigmaExtractor(figma_session)
figma_filter_api = FigmaToSQLIntegrator(figma_filter_session)
