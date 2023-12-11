"""
==============================================================================
Wingbox mesh generation
==============================================================================
@File    :   generate_wingbox.py
@Date    :   2023/03/29
@Author  :   Alasdair Christison Gray
@Description :
"""

# ==============================================================================
# Standard Python modules
# ==============================================================================
import argparse
import sys

# ==============================================================================
# External Python modules
# ==============================================================================
import numpy
from pygeo import pyGeo, geo_utils
from pylayout import pyLayout

# ==============================================================================
# Extension modules
# ==============================================================================
sys.path.append("../geometry")
from wingGeometry import wingGeometry  # noqa: E402

parser = argparse.ArgumentParser()
parser.add_argument("--order", type=int, default=2, help="Order of elements", choices=[2, 3, 4])
parser.add_argument(
    "--nChord",
    type=int,
    default=25,
    help="Number of elements in the chordwise direction",
)
parser.add_argument(
    "--nSpan",
    type=int,
    default=10,
    help="Number of elements in the spanwise direction (between each pair of ribs)",
)
parser.add_argument(
    "--nVertical",
    type=int,
    default=10,
    help="Number of elements in the vertical direction",
)
parser.add_argument("--name", type=str, default="wingbox", help="Name of output file")
args = parser.parse_args()

# ==============================================================================
#       Specify wingbox properties
# ==============================================================================
chords = wingGeometry["wing"]["sectionChord"]  # root and tip chords
sweep = [0, 7.5]  # root and tip sweep
semiSpan = wingGeometry["wing"]["semiSpan"]
sob = wingGeometry["wingbox"]["SOB"]  # span location of side-of-body
ncols = wingGeometry["wingbox"]["numRibs"]  # number of columns (aligned with ribs)
nrows = wingGeometry["wingbox"]["numSpars"]  # number of rows (aligned with spars)
nbreak = wingGeometry["wingbox"]["numRibsCentrebody"]  # column index of side-of-body kink

# Number of quad elements in each component
numElementChord = args.nChord  # Elements between each spar pair
numElementSpan = args.nSpan  # Elements between each rib pair
numElementVertical = args.nVertical  # Elements between skins

colSpace = numElementSpan * numpy.ones(ncols - 1, "intc")  # elements between columns
rowSpace = numElementChord * numpy.ones(nrows + 1, "intc")  # elements between rows

# ==============================================================================
#       Set up blanking arrays
# ==============================================================================

# Blanking for ribs (None)
ribBlank = numpy.ones((ncols, nrows - 1), "intc")

# Blanking for spars
sparBlank = numpy.zeros((nrows, ncols - 1), "intc")
sparBlank[0, :] = 1  # Keep First
sparBlank[-1, :] = 1  # Keep Last


# Blanking for rib stiffeners:
ribStiffenerBlank = numpy.zeros((ncols, nrows), "intc")  # No rib stiffeners
teEdgeList = []

# ==============================================================================
#       Set up array of grid coordinates for ribs, spars
# ==============================================================================
leList = wingGeometry["wingbox"]["LESparCoords"]

teList = wingGeometry["wingbox"]["TESparCoords"]

# Initialize grid coordinate matrix
X = numpy.zeros((ncols, nrows, 3))

# Fill in LE and TE coordinates from root to side-of-body
X[0:nbreak, 0] = geo_utils.linearEdge(leList[0], leList[1], nbreak)
X[0:nbreak, -1] = geo_utils.linearEdge(teList[0], teList[1], nbreak)

# Fill in LE and TE coordinates from side-of-body to tip
X[nbreak - 1 : ncols, 0] = geo_utils.linearEdge(leList[1], leList[2], ncols - nbreak + 1)
X[nbreak - 1 : ncols, -1] = geo_utils.linearEdge(teList[1], teList[2], ncols - nbreak + 1)

# Finally fill in chord-wise with linear edges
for i in range(ncols):
    X[i, :] = geo_utils.linearEdge(X[i, 0], X[i, -1], nrows)

# Boundary conditions
spanIndex = wingGeometry["spanIndex"]
chordIndex = wingGeometry["chordIndex"]
verticalIndex = wingGeometry["verticalIndex"]
symBCDOF = [spanIndex, chordIndex + 3, verticalIndex + 3]
symBCDOF = "".join([str(dof + 1) for dof in symBCDOF])

sobBCDOF = [chordIndex, verticalIndex]
sobBCDOF = "".join([str(dof + 1) for dof in sobBCDOF])

ribBC = {
    0: {"all": symBCDOF},
    nbreak - 1: {"edge": sobBCDOF},
}

# ==============================================================================
#       Generate wingbox
# ==============================================================================
# Get surface definition to use for projections
surfFile = "../geometry/wing.igs"
geo = pyGeo("iges", fileName=surfFile)

# Initialize pyLayout
layout = pyLayout.Layout(
    geo,
    teList=[],
    nribs=ncols,
    nspars=nrows,
    elementOrder=args.order,
    X=X,
    ribBlank=ribBlank,
    sparBlank=sparBlank,
    ribStiffenerBlank=ribStiffenerBlank,
    spanSpace=colSpace,
    ribSpace=rowSpace,
    vSpace=numElementVertical,
    ribBC=ribBC,
    rightWing=True,
)
# Write bdf file
layout.finalize(f"{args.name}.bdf")

# Write a tecplot file
layout.writeTecplot(f"{args.name}.dat")
