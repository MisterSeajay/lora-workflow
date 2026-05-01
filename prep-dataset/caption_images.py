"""
An app that takes one or more PNG files as input, extracts metadata from their
text-based chunks, unwraps the relevant data (keywords) from Adobe Lightroom XML
and builds them into a caption for the image.
"""

import argparse
import glob
import os
import sys
from typing import Any

import typer
from captioner import Captioner
from images import PNGExtractor
from lightroom import LrXmlExtractor
from loguru import logger

app = typer.Typer()


def configure_logging(args: argparse.Namespace) -> None:
    # Set a global WHATIF variable to control the behavior of the script
    global WHATIF
    WHATIF = args.whatif

    ## Clear existing loggers to reconfigure
    logger.remove()

    # Define new custom log levels
    VERBOSE_LEVEL = 15  # between INFO and DEBUG
    WHATIF_LEVEL = 55  # highest level; if you ask for it, you _always_ get it!

    # Add new custom log levels to logger
    logger.level("VERBOSE", no=VERBOSE_LEVEL, color="<cyan>")
    logger.level("WHATIF", no=WHATIF_LEVEL, color="<yellow>")

    # Set the log level based on the debug flag
    log_level = "DEBUG" if args.debug else "VERBOSE"
    logger.add(sys.stderr, level=log_level)


def extract_metadata_from_png(png_file: str, chunk_type: str) -> dict[str, Any] | None:
    """
    Extracts iTXt data from a PNG file using PNGExtractor then processes this
    with the LrXmlExtractor to get clean metadata.
    """
    logger.log("VERBOSE", f"Extracting metadata from {png_file}")

    png_extractor = PNGExtractor(png_file, chunk_type)
    try:
        chunk_data = png_extractor.chunks.get(chunk_type)
    except Exception as e:
        logger.error(f"Error extracting metadata from {png_file}: {e}")
        chunk_data = None

    if not chunk_data:
        logger.warning("No iTXt chunk found")
        return None
    if not chunk_data.data:
        logger.warning("No data found in iTXt chunk")
        logger.debug(chunk_data)
        return None

    lr_extractor = LrXmlExtractor()
    lr_extractor.load_xml(xml=chunk_data.data)
    metadata = lr_extractor.extract()
    return metadata


@app.command()
def main(
    source: str, subject: str, include_appearance: bool = True, chunk_type: str = "iTXt"
):
    """
    Main function to handle argument parsing and processing of files.
    """
    png_files = glob.glob(source)
    if not png_files:
        logger.error("No PNG files found")
        return

    # Delete all matching .txt files in this folder
    to_delete = source.replace(".png", ".txt")
    for file in glob.glob(to_delete):
        if WHATIF:
            logger.log("WHATIF", f"Delete file: {file}")
        else:
            os.remove(file)

    # Initialize the captioner
    captioner = Captioner()

    for png_file in png_files:
        metadata = extract_metadata_from_png(png_file, chunk_type)
        if not metadata:
            logger.warning(f"No metadata data found in {png_file}")
            continue

        captioner.load_metadata(metadata)

        caption = captioner.generate_caption(subject, include_appearance)
        caption_file = png_file.replace(".png", ".txt")
        if WHATIF:
            # simply output the metadata found in the PNG file
            logger.debug(f"{png_file}:\n{metadata['lr:hierarchicalSubject']}")
            logger.log("WHATIF", f"Write caption to {caption_file}")
        else:
            # write the caption to a file. The file will have the same name as
            # the PNG file, but with a .txt extension
            with open(caption_file, "w") as f:
                f.write(caption)
        logger.info(f"{caption_file}:\n{caption}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Extract metadata from PNG files and build captions"
    )
    # "project" is a mandatory command line parameter:
    parser.add_argument(
        "project",
        help="The main subject of the image (will be prefixed in the caption)",
    )
    parser.add_argument(
        "--source",
        required=True,
        help="The path to the PNG file(s), supports wildcards",
    )
    parser.add_argument(
        "--include-appearance",
        default=False,
        action="store_true",
        help="Switch to include appearance/description in the caption.",
    )
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument(
        "--whatif",
        action="store_true",
        help="Runs script without making changes to files",
    )
    args = parser.parse_args()
    configure_logging(args)
    main(args.source, args.project, args.include_appearance)
