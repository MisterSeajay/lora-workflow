"""
A helper for reading Lightroom XML data, especially image metadata.
"""

import xml.etree.ElementTree as ET
import zlib

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

    def _decompress_metadata(self, compressed_data: bytes) -> str:
        """
        Decompresses metadata stored in the Adobe_AdditionalMetadata table.
        """
        if compressed_data[:2] == b"\x78\x9c":
            xml_bytes = zlib.decompress(compressed_data)
        else:
            xml_bytes = zlib.decompress(compressed_data[4:])
        return xml_bytes.decode("utf-8")

    def clean_xml(self, xml: str | None = None) -> str:
        """
        Cleans up the XML string by removing unnecessary elements.
        """
        if not xml:
            if self.xml:
                xml = self.xml

        if not xml:
            raise ValueError("No XML data to clean.")

        cleaned = True
        while cleaned:
            cleaned = False

            # Remove any BOM if present
            if xml[0] == "\ufeff":
                xml = xml[1:]
                cleaned = True
                continue

            # Remove any leading null bytes
            if xml.startswith("\x00"):
                xml = xml[1:]
                cleaned = True
                continue

            # Remove <?xpacket ... ?> element from the start of the XML
            if xml.startswith("<?xpacket"):
                xml = xml[xml.find("?>") + 2 :].strip()
                cleaned = True
                continue

            # Remove <?xpacket ... ?> element from the end of the XML. It seems
            # that the raw XML sometimes has multiple (corrupt) xpacket elements
            # at the end, so we need to find the start of the first one and
            # remove everything after that.
            if xml.rfind("<?xpacket end") > 0:
                xml = xml[: xml.rfind("<?xpacket")].strip()
                cleaned = True
                continue

            xml = xml.strip()

        return xml

    def load_xml(self, *, xml: str | None = None, binary: bytes | None = None) -> None:
        """
        Loads the XML data into the object's self.xml attribute, as a string.
        """
        assert xml or binary, "Either XML or binary data must be provided."

        if binary:
            xml = self._decompress_metadata(binary)

        if not xml:
            raise ValueError("No XML data provided.")

        clean_xml = self.clean_xml(xml)
        if not clean_xml:
            raise ValueError("No XML data loaded after cleaning.")

        self.xml = clean_xml

    def _extract_alt_text(self, element: ET.Element, field: str) -> str:
        """
        Extracts the text from an Alt element.
        """
        alt_element = element.find(f"{field}/rdf:Alt/rdf:li", namespaces=NAMESPACES)
        if alt_element and alt_element.text:
            return alt_element.text
        else:
            return ""

    def _extract_bag_items(self, element: ET.Element, field: str) -> list:
        """
        Extracts the items from a Bag element.
        """
        items = []
        bag_element = element.find(f"{field}/rdf:Bag", namespaces=NAMESPACES)
        if bag_element is not None:
            items = [
                li.text for li in bag_element.findall("rdf:li", namespaces=NAMESPACES)
            ]
        return items

    def _extract_metadata(self, xml_tree: ET.Element) -> dict[str, str]:
        """
        Parse XMP metadata string into a dictionary.
        """
        metadata = {}
        description = xml_tree.find(".//rdf:Description", NAMESPACES)
        if description:
            metadata["xmpMM:DocumentID"] = description.get(
                f"{{{NAMESPACES['xmpMM']}}}DocumentID", None
            )
            metadata["xmpMM:PreservedFileName"] = description.get(
                f"{{{NAMESPACES['xmpMM']}}}PreservedFileName", None
            )
            metadata["xmpMM:OriginalDocumentID"] = description.get(
                f"{{{NAMESPACES['xmpMM']}}}OriginalDocumentID", None
            )
            metadata["xmpMM:InstanceID"] = description.get(
                f"{{{NAMESPACES['xmpMM']}}}InstanceID", None
            )
            metadata["dc:format"] = description.get(
                f"{{{NAMESPACES['dc']}}}format", None
            )
            metadata["xmpDM:pick"] = description.get(
                f"{{{NAMESPACES['xmpDM']}}}pick", None
            )
            metadata["xmp:MetadataDate"] = description.get(
                f"{{{NAMESPACES['xmp']}}}MetadataDate", None
            )
            metadata["xmp:Rating"] = description.get(
                f"{{{NAMESPACES['xmp']}}}Rating", None
            )
            metadata["xmp:CreatorTool"] = description.get(
                f"{{{NAMESPACES['xmp']}}}CreatorTool", None
            )
            metadata["xmp:ModifyDate"] = description.get(
                f"{{{NAMESPACES['xmp']}}}ModifyDate", None
            )
            metadata["Iptc4xmpCore:Location"] = description.get(
                f"{{{NAMESPACES['Iptc4xmpCore']}}}Location", None
            )
            metadata["exif:ExifVersion"] = description.get(
                f"{{{NAMESPACES['exif']}}}ExifVersion", None
            )
            metadata["tiff:XResolution"] = description.get(
                f"{{{NAMESPACES['tiff']}}}XResolution", None
            )
            metadata["tiff:YResolution"] = description.get(
                f"{{{NAMESPACES['tiff']}}}YResolution", None
            )
            metadata["tiff:ResolutionUnit"] = description.get(
                f"{{{NAMESPACES['tiff']}}}ResolutionUnit", None
            )

            metadata["dc:subject"] = self._extract_bag_items(
                description, f"{{{NAMESPACES['dc']}}}subject"
            )
            metadata["lr:weightedFlatSubject"] = self._extract_bag_items(
                description, f"{{{NAMESPACES['lr']}}}weightedFlatSubject"
            )
            metadata["lr:hierarchicalSubject"] = self._extract_bag_items(
                description, f"{{{NAMESPACES['lr']}}}hierarchicalSubject"
            )
            metadata["Iptc4xmpExt:PersonInImage"] = self._extract_bag_items(
                description, f"{{{NAMESPACES['Iptc4xmpExt']}}}PersonInImage"
            )

            region_list = description.find(
                ".//mwg-rs:RegionList/rdf:Bag", namespaces=NAMESPACES
            )
            regions = []
            if region_list is not None:
                for region in region_list.findall("rdf:li", namespaces=NAMESPACES):
                    region_desc = region.find("rdf:Description", namespaces=NAMESPACES)
                    if region_desc is not None:
                        region_data = {
                            "mwg-rs:Rotation": region_desc.get(
                                f"{{{NAMESPACES['mwg-rs']}}}Rotation", None
                            ),
                            "mwg-rs:Name": region_desc.get(
                                f"{{{NAMESPACES['mwg-rs']}}}Name", None
                            ),
                            "mwg-rs:Type": region_desc.get(
                                f"{{{NAMESPACES['mwg-rs']}}}Type", None
                            ),
                            "mwg-rs:Area": {
                                "stArea:h": region_desc.find(
                                    "mwg-rs:Area", namespaces=NAMESPACES
                                ).get(f"{{{NAMESPACES['stArea']}}}h", None),
                                "stArea:w": region_desc.find(
                                    "mwg-rs:Area", namespaces=NAMESPACES
                                ).get(f"{{{NAMESPACES['stArea']}}}w", None),
                                "stArea:x": region_desc.find(
                                    "mwg-rs:Area", namespaces=NAMESPACES
                                ).get(f"{{{NAMESPACES['stArea']}}}x", None),
                                "stArea:y": region_desc.find(
                                    "mwg-rs:Area", namespaces=NAMESPACES
                                ).get(f"{{{NAMESPACES['stArea']}}}y", None),
                            },
                        }
                        regions.append(region_data)
            metadata["mwg-rs:Regions"] = regions
        else:
            logger.warning("No description element found in XML data.")
            logger.debug(xml_tree)
        return metadata

    def extract(self) -> dict[str, str]:
        """
        Extracts metadata from the XML data into a dictionary.
        """
        if not self.xml:
            raise ValueError("No XML data loaded to extract.")

        tree = ET.fromstring(self.xml)

        rdf_data = tree.find(".//rdf:RDF", NAMESPACES)
        if rdf_data is None:
            logger.warning("No rdf_data element found in XML data.")
            logger.debug(tree)
            return {}

        metadata = self._extract_metadata(rdf_data)
        return metadata
