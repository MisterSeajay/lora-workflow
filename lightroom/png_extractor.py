"""
Script to extract text chunks from a PNG file and write them to a text file or
copy them to another PNG file.
"""
import argparse
import struct
import zlib
from collections import namedtuple
from loguru import logger

# Define a named tuple to store the keyword and data of a text chunk
ChunkData = namedtuple("ChunkData", ("keyword", "data"))

class PNGExtractor:
    """
    Extracts text chunks from a PNG file. These are stored internally in a
    dictionary, whose keys are the type of text chunk(s) found in the PNG and
    the values are (keyword, data) pairs for each chunk type.
    """

    def __init__(self, png_path: str, chunk_type: str = None):
        self.png_path = png_path
        if chunk_type is None:
            self.chunk_types = [b"tEXt", b"zTXt", b"iTXt"]
        if isinstance(chunk_type, list):
            self.chunk_types = [c.encode() for c in chunk_type]
        if isinstance(chunk_type, str):
            self.chunk_types = [chunk_type.encode()]
        self.chunks = dict()
        self._get_png_chunks()

    @staticmethod
    def decode_chunk_data(chunk_type: bytes, data: bytes) -> ChunkData:
        """
        Decodes a text-based chunk from a PNG file.

        Takes a text-based chunk from a PNG file (as a stream of bytes) and converts
        this into a keyword-data pair (tuple).

        (Only) the iTXt, tEXt, and zTXt chunks are used for conveying textual
        information associated with the image.

        See: http://www.libpng.org/pub/png/spec/1.2/PNG-Chunks.html

        Parameters:
        - chunk_type: The type of chunk (e.g., "tEXt", "iTXt").
        - data: The data of the chunk (as a stream of bytes).
        """
        try:
            if chunk_type == b"tEXt":
                # The tEXt chunk just contains a keyword and text data separated by a
                # null byte:
                keyword, text = data.split(b"\x00", 1)
            elif chunk_type == b"zTXt":
                # The zTXt chunk contains a keyword, then a null byte, a single-byte
                # for the compression method then the rest of the compressed text.
                #
                # So we split() at the first null byte, to get the keyword and the
                # rest of the data; we extract the compression method as the first
                # character of the "rest" of the data. Depending on whether the data
                # has been compressed, we decompress it using zlib.
                keyword, rest = data.split(b"\x00", 1)
                compression_method = rest[0]
                compressed_text = rest[1:]
                if compression_method == 0:
                    text = zlib.decompress(compressed_text)
                else:
                    raise ValueError("Unsupported compression method.")
            elif chunk_type == b"iTXt":
                # iTxt data is more complex. It contains a keyword, then a null byte,
                # then a compression flag (1 byte), a compression method (1 byte)... and
                # so on. See the link above!

                parts = data.split(b"\x00", 2)
                keyword, compression_flag, rest = parts[0], parts[1], parts[2]
                if compression_flag in (b'0', b''):
                    text = rest.split(b"\x00", 1)[1]
                else:
                    compression_method = rest[0]
                    compressed_text = rest[2:]
                    if compression_method == 0:
                        text = zlib.decompress(compressed_text)
                    else:
                        raise ValueError("Unsupported compression method.")
            else:
                raise ValueError(f"Unsupported chunk type: {chunk_type}")

            return ChunkData(keyword.decode('utf-8'), text.decode("utf-8"))
        except Exception as e:
            logger.error(f"Error decoding chunk {chunk_type.decode('utf-8')}: {e}")
            keyword = keyword if keyword else "unknown"
            return ChunkData(keyword, data)

    def _get_png_chunks(self) -> None:
        """
        Extracts text data from the text-based chunks in a PNG file.
        """
        self.chunks = {}

        with open(self.png_path, "rb") as f:
            f.seek(8)  # Skip the PNG signature

            while True:
                chunk_length, chunk_type = self._get_chunk_meta(f)
                if chunk_length is None:
                    break

                if chunk_type in self.chunk_types:
                    logger.debug(f"{chunk_type.decode('utf-8')} chunk found ({chunk_length} bytes)")
                    chunk_data = f.read(chunk_length)
                    decoded_data = self.decode_chunk_data(chunk_type, chunk_data)
                    self.chunks[chunk_type.decode("utf-8")] = decoded_data
                    f.seek(4, 1)  # Skip CRC
                else:
                    f.seek(chunk_length + 4, 1)  # Skip chunk data and CRC

    def _get_chunk_meta(self, f) -> tuple[int, bytes]:
        """
        Reads the length and type of a chunk from a PNG file.
        """
        length_bytes = f.read(4)
        if not length_bytes:
            return None, None

        chunk_length = struct.unpack("!I", length_bytes)[0]
        chunk_type = f.read(4)

        return chunk_length, chunk_type


def main(source: str) -> None:
    """
    Main function.
    """
    chunks = PNGExtractor(source).chunks
    if not chunks:
        print(f"No text chunks found in {source}.")
        return
    for chunk_type, chunk_data in chunks.items():
        print(f"## {chunk_type}: {chunk_data.keyword}", "#"*20)
        print(chunk_data.data)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Get text chunks from a PNG file")
    parser.add_argument("--source", help="The full path of the PNG to read from")
    args = parser.parse_args()
    main(**vars(args))