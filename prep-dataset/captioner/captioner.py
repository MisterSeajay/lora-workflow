"""
A Class that takes a dictionary of Adobe Lightroom export metadata and returns
a legible caption based on the keywords.
"""

import re

from loguru import logger


class Captioner:
    def __init__(self):
        self.keywords: list[str] = []
        self.location: str = ""

    @staticmethod
    def clean_caption(lines: list[str]) -> str:
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

    @staticmethod
    def extract_keywords_from_metadata(metadata: dict[str, list[str]]) -> list[str]:
        """
        Builds a summary of the Adobe Lightroom keywords from the metadata,
        using an ordered list (by preference of use) of keywords.
        """
        preferred_keywords = [
            "lr:hierarchicalSubject",
            "dc:subject",
        ]
        for key in preferred_keywords:
            if key in metadata:
                return metadata[key]
        return []

    @staticmethod
    def extract_location_from_metadata(metadata: dict[str, list[str]]) -> str:
        """
        Extracts the 'Iptc4xmpCore:Location' key from the metadata.
        """
        return str(metadata.get("Iptc4xmpCore:Location", ""))

    def load_metadata(self, metadata: dict[str, list[str]]) -> None:
        self.keywords = self.extract_keywords_from_metadata(metadata)
        self.location = self.extract_location_from_metadata(metadata)

    def _parse_keyword(self, keyword: str) -> str:
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

    def generate_caption(self, subject: str, include_appearance: bool) -> str:
        """
        Generates a caption for the image using the metadata. To create a caption we
        will use _extract_keywords() as well as the 'Iptc4xmpCore:Location' key
        from the metadata.

        We will try to turn the keywords and location into something that resembles
        a sentence. The keywords should have prefixes that help with the conversion.

        """
        style: list[str] = []
        parsed: list[str] = []

        for keyword in self.keywords:
            if not include_appearance:
                if (
                    keyword.split("|")[0] == "3. appearance"
                    and not keyword.split("|")[1] == "expression"
                ):
                    continue
            if keyword.split("|")[0] == "1. style":
                style.append(self._parse_keyword(keyword))
            else:
                parsed.append(self._parse_keyword(keyword))

        # clean up and join into one string
        caption = self.clean_caption(list(set(style)) + parsed)

        # if the #LOCATION# placeholder is present in the caption, replace it
        # with the actual Iptc4xmpCore location
        location = self.location if self.location else ""
        caption: str = caption.replace("#LOCATION#", location)

        return f"{subject}, {caption}"
