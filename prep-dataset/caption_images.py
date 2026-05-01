"""
An app that takes one or more PNG files as input, extracts metadata from their
text-based chunks, unwraps the relevant data (keywords) from Adobe Lightroom XML
and builds them into a caption for the image.
"""

import argparse
import glob
import os
import re
import sys

from lightroom.lrxml_extractor import LrXmlExtractor
from loguru import logger
from png_tools.png_extractor import PNGExtractor


def configure_logging(args: argparse.Namespace):
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


def extract_metadata_from_png(png_file: str, chunk_type: str):
    """
    Extracts iTXt data from a PNG file using PNGExtractor.
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
    return chunk_data.data


def parse_xml_metadata(xml_data: str) -> dict[str, str]:
    """
    Parses XML metadata using LrXmlExtractor.
    """
    lr_extractor = LrXmlExtractor()
    lr_extractor.load_xml(xml=xml_data)
    metadata = lr_extractor.extract()
    return metadata


def _extract_keywords(metadata: dict[str, list[str]]) -> list[str]:
    """
    Builds a summary of the Adobe Lightroom keywords from the metadata, using an
    ordered list (by preference of use) of keywords.
    """
    preferred_keywords = [
        "lr:hierarchicalSubject",
        "dc:subject",
    ]
    for key in preferred_keywords:
        if key in metadata:
            return metadata[key]
    return []


def _parse_keyword(keyword: str) -> str:
    """
    Parses a keyword into a sentence fragment.
    """

    def _noun(word: str) -> str:
        """
        Returns the word with the appropriate article (if singular).
        """
        if word.lower()[-1] == "s" and not word.lower()[-2] == "s":
            return word
        if word.lower()[-2:] == "ie":
            return word
        article = "an" if word[0].lower() in "aeiou" else "a"
        return f"{article} {word}"

    elements = keyword.split("|")
    if len(elements) == 1:
        # ignore if this keyword starts with a number
        if keyword[0].isdigit():
            return ""
        return keyword

    parsed = ""

    try:
        if elements[0] == "1. style":
            # return the elements in reverse order, excluding the first element
            parsed = " ".join(elements[1:][::-1])

        if elements[0] == "2. subject":
            if elements[1] in ("man", "woman"):
                parsed += "of a " + " ".join(elements[1:][::-1])
            else:
                parsed = "of " + elements[-1]

        if elements[0] == "3. position":
            if elements[1] in ("head", "pose"):
                parsed = " ".join(elements[2:])
            else:
                parsed = " ".join(elements[1:])

        if elements[0] == "4. appearance":
            if elements[1] == "nudity":
                if " " in elements[-1]:
                    parsed += elements[-1]
                else:
                    parsed += " ".join(elements[2:])
            else:
                parsed = " ".join(elements[1:][::-1])

        if elements[0] == "5. attire":
            if len(elements) == 2:
                parsed = f"{elements[-1]}"
            elif elements[2] == "outfit":
                parsed = "wearing a "
                parsed += " ".join(elements[3:][::-1])
                parsed += " outfit"
            elif elements[1] == "wearing":
                parsed = f"wearing {_noun(elements[-1])}"
            else:
                parsed = "with "
                # return the elements in reverse order, excluding the first two
                parsed += " ".join(elements[2:])

        if elements[0] == "6. location":
            if elements[1] == "featuring":
                parsed = f"{elements[1]} {_noun(elements[-1])}"
            else:
                parsed = f"taken {elements[-1]}, #LOCATION#"

    except IndexError:
        return ", ".join(elements[1:][::-1])

    if not parsed:
        logger.warning(f"Failed to parse: {keyword}")

    return parsed


def _clean_caption(lines: list[str]) -> str:
    """
    Cleans up the caption by removing any empty lines and trimming whitespace.
    """
    cleaned = [line.strip() for line in lines if line.strip()]
    # Reassemble into one line
    caption = ", ".join(cleaned)
    # Improve the grammar by replacing "a" with "an" before a vowel
    caption = re.sub(r"(^|\s+)a ([AEIOUaeiou])", r"\g<1>an \g<2>", caption)
    # Improve the grammar by removing commas before "and" or "of", etc.
    caption = re.sub(r",\s+(and|in|of)", r" \g<1>", caption)
    return caption


def generate_caption(
    subject: str, metadata: dict[str, list[str]], include_appearance: bool
) -> str:
    """
    Generates a caption for the image using the metadata. To create a caption we
    will use _extract_keywords() as well as the 'Iptc4xmpCore:Location' key
    from the metadata.

    We will try to turn the keywords and location into something that resembles
    a sentence. The keywords should have prefixes that help with the conversion.

    """
    keywords: list[str] = _extract_keywords(metadata)
    style: list[str] = []
    parsed: list[str] = []

    for keyword in keywords:
        if not include_appearance:
            if (
                keyword.split("|")[0] == "3. appearance"
                and not keyword.split("|")[1] == "expression"
            ):
                continue
        if keyword.split("|")[0] == "1. style":
            style.append(_parse_keyword(keyword))
        else:
            parsed.append(_parse_keyword(keyword))

    # clean up and join into one string
    caption = _clean_caption(list(set(style)) + parsed)

    # if the #LOCATION# placeholder is present in the caption, replace it with
    # the actual location
    location: str = metadata.get("Iptc4xmpCore:Location", "")
    location = location if location else ""
    caption: str = caption.replace("#LOCATION#", location)

    return f"{subject}, {caption}"


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

    for png_file in png_files:
        chunk_data = extract_metadata_from_png(png_file, chunk_type)
        if not chunk_data:
            logger.warning(f"No {chunk_type} data found in {png_file}")
            continue

        metadata = parse_xml_metadata(chunk_data)
        if metadata:
            caption = generate_caption(subject, metadata, include_appearance)
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
        else:
            logger.warning(f"No metadata found in {png_file}")
            continue


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
