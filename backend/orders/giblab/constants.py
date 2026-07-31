"""Constants for the GibLab `.project` import pipeline.

Kept in one place so version support, safety limits and the XML vocabulary
never get scattered across parser/validator/mapper.
"""

SOURCE_SYSTEM = "giblab"

# The only GibLab export version this pipeline has been verified against
# (the real sample file). Unknown newer/older versions are rejected with
# UNSUPPORTED_GIBLAB_VERSION rather than parsed on a guess -- extend this
# set (and, if the structure actually changed, add a version adapter) once
# a new sample is available.
SUPPORTED_VERSIONS = {"23051701"}

MAX_PROJECT_FILE_SIZE = 25 * 1024 * 1024  # 25 MB, generous vs. the ~100KB sample
MAX_ZIP_UNCOMPRESSED_SIZE = 100 * 1024 * 1024  # zip-bomb guard
MAX_ZIP_COMPRESSION_RATIO = 100  # zip-bomb guard
MAX_ZIP_MEMBER_COUNT = 50

GOOD_TYPE_PRODUCT = "product"
GOOD_TYPE_SHEET = "sheet"
GOOD_TYPE_BAND = "band"
GOOD_TYPE_TOOL_CUTTING = "tool.cutting"
GOOD_TYPE_TOOL_EDGELINE = "tool.edgeline"

OPERATION_TYPE_CS = "CS"
OPERATION_TYPE_EL = "EL"
OPERATION_TYPE_CL = "CL"
OPERATION_TYPE_XNC = "XNC"

# Edge attribute -> (side, source-material-name attribute)
EDGE_SIDE_ATTRS = {
    "elb": ("BOTTOM", "elbMat"),
    "ell": ("LEFT", "ellMat"),
    "elr": ("RIGHT", "elrMat"),
    "elt": ("TOP", "eltMat"),
}

# BOTTOM/TOP run along the part's length; LEFT/RIGHT along its width --
# confirmed against the sample.
EDGE_SIDE_USES_LENGTH = {"BOTTOM", "TOP"}
EDGE_SIDE_USES_WIDTH = {"LEFT", "RIGHT"}

MATERIAL_CATEGORY_PANEL = "panel"
MATERIAL_CATEGORY_EDGE_BAND = "edge_band"
MATERIAL_CATEGORY_LINEAR = "linear"
MATERIAL_CATEGORY_ACCESSORY = "accessory"
MATERIAL_CATEGORY_OTHER = "other"

BOM_ITEM_PART = "part"
BOM_ITEM_MATERIAL = "material"
BOM_ITEM_EDGE_BAND = "edge_band"

# Rounding tolerance (metres) when cross-checking a summed per-part edge
# net length against the EL operation's own declared `elLength` total.
EDGE_LENGTH_TOLERANCE_M = "0.5"
