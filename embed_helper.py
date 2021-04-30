from enum import Enum


class Constants(Enum):
    EMPTY = '\u200b'  # A zero width character that can be used in replacement of an empty string
    SPACE = '\u00A0'  # A different method to add spaces, since discord treats multiple consecutive spaces as 1 space
    FIELD_VALUE_LIMIT = 1024  # Maximum number of characters allowed in a field's value
    FIELD_LIMIT = 25  # Maximum number of fields
