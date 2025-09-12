"""
A handler class for accessing an Adobe Lightroom catalog (SQLite database).
"""
from __future__ import annotations
import argparse
import loguru
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from tabulate import tabulate
from typing import Generator, Tuple, Any
from lrxml_extractor import LrXmlExtractor

logger = loguru.logger

@dataclass
class LrCatImage:
    """
    A dataclass for storing information about an image in a Lightroom catalog.
    """
    id: int
    path: str
    name: str
    ext: str
    timestamp: int
    width: int
    height: int
    aspect: float
    caption: str
    keywords: list[str]


class LrCatKeyword:
    """
    A dataclass for storing information about a keyword in a Lightroom catalog.
    A keyword can be created by providing either a name or an ID.
    """
    def __init__(self, lrcat: LrCatDatabase, name: str = None, id: int = None):
        self.lrcat = lrcat

        if not name and not id:
            raise ValueError("Either a keyword name or ID must be provided.")
        elif id and not name:
            self.id = id
            self.name = self._get_name()
        elif name and not id:
            self.name = name
            self.id = self._get_id()
        else:
            self.name = name
            self.id = id

        self.parent_id = None
        self.includeOnExport = None
        self.includeParents = None
        self.includeSynonyms = None
        self._get_keyword_data()

        if self.parent_id and self.parent_id != 'None':
            self.path = "/".join(list(self._get_keyword_path()))
        else:
            self.path = "/"

    def __repr__(self):
        return f"LrCatKeyword({self.name})"

    def __str__(self):
        return self.path

    def __to_dict__(self):
        return {
            "id": self.id,
            "name": self.name,
            "parent_id": self.parent_id,
            "includeOnExport": self.includeOnExport,
            "includeParents": self.includeParents,
            "includeSynonyms": self.includeSynonyms,
            "path": self.path
        }

    def _get_id(self) -> int:
        """
        Returns the id of the keyword.
        """
        query = f"""
        SELECT AgLibraryKeyword.id_local
        FROM AgLibraryKeyword
        WHERE AgLibraryKeyword.name = '{self.name}'
        """
        row = self.lrcat._oneshot(query)
        return row[0]

    def _get_name(self) -> str:
        """
        Returns the name of the keyword.
        """
        query = f"""
        SELECT AgLibraryKeyword.name
        FROM AgLibraryKeyword
        WHERE AgLibraryKeyword.id_local = {self.id}
        """
        row = self.lrcat._oneshot(query)
        return row[0]

    def _get_keyword_data(self) -> None:
        """
        Queries the AgLibraryKeyword table to update the keyword data.
        """
        query = f"""
        SELECT
            AgLibraryKeyword.name,
            AgLibraryKeyword.parent,
            AgLibraryKeyword.includeOnExport,
            AgLibraryKeyword.includeParents,
            AgLibraryKeyword.includeSynonyms
        FROM AgLibraryKeyword
        WHERE AgLibraryKeyword.id_local={self.id}
        """
        row = self.lrcat._oneshot(query)
        if row:
            self.name, self.parent_id, self.includeOnExport, self.includeParents, self.includeSynonyms = row
        else:
            logger.warning(f"No data found for keyword id {self.id} ({self.name})")

    def _get_keyword_path(self) -> list[str]:
        """
        Returns the hierarchical structure of a keyword by using the
        AgLibraryKeyword table recursively until the parent name is None.
        """
        parent = LrCatKeyword(self.lrcat, id=self.parent_id)
        if parent.parent_id is None:
            return [self.name.lower()]
        return [parent.path, self.name]


class LrCatAlbum:
    """
    A collection of images in a Lightroom catalog. This has been named "album"
    to avoid confusion with the Lightroom concept of "collections".
    """
    def __init__(self):
        self.backup = []
        self.images = []
        self.count = 0

    def __repr__(self):
        return f"LrCatAlbum({self.count} images)"

    def add_image(self, image: LrCatImage) -> None:
        self.backup = self.images
        self.images.append(image)
        self.count += 1

    def remove_image(self, image: LrCatImage) -> None:
        self.backup = self.images
        self.images.remove(image)
        self.count -= 1

    def remove_by_keyword(self, keyword: str) -> None:
        """
        Removes all images with a given keyword from the album.
        """
        self.backup = self.images
        # Keep all the images that DON'T have the keyword
        self.images = [image for image in self.backup if keyword not in image.keywords]
        self.count = len(self.images)

    def filter_by_keyword(self, keyword: str) -> None:
        """
        Removes all images without a given keyword from the album.
        """
        self.backup = self.images
        # Keep all the iamges that DO have the keyword
        self.images = [image for image in self.images if keyword in image.keywords]
        self.count = len(self.images)

    def get_images_by_keyword(self, keyword: str) -> Generator[LrCatImage]:
        """
        Generator that yields images with a given keyword.
        """
        for image in self.images:
            if keyword in image.keywords:
                yield image

    def undo(self):
        """
        Restores the album to its previous state.
        """
        self.images = self.backup
        self.count = len(self.images)

    @property
    def keywords(self) -> set[str]:
        """
        Returns a set of all keywords in the album.
        """
        return set([keyword for image in self.images for keyword in image.keywords])


class LrCatDatabase:
    """
    A SQLite database handler for Adobe Lightroom catalogs.
    """
    # Define table headers as they appear in PRAGMA table_info output
    SQLITE_TABLE_METADATA = ["cid", "name", "type", "notnull", "dflt_value", "pk"]

    def __init__(self, catalog_path: str):
        self.conn = None

        # Check that catalog_path is not None
        if not catalog_path:
            raise ValueError("No catalog path provided.")
        # Check that catalog_path is a valid file
        if not Path(catalog_path).is_file():
            raise FileNotFoundError(f"File not found: {catalog_path}")
        self.catalog_path = catalog_path

        self.conn = sqlite3.connect(catalog_path)
        self.cursor = self.conn.cursor()

        self.library = LrCatAlbum()
        for image in self.get_images():
            self.library.add_image(image)

    def __del__(self):
        if self.conn:
            self.conn.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.conn.close()

    def __repr__(self):
        return f"LrCatDatabase({self.catalog_path})"

    ############################################################################
    # Helper functions for executing database queries
    #region

    def _exec(self, query: str) -> Generator[Tuple[Any, ...], None, None]:
        """
        Executes a query on the Lightroom catalog.

        Parameters:
        - query: The query to execute.

        Returns:
        A generator that yields rows from the query result.
        """
        self.cursor.execute(query)
        rows = self.cursor.fetchall()
        for row in rows:
            yield row

    def _oneshot(self, query: str) -> list[Tuple[Any, ...], None, None]:
        """
        Executes a query on the Lightroom catalog.

        Parameters:
        - query: The query to execute.

        Returns:
        A generator that yields rows from the query result.
        """
        try:
            return next(self._exec(query))
        except StopIteration:
            return None

    #endregion
    ############################################################################

    ############################################################################
    # The following methods are intended ONLY for interactive (CLI) use.
    #region

    def cli_query(self, query: str):
        """
        Executes a query on the Lightroom catalog. This method is intended for
        interactive use, as it prints the results to the console. For any other
        (programmatic) use, use the exec() method instead.

        Parameters:
        - query: The query to execute.

        Returns:
        A tabulated representation of the query result.
        """
        self.cursor.execute(query)
        headers = [desc[0] for desc in self.cursor.description]
        data = self.cursor.fetchall()
        print(tabulate(data, headers=headers, tablefmt="pretty"))

    def cli_table_list(self):
        """
        Prints a list of tables in the Lightroom catalog.
        """
        self.cursor.execute("PRAGMA table_list")
        table_info = self.cursor.fetchall()
        print(tabulate(table_info, headers=self.SQLITE_TABLE_METADATA, tablefmt="pretty"))

    def cli_table_info(self, table_name: str):
        """
        Prints metadata about a table in the Lightroom catalog.
        """
        self.cursor.execute(f"PRAGMA table_info({table_name})")
        table_info = self.cursor.fetchall()
        print(tabulate(table_info, headers=self.SQLITE_TABLE_METADATA, tablefmt="pretty"))

    #endregion
    ############################################################################

    ############################################################################
    # Image metadata extraction
    # region

    def _extract_caption(self, metadata: dict) -> str:
        """
        Extracts the caption from the metadata.
        """
        return metadata.get('dc:description', '')

    def _extract_keywords(self, metadata: dict, normalize: bool = True) -> list[LrCatKeyword]:
        """
        Takes the metadata dictionary and extracts the keywords.
        """
        keywords = metadata.get('dc:subject', [])
        kw_paths = [str(LrCatKeyword(self, name=keyword)) for keyword in keywords]
        if not normalize:
            return kw_paths
        # Remove any keywords that are wholly part of another keyword
        kw_copy = kw_paths.copy()
        for kw_path in kw_copy:
            for other_kw_path in kw_copy:
                if kw_path != other_kw_path and kw_path in other_kw_path:
                    try:
                        kw_paths.remove(kw_path)
                    except ValueError:
                        pass
        # return the sorted list of keywords
        return sorted(kw_paths)

    def get_metadata(self, image_id: int) -> dict:
        """
        The metadata is stored as comperessed binary data in the
        Adobe_AdditionalMetadata table. We need to query that table using the
        image_id and then decompress the `xmp` field.

        Parameters:
        - image_id: The ID of the image in the Adobe_images table.

        Returns:
        A dictionary of metadata for the image.
        """
        query = f"""
        SELECT xmp
        FROM Adobe_AdditionalMetadata
        WHERE image = {image_id}
        """
        row = self._oneshot(query)
        if not row:
            logger.warning(f"No metadata found for image ID {image_id}")
            return None

        parser = LrXmlExtractor()
        parser.load_xml(binary=row[0])
        return parser.extract()

    #endregion
    ############################################################################

    def get_images(self, *, id: int = None, name: str = None) -> Generator[LrCatImage, None, None]:
        """
        Generator that yields information about images in the Lightroom catalog.
        """
        query = """
        SELECT
            Adobe_images.id_local,
            AgLibraryRootFolder.absolutePath,
            AgLibraryFolder.pathFromRoot,
            AgLibraryFile.baseName,
            AgLibraryFile.extension,
            Adobe_images.captureTime,
            Adobe_images.fileWidth,
            Adobe_images.fileHeight
        FROM Adobe_images
        JOIN AgLibraryFile
            ON Adobe_images.rootFile = AgLibraryFile.id_local
        JOIN AgLibraryFolder
            ON AgLibraryFolder.id_local=AgLibraryFile.folder
        JOIN AgLibraryRootFolder
            ON AgLibraryRootFolder.id_local=AgLibraryFolder.rootFolder
        """
        if id:
            query += f"WHERE Adobe_images.id_local = {id}"
        elif name:
            query += f"WHERE AgLibraryFile.baseName LIKE '%{name}%'"

        for row in self._exec(query):
            metadata = self.get_metadata(row[0])
            yield LrCatImage(
                id=row[0],
                path=f"{row[1]}{row[2]}{row[3]}.{row[4]}",
                name=row[3],
                ext=row[4],
                timestamp=row[5] if row[5] != "None" else 0,
                width=row[6],
                height=row[7],
                aspect=round((float(row[6]) / float(row[7])), 2) if float(row[7]) > 0 else 0,
                caption=self._extract_caption(metadata) if metadata else "",
                keywords=self._extract_keywords(metadata) if metadata else []
            )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Query an Adobe Lightroom catalog")
    parser.add_argument("lrcat_path", help="The path to the Lightroom catalog")
    args = parser.parse_args()

    lrcat_path = args.lrcat_path.replace("\\", "/")
    with LrCatDatabase(lrcat_path) as lrcat:
        print(lrcat)

        query = "dummy"
        while query != "":
            query = input("Enter a query (or press Enter to quit): ")
            try:
                max_rows = input("Enter the maximum number of rows to display (Enter for no limit): ")
                if max_rows:
                    query += f" LIMIT {int(max_rows)}"
            except ValueError:
                logger.error("Invalid input. Please enter a number.")
                continue
            logger.debug(query)
            lrcat.db_query(query)