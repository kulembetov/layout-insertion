import argparse

import configuration as config
from log_utils import setup_logger

from .base import FigmaSession
from .figma_integrator import FigmaToSQLIntegrator
from .utils.helper import HelpUtils

logger = setup_logger(__name__)


def main():
    """Main CLI entry point"""
    parser = create_argument_parser()
    args = parser.parse_args()

    # Validate and get credentials
    file_id, token = get_credentials(args)
    if not file_id or not token:
        print("Please provide --file-id and --token, or set FIGMA_FILE_ID and FIGMA_TOKEN in environment")
        exit(1)

    # Process based on mode
    process_request(args, file_id, token)


def create_argument_parser() -> argparse.ArgumentParser:
    """Create and configure argument parser"""
    parser = argparse.ArgumentParser(description="Figma to SQL Generator Integration (Config Compatible)")

    # Credentials
    parser.add_argument("--file-id", required=False, help="Figma file ID (optional if set in config.py)")
    parser.add_argument("--token", required=False, help="Figma API token (optional if set in config.py)")

    # Processing options
    parser.add_argument(
        "--mode",
        choices=["slides", "names", "statuses", "validate"],
        default="slides",
        help="Processing mode",
    )
    parser.add_argument("--slides", type=int, nargs="*", help="Slide group")
    parser.add_argument("--names", nargs="*", help="Slide names")
    parser.add_argument("--statuses", nargs="*", help="Slide statuses")
    parser.add_argument(
        "--output-dir",
        default=config.OUTPUT_CONFIG.output_dir,
        help="Output directory",
    )

    return parser


def get_credentials(args) -> tuple[str | None, str | None]:
    """Get Figma credentials from arguments or environment"""
    file_id = args.file_id or config.figma_settings.FIGMA_FILE_ID
    token = args.token or config.figma_settings.FIGMA_TOKEN
    return file_id, token


def process_request(args, file_id: str, token: str) -> None:
    """Process the request based on mode"""
    integrator = FigmaToSQLIntegrator(FigmaSession(file_id=file_id, token=token))

    if args.mode == "slides" and args.slides:
        process_slides(integrator, args.slides, args.output_dir)

    elif args.mode == "names" and args.names:
        process_names(integrator, args.names, args.output_dir)

    elif args.mode == "statuses":
        process_statuses(integrator, args.statuses, args.output_dir)

    elif args.mode == "validate":
        process_validation(integrator)

    else:
        show_usage_help()


def process_slides(integrator: FigmaToSQLIntegrator, slide_numbers: list[int], output_dir: str) -> None:
    """Process specific slides"""
    logger.info(f"Processing slide group: {slide_numbers}")
    integrator.generate_sql_for_slides(slide_numbers, output_dir)


def process_names(integrator: FigmaToSQLIntegrator, names: list[str], output_dir: str) -> None:
    """Process slides by their names"""
    logger.info(f"Processing slides by names: {names}")
    data = integrator.extract_slide_names(names)

    if data:
        sql_input = integrator.prepare_sql_generator_input(data)
        HelpUtils.create_directory_structure(output_dir, [])

        HelpUtils.json_dump({"slides": sql_input}, f"{output_dir}/names_config.json")
        logger.info(f"Processed {len(sql_input)} slides with specified names")


def process_statuses(integrator: FigmaToSQLIntegrator, statuses: list[str] | None, output_dir: str) -> None:
    """Process slides by status"""
    logger.info(f"Processing slides by status: {statuses or 'ready_to_dev'}")
    data = integrator.extract_status()

    if data:
        sql_input = integrator.prepare_sql_generator_input(data)
        HelpUtils.create_directory_structure(output_dir, [])

        HelpUtils.json_dump({"slides": sql_input}, f"{output_dir}/status_config.json")
        logger.info(f"Processed {len(sql_input)} slides with ready status")


def process_validation(integrator: FigmaToSQLIntegrator) -> None:
    """Process validation operations"""
    logger.info("Running font weight validation...")
    validation = integrator.validate_font_weights()

    logger.info("Validation Results:")

    if not isinstance(validation, dict):
        logger.info("   Error: Invalid validation data format")
        return

    total_blocks = validation.get("total_blocks", 0)
    slides_analyzed = validation.get("slides_analyzed", 0)
    weight_distribution = validation.get("weight_distribution", {})

    logger.info(f"   Total blocks analyzed: {total_blocks}")
    logger.info(f"   Slides analyzed: {slides_analyzed}")
    logger.info(f"   Font weight distribution: {weight_distribution}")

    invalid_weights = validation.get("invalid_weights_found", [])
    if isinstance(invalid_weights, list) and invalid_weights:
        logger.info(f"   Found {len(invalid_weights)} blocks with invalid font weights:")
        for item in invalid_weights[:5]:
            if isinstance(item, dict):
                slide = item.get("slide", "unknown")
                block = item.get("block", "unknown")
                weight = item.get("invalid_weight", "unknown")
                logger.info(f"     - Slide {slide}, Block: {block}, Weight: {weight}")
        if len(invalid_weights) > 5:
            logger.info(f"     ... and {len(invalid_weights) - 5} more")
    else:
        logger.info("   All font weights are valid!")


def show_usage_help() -> None:
    """Show usage help"""
    print("Please specify a valid mode and required parameters")
    print("Examples:")
    print("  python -m figma_integration.cli --file-id ID --token TOKEN --mode slides --slides 1 2 3")
    print("  python -m figma_integration.cli --file-id ID --token TOKEN --mode names --names hero infographics")
    print("  python -m figma_integration.cli --file-id ID --token TOKEN --mode statuses")
    print("  python -m figma_integration.cli --file-id ID --token TOKEN --mode validate")


if __name__ == "__main__":
    main()
