from pyhyp import pyHyp
import argparse

parser = argparse.ArgumentParser()

# Problem/task options
parser.add_argument("--level", type=int, default=0)

args = parser.parse_args()

numLayers = [181, 174, 167, 159]  # For growth ratio of 1.1
numLayers = [95, 91, 87, 84]  # For growth ratio of 1.2
firstLayerHeight = 2e-6
numConstLayers = 4

if args.level < 2:
    smoothingSchedule = [[0, 0], [0.2, 0], [0.21, 100], [1.0, 1000]]
else:
    smoothingSchedule = [[0, 0], [0.2, 0], [0.21, 1], [1.0, 100]]

surfMeshFile = "Wing_Surf_L0.cgns"

options = {
    # ---------------------------
    #   General options
    # ---------------------------
    "inputFile": surfMeshFile,
    "fileType": "CGNS",
    "unattachedEdgesAreSymmetry": True,
    "outerFaceBC": "farfield",
    "autoConnect": True,
    "BC": {},
    "families": "wall",
    "coarsen": args.level + 1,
    # ---------------------------
    #   Grid Parameters
    # ---------------------------
    "N": numLayers[args.level] + numConstLayers,
    "s0": firstLayerHeight * (args.level + 1),
    "nConstantStart": numConstLayers,
    "marchDist": 300.0,
    # ---------------------------
    #   Pseudo Grid Parameters
    # ---------------------------
    "ps0": -1.0,
    "pGridRatio": -1.0,
    "cMax": 1.0,
    # ---------------------------
    #   Smoothing parameters
    # ---------------------------
    "epsE": 1.0,
    "epsI": 2.0,
    "theta": 3.0,
    "volCoef": 0.85,
    "volBlend": 0.0005,
    # "volSmoothIter": 100,
    "volSmoothSchedule": smoothingSchedule,
    # ---------------------------
    #   Solution Parameters
    # ---------------------------
    "kspRelTol": 1e-10,
    "kspMaxIts": 1500,
    "kspSubspaceSize": 50,
}

hyp = pyHyp(options=options)
hyp.run()
fileName = f"wing_alt_vol_L{args.level}.cgns"
hyp.writeCGNS(fileName)
