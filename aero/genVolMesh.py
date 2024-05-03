"""
==============================================================================
Volume mesh extrusion
==============================================================================
@File    :   genVolMesh.py
@Date    :   2024/03/28
@Author  :   Anil Yildirim, slightly modified by Alasdair Christision Gray
@Description : Program to extrude CFD volume meshes using pyHyp
"""

# ==============================================================================
# Standard Python modules
# ==============================================================================
import argparse

# ==============================================================================
# External Python modules
# ==============================================================================
from mpi4py import MPI
from pyhyp import pyHyp
from cgnsutilities.cgnsutilities import readGrid

# ==============================================================================
# Extension modules
# ==============================================================================


parser = argparse.ArgumentParser()
parser.add_argument("--level", default="L3")
args = parser.parse_args()

rank = MPI.COMM_WORLD.rank

# process the arguments and set up the variables
comm = MPI.COMM_WORLD

mesh_name = f"wing_vol_{args.level}"

# print all arguments
if comm.rank == 0:
    print("Arguments are:")
    for argname in vars(args):
        print(argname, ":", getattr(args, argname))

if args.level in ["L1", "L2", "L3"]:
    surface_family = "S1"
else:
    surface_family = "S0.7"

# factor for spacings
levelFact = {
    "L3": 0.5,
    "L2": 1.0,
    "L1.4": 1.4,
    "L1": 2.0,
    "L0.7": 2.8,
}
fact = levelFact[args.level]

# reference first off wall spacing for L2 level meshes
s0 = 3.6e-6 / fact

# farfield distance. this is adjusted to compensate for the mesh levels
marchDist = {
    "L3": 350.0,
    "L2": 325.0,
    "L1.4": 310.0,
    "L1": 305.0,
    "L0.7": 300.0,
}[args.level]

# levels of coarsening for the surface meshes
coarsen = {
    "L3": 3,
    "L2": 2,
    "L1.4": 2,
    "L1": 1,
    "L0.7": 1,
}[args.level]

levelNGrid = {
    "L3": 49,
    "L2": 65,
    "L1.4": 97,
    "L1": 129,
    "L0.7": 193,
}
nGrid = levelNGrid[args.level]

nConstantStart = {"L3": 1, "L2": 2, "L1.4": 2, "L1": 3, "L0.7": 3}[args.level]

options = {
    # ---------------------------
    #   General options
    # ---------------------------
    "inputFile": f"wing_surf_{surface_family}.cgns",
    "fileType": "CGNS",
    "unattachedEdgesAreSymmetry": True,
    "outerFaceBC": "farfield",
    "autoConnect": True,
    "BC": {},
    "families": "wall",
    # ---------------------------
    #   Grid Parameters
    # ---------------------------
    "N": nGrid,
    "s0": s0,
    "marchDist": marchDist,
    "nConstantStart": nConstantStart,
    "coarsen": coarsen,
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
    "volCoef": 0.25,
    "volBlend": 1e-4,
    # TODO AY-AG: this option below is implemented in one of my pyhyp branches. The final using this custom blend schedule will be better, but a fixed blend is also fine.
    # "volBlendSchedule": [[0.0, 1e-8], [0.1, 1e-7], [0.2, 1e-6], [0.4, 1e-5], [0.6, 1e-4], [1.0, 1e-3]],
    "volSmoothIter": 100,
    "kspreltol": 1e-8,
    # ---------------------------
    #   Solution Parameters
    # ---------------------------
    "kspRelTol": 1e-10,
    "kspMaxIts": 1500,
    "kspSubspaceSize": 50,
}

hyp = pyHyp(options=options)
hyp.run()
hyp.writeCGNS(f"{mesh_name}.cgns")

if rank == 0:
    # finally, print information about the grid
    finalGrid = readGrid(f"{mesh_name}.cgns")
    print("\nGrid info:")
    finalGrid.printInfo()
