"""
A helper for reading Lightroom XML data, especially image metadata.
"""

import xml.etree.ElementTree as ET
import zlib
from typing import Any

from loguru import logger

NAMESPACES = {
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "x": "adobe:ns:meta/",
    "dc": "http://purl.org/dc/elements/1.1/",
    "lr": "http://ns.adobe.com/lightroom/1.0/",
    "mwg-rs": "http://www.metadataworkinggroup.com/schemas/regions/",
    "xmp": "http://ns.adobe.com/xap/1.0/",
    "tiff": "http://ns.adobe.com/tiff/1.0/",
    "exif": "http://ns.adobe.com/exif/1.0/",
    "xmpMM": "http://ns.adobe.com/xap/1.0/mm/",
    "xmpDM": "http://ns.adobe.com/xmp/1.0/DynamicMedia/",
    "stDim": "http://ns.adobe.com/xap/1.0/sType/Dimensions#",
    "stArea": "http://ns.adobe.com/xmp/sType/Area#",
    "Iptc4xmpCore": "http://iptc.org/std/Iptc4xmpCore/1.0/xmlns/",
    "Iptc4xmpExt": "http://iptc.org/std/Iptc4xmpExt/2008-02-29/",
}


class LrXmlExtractor:
    """
    A class that decompresses lightroom metadata and extracts information.
    """

    def __init__(self):
        self.xml = None

    ############################################################################
    # Methods to load data from raw XML

    def _decompress_metadata(self, compressed_data: bytes) -> str:
        if compressed_data[:2] == b"\x78\x9c":
            xml_bytes = zlib.decompress(compressed_data)
        else:
            xml_bytes = zlib.decompress(compressed_data[4:])
        return xml_bytes.decode("utf-8")

    def _clean_xml(self, xml: str | None = None) -> str:
        if not xml:
            xml = self.xml
        if not xml:
            raise ValueError("No XML data to clean.")

        cleaned = True
        while cleaned:
            cleaned = False
            if xml.startswith("\ufeff"):
                xml = xml[1:]
                cleaned = True
                continue
            if xml.startswith("\x00"):
                xml = xml[1:]
                cleaned = True
                continue
            if xml.startswith("<?xpacket"):
                xml = xml[xml.find("?>") + 2 :].strip()
                cleaned = True
                continue
            if xml.rfind("<?xpacket end") > 0:
                xml = xml[: xml.rfind("<?xpacket")].strip()
                cleaned = True
                continue
            xml = xml.strip()
        return xml

    def load_xml(self, *, xml: str | None = None, binary: bytes | None = None) -> None:
        assert xml or binary, "Either XML or binary data must be provided."
        if binary:
            xml = self._decompress_metadata(binary)
        if not xml:
            raise ValueError("No XML data provided.")

        c_xml = self._clean_xml(xml)
        if not c_xml:
            raise ValueError("No XML data loaded after cleaning.")
        self.xml = c_xml

    ############################################################################
    # Methods to export data from clean XML

    @staticmethod
    def _get_ns_attr(
        node: ET.Element | None, ns_key: str, attr_name: str, default: str = ""
    ) -> str:
        if node is None:
            return default
        full_name = f"{{{NAMESPACES[ns_key]}}}{attr_name}"
        return node.get(full_name, default)

    def _extract_bag_items(
        self, element: ET.Element, ns_key: str, tag: str
    ) -> list[str]:
        path = f"{{{NAMESPACES[ns_key]}}}{tag}/rdf:Bag"
        bag_element = element.find(path, namespaces=NAMESPACES)
        if bag_element is None:
            return []
        return [
            li.text.strip()
            for li in bag_element.findall("rdf:li", namespaces=NAMESPACES)
            if li.text
        ]

    def extract(self) -> dict[str, Any]:
        if not self.xml:
            raise ValueError("No XML loaded.")

        tree = ET.fromstring(self.xml)
        rdf = tree.find(".//rdf:RDF", NAMESPACES)
        if rdf is None:
            return {}

        data = self.extract_metadata(rdf)
        try:
            data["regions"] = self.get_regions(rdf)
        except ValueError:
            data["regions"] = []

        return data

    def extract_alt_text(self, element: ET.Element, ns_key: str, tag: str) -> str:
        path = f"{{{NAMESPACES[ns_key]}}}{tag}/rdf:Alt/rdf:li"
        alt_element = element.find(path, namespaces=NAMESPACES)
        return (
            alt_element.text.strip()
            if alt_element is not None and alt_element.text
            else ""
        )

    def extract_metadata(self, xml_tree: ET.Element) -> dict[str, Any]:
        description = xml_tree.find(".//rdf:Description", NAMESPACES)
        if description is None:
            logger.warning("No description element found.")
            return {}

        dims = self.get_dimensions(xml_tree)

        return {
            # Dimensions
            "width": dims["width"],
            "height": dims["height"],
            "tiff:ImageWidth": dims["width"],  # Keep for backward compatibility
            "tiff:ImageLength": dims["height"],
            # Adobe Media Management
            "xmpMM:DocumentID": self._get_ns_attr(description, "xmpMM", "DocumentID"),
            "xmpMM:InstanceID": self._get_ns_attr(description, "xmpMM", "InstanceID"),
            "xmpMM:OriginalDocumentID": self._get_ns_attr(
                description, "xmpMM", "OriginalDocumentID"
            ),
            "xmpMM:PreservedFileName": self._get_ns_attr(
                description, "xmpMM", "PreservedFileName"
            ),
            "xmpDM:pick": self._get_ns_attr(description, "xmpDM", "pick"),
            # Photo Metadata
            "xmp:MetadataDate": self._get_ns_attr(description, "xmp", "MetadataDate"),
            "xmp:Rating": self._get_ns_attr(description, "xmp", "Rating"),
            "xmp:CreatorTool": self._get_ns_attr(description, "xmp", "CreatorTool"),
            "xmp:ModifyDate": self._get_ns_attr(description, "xmp", "ModifyDate"),
            "exif:ExifVersion": self._get_ns_attr(description, "exif", "ExifVersion"),
            # Resolution
            "tiff:ResolutionUnit": self._get_ns_attr(
                description, "tiff", "ResolutionUnit"
            ),
            "tiff:XResolution": self._get_ns_attr(description, "tiff", "XResolution"),
            "tiff:YResolution": self._get_ns_attr(description, "tiff", "YResolution"),
            # Location & Format
            "Iptc4xmpCore:Location": self._get_ns_attr(
                description, "Iptc4xmpCore", "Location"
            ),
            "dc:format": self._get_ns_attr(description, "dc", "format"),
            # People & Keywords
            "Iptc4xmpExt:PersonInImage": self._extract_bag_items(
                description, "Iptc4xmpExt", "PersonInImage"
            ),
            "dc:subject": self._extract_bag_items(description, "dc", "subject"),
            "lr:weightedFlatSubject": self._extract_bag_items(
                description, "lr", "weightedFlatSubject"
            ),
            "lr:hierarchicalSubject": self._extract_bag_items(
                description, "lr", "hierarchicalSubject"
            ),
            # Captions
            "dc:title": self.extract_alt_text(description, "dc", "title"),
            "dc:description": self.extract_alt_text(description, "dc", "description"),
        }

    def get_dimensions(self, xml_tree: ET.Element) -> dict[str, str]:
        """
        Standalone logic to find image dimensions across EXIF, TIFF, and stDim.
        """
        desc = xml_tree.find(".//rdf:Description", NAMESPACES)
        if desc is None:
            return {"width": "", "height": ""}

        # 1. EXIF (Pixel Dimensions)
        w = self._get_ns_attr(desc, "exif", "PixelXDimension")
        h = self._get_ns_attr(desc, "exif", "PixelYDimension")

        # 2. TIFF Fallback
        if not w:
            w = self._get_ns_attr(desc, "tiff", "ImageWidth")
        if not h:
            h = self._get_ns_attr(desc, "tiff", "ImageLength")

        # 3. stDim Fallback (Adobe standard)
        if not w or not h:
            dim_node = desc.find("xmp:Dimensions", namespaces=NAMESPACES)
            if dim_node is not None:
                w = self._get_ns_attr(dim_node, "stDim", "w")
                h = self._get_ns_attr(dim_node, "stDim", "h")

        return {"width": w, "height": h}

    def get_regions(self, xml_tree: ET.Element) -> list[dict[str, Any]]:
        description = xml_tree.find(".//rdf:Description", NAMESPACES)
        if description is None:
            raise ValueError("No description element found.")

        region_list = description.find(".//mwg-rs:RegionList/rdf:Bag", NAMESPACES)
        if region_list is None:
            return []

        regions: list[dict[str, Any]] = []
        for region in region_list.findall("rdf:li", NAMESPACES):
            r_desc = region.find("rdf:Description", NAMESPACES)
            if r_desc is None:
                continue

            area = r_desc.find("mwg-rs:Area", NAMESPACES)
            this_region: dict[str, Any] = {
                "mwg-rs:Name": self._get_ns_attr(r_desc, "mwg-rs", "Name"),
                "mwg-rs:Type": self._get_ns_attr(r_desc, "mwg-rs", "Type"),
                "mwg-rs:Area": {
                    "stArea:h": float(self._get_ns_attr(area, "stArea", "h", "0")),
                    "stArea:w": float(self._get_ns_attr(area, "stArea", "w", "0")),
                    "stArea:x": float(self._get_ns_attr(area, "stArea", "x", "0")),
                    "stArea:y": float(self._get_ns_attr(area, "stArea", "y", "0")),
                },
            }
            regions.append(this_region)
        return regions
