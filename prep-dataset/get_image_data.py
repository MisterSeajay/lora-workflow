import json
from pathlib import Path

import images
import lightroom
import typer
from loguru import logger

app = typer.Typer()


@app.command()
def main(image_path: str):
    """
    Gets Adobe Lightroom metadata from a PNG file.
    """
    # Ensure the path exists and is a PNG file
    if not Path(image_path).is_file():
        raise FileNotFoundError(f"File not found: {image_path}")

    if not image_path.lower().endswith(".png"):
        raise ValueError(f"Invalid file type: {image_path}")

    # Exctract XML from PNG file
    png_extractor = images.PNGExtractor(image_path)
    chunk_data = png_extractor.chunks.get("iTXt")
    if not chunk_data:
        raise ValueError("No iTXt chunk found")

    lr_extractor = lightroom.LrXmlExtractor()
    lr_extractor.load_xml(xml=chunk_data.data)
    print(json.dumps(lr_extractor.extract(), indent=4))


if __name__ == "__main__":
    # use typer
    try:
        app()
    except KeyboardInterrupt:
        print("Operation cancelled by user...")
    except Exception as e:
        logger.error(e)
