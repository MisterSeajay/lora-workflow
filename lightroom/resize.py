"""
A script that will resize all PNG images in a specific folder so that their
shortest size is a certain value, 512px by default.
"""

import argparse
import glob
import os

from loguru import logger
from PIL import Image
from tqdm import tqdm


def resize(file: str, size: int = 512) -> None:
    """
    Resizes an image to a fixed minimum size.
    Args:
        file (str): The path to the PNG file.
        size (int): The size of the minimum dimension of the image.
    """
    image = Image.open(file)
    width, height = image.size
    if width < height:
        new_width = size
        new_height = int(height * (size / width))
    else:
        new_width = int(width * (size / height))
        new_height = size
    image = image.resize((new_width, new_height))
    image.save(file)


def main(source: str, size: int = 512) -> None:
    """
    Gets all PNG files in the `source` path, which must be a directory.

    Loops through each of these, calling the resize() function to resize them.

    Args:
        source (str): The path to the PNG file(s).
        size (int): The size of the minimum dimension of the images.
    """
    # Check that source is a directory
    if not os.path.isdir(source):
        logger.error(f"{source} is not a directory")
        return

    files = glob.glob(f"{source}/*.png")
    if not files:
        logger.error("No PNG files found")
        return

    for file in tqdm(files):
        resize(file, size)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Resizes all images in a folder to a fixed minimum size."
    )
    parser.add_argument(
        "--source",
        required=True,
        type=str,
        help="The path to the directory containing the PNG files.",
    )
    parser.add_argument(
        "--size",
        default=512,
        type=int,
        help="The size of the minimum dimension of the images. Defaults to 512px",
    )
    args = parser.parse_args()

    main(args.source, args.size)
