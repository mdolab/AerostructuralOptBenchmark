"""
==============================================================================
Wingbox iges generator
==============================================================================
@File    :   generateWingboxGeometry.py
@Date    :   2023/12/21
@Author  :   Alasdair Christison Gray
@Description :
"""

# ==============================================================================
# Standard Python modules
# ==============================================================================
import sys

# ==============================================================================
# External Python modules
# ==============================================================================
import numpy as np
from pygeo import pyGeo, geo_utils
from pyspline import Curve
from pylayout import pyLayoutGeo

# ==============================================================================
# Extension modules
# ==============================================================================
sys.path.append("../geometry")
from wingGeometry import wingGeometry  # noqa: E402

# --- Get the wingbox leading and trailing edge definitions from the geometry definition ---
spanIndex = wingGeometry["spanIndex"]
chordIndex = wingGeometry["chordIndex"]
verticalIndex = wingGeometry["verticalIndex"]
chords = wingGeometry["wing"]["sectionChord"]  # root and tip chords
sweep = [0, 7.5]  # root and tip sweep
semiSpan = wingGeometry["wing"]["semiSpan"]
sob = wingGeometry["wingbox"]["SOB"]  # span location of side-of-body
numRibs = wingGeometry["wingbox"]["numRibs"]  # number of columns (aligned with ribs)
numRibsCentrebody = wingGeometry["wingbox"]["numRibsCentrebody"]  # column index of side-of-body kink
LESparCoords = wingGeometry["wingbox"]["LESparCoords"]
TESparCoords = wingGeometry["wingbox"]["TESparCoords"]

# ==============================================================================
# Create pyLayoutGeo object
# ==============================================================================
surfFile = "../geometry/wing.igs"
geo = pyGeo("iges", fileName=surfFile)
layoutGeo = pyLayoutGeo.LayoutGeo(geo, rightWing=True, prefix="WING")

layoutGeo.addDomain("z", offset=0)  # This is the plane to which curves are projected (I think)

resolution = 50

# ==============================================================================
# Spar definition
# ==============================================================================
# We need to convert the spar coordinates from 2d arrays to lists of 1d arrays so the pyLayoutGeo creates linear
# segments between them
layoutGeo.addComponent(
    "spar", [LESparCoords[ii] for ii in range(LESparCoords.shape[0])], tag="le_spar", resolution=resolution
)

layoutGeo.addComponent(
    "spar", [TESparCoords[ii] for ii in range(TESparCoords.shape[0])], tag="te_spar", resolution=resolution
)

# ==============================================================================
# Rib definitions
# ==============================================================================
ribDirection = np.zeros(3)
ribDirection[chordIndex] = 1
# The ribs are all aligned with the chordwise, we have numRibs of them in total, numRibsCentrebody of which are in the
# centrebody
inboardPts = geo_utils.linearEdge(LESparCoords[0], LESparCoords[1], numRibsCentrebody)

for ii in range(numRibsCentrebody):
    layoutGeo.addComponent(
        "rib",
        basePt=inboardPts[ii],
        direction=ribDirection,
        bidirectional=True,
        clipLower=["le_spar"],
        clipUpper=["te_spar"],
        resolution=resolution,
    )

outboardPts = geo_utils.linearEdge(LESparCoords[1], LESparCoords[2], 1 + numRibs - numRibsCentrebody)
for ii in range(1, outboardPts.shape[0]):
    layoutGeo.addComponent(
        "rib",
        basePt=outboardPts[ii],
        direction=ribDirection,
        bidirectional=True,
        clipLower=["le_spar"],
        clipUpper=["te_spar"],
        resolution=resolution,
    )

# ==============================================================================
# Skin definitions
# ==============================================================================
layoutGeo.addSkins(resolution=resolution)

# ==============================================================================
# Write output files
# ==============================================================================
layoutGeo.writeTinFile("wingbox.tin")
layoutGeo.writeIGESFile("wingbox.igs")
layoutGeo.writeOrigCurves("wingbox_orig_curves.dat")
