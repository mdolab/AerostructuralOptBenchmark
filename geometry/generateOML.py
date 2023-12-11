"""
==============================================================================
OML Geometry generation
==============================================================================
@File    :   generateOML.py
@Date    :   2023/03/29
@Author  :   Alasdair Christison Gray
@Description : This file generates the surface geometry of the wing's OML and a series of fitted FFD's
"""

# ==============================================================================
# Standard Python modules
# ==============================================================================
import os
import argparse

# ==============================================================================
# External Python modules
# ==============================================================================
from pygeo import pyGeo
from pygeo.geo_utils import createFittedWingFFD
import numpy as np

# ==============================================================================
# Extension modules
# ==============================================================================
from wingGeometry import wingGeometry

parser = argparse.ArgumentParser()
parser.add_argument("--ffdType", type=str, choices=["basic", "advanced", "none"], default="basic")
args = parser.parse_args()

airfoilFiles = [
    os.path.join(os.path.dirname(os.path.abspath(__file__)), file) for file in wingGeometry["wing"]["sectionProfiles"]
]

# Airfoil rotations, this is a bit complicated because the wing we want to make is not in the orientation pyGeo expects
rot_x = [90.0, 90.0]
rot_y = wingGeometry["wing"]["sectionTwist"]
rot_z = [0.0, 0.0]

wingSurface = pyGeo(
    "liftingSurface",
    xsections=airfoilFiles,
    scale=wingGeometry["wing"]["sectionChord"],
    x=wingGeometry["wing"]["LECoords"][:, 0],
    y=wingGeometry["wing"]["LECoords"][:, 1],
    z=wingGeometry["wing"]["LECoords"][:, 2],
    rotX=rot_x,
    rotY=rot_y,
    rotZ=rot_z,
    # tip="pinched",
    bluntTe=True,
    squareTeTip=False,
    teHeight=wingGeometry["wing"]["teHeight"],
)

wingSurface.writeTecplot("wing.dat")
wingSurface.writeIGES("wing.igs")
wingSurface.writeTin("wing.tin")

if args.ffdType == "basic":
    # ==============================================================================
    # Generate fitted FFD
    # ==============================================================================
    numFFDSpan = [6, 9, 12]
    numFFDChord = [8, 12, 16]
    fileNames = ["wing-ffd-coarse.xyz", "wing-ffd-med.xyz", "wing-ffd-fine.xyz"]

    # --- We need to shift the LE and TE coordinate slightly inside the wing for the fitted FFD creation to work ---
    wingLEList = wingGeometry["wing"]["LECoords"]
    wingTEList = wingGeometry["wing"]["TECoords"]
    wingLEList += 0.01 * (wingTEList - wingLEList)
    wingTEList += 0.01 * (wingLEList - wingTEList)
    wingLEList[0, wingGeometry["spanIndex"]] += 1e-3
    wingTEList[0, wingGeometry["spanIndex"]] += 1e-3

    for nSpan, nChord, file in zip(numFFDSpan, numFFDChord, fileNames):
        createFittedWingFFD(
            wingSurface,
            surfFormat="point-vector",
            outFile=file,
            leList=wingLEList,
            teList=wingTEList,
            nSpan=nSpan,
            nChord=nChord,
            absMargins=[0.05, 0.005, 0.05],
            relMargins=[0.01, 0.005, 0.01],
            liftIndex=wingGeometry["verticalIndex"] + 1,
        )

elif args.ffdType == "advanced":
    # ==============================================================================
    # Fancier FFD
    # ==============================================================================
    # This is a more complex FFD that should allw me to stop the wing root and SOB moving in the spanwise direction

    # The first segment of the FFD will contain 3 sections around the root, purely to enforce that the wing root does not
    # move away from the symmetry plane
    ffdLEList = np.zeros((4, 3))
    ffdTEList = np.zeros((4, 3))
    ffdLEList[0] = wingLEList[0]
    ffdTEList[0] = wingTEList[0]

    ffdLEList[1] = ffdLEList[0]
    ffdTEList[1] = ffdTEList[0]
    ffdLEList[1, wingGeometry["spanIndex"]] = 1e-2
    ffdTEList[1, wingGeometry["spanIndex"]] = 1e-2

    # Next we place an FFD section at the side-of-body location so we can fix that in place
    sobLE = wingLEList[0] + wingGeometry["wingbox"]["SOB"] / wingGeometry["wing"]["semiSpan"] * (
        wingLEList[1] - wingLEList[0]
    )
    sobTE = wingTEList[0] + wingGeometry["wingbox"]["SOB"] / wingGeometry["wing"]["semiSpan"] * (
        wingTEList[1] - wingTEList[0]
    )
    ffdLEList[2] = sobLE
    ffdTEList[2] = sobTE

    # The final FFD section is placed at the wing tip
    ffdLEList[3] = wingLEList[-1]
    ffdTEList[3] = wingTEList[-1]

    for nSpan, nChord, file in zip(numFFDSpan, numFFDChord, fileNames):
        createFittedWingFFD(
            wingSurface,
            surfFormat="point-vector",
            outFile=file,
            leList=ffdLEList,
            teList=ffdTEList,
            nSpan=[2, 1, nSpan],
            nChord=nChord,
            absMargins=[0.05, 0.005, 0.05],
            relMargins=[0.01, 0.005, 0.01],
            liftIndex=wingGeometry["verticalIndex"] + 1,
        )
