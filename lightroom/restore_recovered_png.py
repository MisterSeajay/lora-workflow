"""
A script that will restore an image file that has been recovered after
accidental deletion. The script will attempt to extract Adobe Lightroom metadata
from the file and perform the following:

1. Rename the file to its original name.
2. Find the file in the Adobe Lightroom catalog.
3. Move the file to the original folder, checking for duplicates.
"""

import argparse
import glob
import os

from loguru import logger
from lrcat_helper import LrCatDatabase
from lrxml_extractor import LrXmlExtractor
from png_extractor import PNGExtractor


def get_original_name_and_id(chunks) -> tuple[str | None, str | None]:
    """
    Get the original file and Adobe file id from the iTxt metadata, which will
    be found within the iTXt chunk. That chunk will contain XML data where the
    necessary information is stored under the rdf:Description tag as per the
    following examples:

        xmpMM:PreservedFileName="00307-264008552-2.png"
        xmpMM:OriginalDocumentID="F9C90BAA5EBB8E1DD96F96B6FE090B5D"

    Parameters:
    - chunks: The text chunks extracted from the PNG file.

    Returns:
    - A tuple containing the original file name and the Adobe file ID.
    """
    # Extract the iTXt chunk data
    itxt_data = chunks.get("iTXt", None)
    if not itxt_data:
        logger.warning("No iTXt chunk found")
        return None, None

    # Extract the XML data from the iTXt chunk
    xml_data = itxt_data.data
    if not xml_data:
        logger.warning("No data found in iTXt chunk")
        return None, None

    # Parse the XML data to extract the original file name and Adobe file ID
    xml_extractor = LrXmlExtractor()
    xml_extractor.load_xml(xml=xml_data)
    try:
        metadata = xml_extractor.extract()
    except Exception as e:
        logger.error(f"Error extracting metadata: {e}")
        logger.debug(f"Raw iTxt data: {itxt_data.keyword}:\n{itxt_data.data}")
        logger.debug(f"Cleaned XML data: {xml_extractor.xml_data}")
        return None, None

    original_name = metadata.get("xmpMM:PreservedFileName", None)
    file_id = metadata.get("xmpMM:OriginalDocumentID", None)

    return original_name, file_id


def main(source, catalog, whatif: bool = False):
    """
    Main function to handle argument parsing and processing of files.
    """
    # Check the Lightroom catalog file exists
    try:
        lrcat = LrCatDatabase(catalog_path=catalog)
    except FileNotFoundError:
        logger.error(f"Lightroom catalog file found: {catalog}")
        return
    except Exception:
        logger.exception("Error initializing Lightroom catalog")
        return

    # if source contains a wildcard we need to expand it to get a list of files
    if "*" in source:
        source = glob.glob(source)
        if not source:
            logger.error(f"No files found matching {source}")
            return
    else:
        source = [source]

    lrcat = LrCatDatabase(catalog_path=catalog)

    for png_file in source:
        if not png_file.endswith(".png"):
            continue

        chunks = PNGExtractor(png_file).chunks
        if not chunks:
            logger.warning(f"No text chunks found in {png_file}.")
            continue

        # Extract the original file name and Adobe file ID from the chunk data
        original_name, file_id = get_original_name_and_id(chunks)
        if not original_name:
            logger.error(f"Original file name NOT found in the metadata for {png_file}")
            continue

        base_name, extension = original_name.split(".")

        # Find the file in the Lightroom catalog
        original_path = [
            i.path
            for i in lrcat.all.images
            if i.name == base_name and i.ext == extension
        ]
        if not file_id:
            logger.warning(f"File {original_name} not found in the Lightroom catalog.")
            continue
        if len(original_path) > 1:
            logger.warning(
                f"Multiple files found with the name {base_name}{extension}."
            )
            continue

        original_path = original_path[0]

        # If source is a short or relative filename, we need to get the full path
        if not os.path.isabs(png_file):
            png_file = os.path.abspath(png_file)

        # Create the original folder if it does not exist
        original_folder = os.path.dirname(original_path)
        if not os.path.exists(original_folder):
            os.makedirs(original_folder)

        # Move the file to the original folder
        if not whatif:
            try:
                os.rename(png_file, original_path)
            except Exception as e:
                logger.error(f"Error moving file: {e}")
                return
        else:
            logger.info(f"WHATIF: move file to {original_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Restore a recovered image file")
    parser.add_argument("--source", help="The full path of the recovered image file")
    parser.add_argument("--catalog", help="The full path of the Lightroom catalog file")
    parser.add_argument(
        "--whatif",
        help="Switch to perform a dry run without moving the file",
        action="store_true",
    )
    args = parser.parse_args()
    main(args.source, args.catalog, args.whatif)
