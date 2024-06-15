"""
==============================================================================
DVGeo setup example
==============================================================================
@File    :   setupDVGeo.py
@Date    :   2024/06/14
@Author  :   Alasdair Christison Gray
@Description : This file contains an example script that sets up the full
geometric parameterisation for case 3 using the FFDs created by generateOML.py.
This code can be modified to fit into
"""

# ==============================================================================
# Standard Python modules
# ==============================================================================
import os
import copy

# ==============================================================================
# External Python modules
# ==============================================================================
from pygeo.parameterization import DVGeometry
import numpy as np
from scipy.interpolate import CubicSpline

# ==============================================================================
# Extension modules
# ==============================================================================
from wingGeometry import wingGeometry  # noqa: E402


def setupDVGeo(args, DVGeo):

    spanIndex = wingGeometry["spanIndex"]
    chordIndex = wingGeometry["chordIndex"]
    verticalIndex = wingGeometry["verticalIndex"]

    # Create reference axis along the leading edge
    numRefAxPts = DVGeo.addRefAxis(name="wing", xFraction=0.00675, alignIndex="j")
    numRootSections = 3
    numSOBSections = 3
    numMovingSections = numRefAxPts - numRootSections - (numSOBSections)

    # Figure out the original chord lengths at the FFD sections, we need these so that we can keep a linear taper when changing the root and tip chords
    refAxisCoords = DVGeo.axis["wing"]["curve"].X
    ffdSectionSpanwiseCoords = refAxisCoords[:, spanIndex]
    ffdSectionEta = ffdSectionSpanwiseCoords / ffdSectionSpanwiseCoords[-1]
    sectionEta = wingGeometry["wing"]["sectionEta"]
    sectionChord = wingGeometry["wing"]["sectionChord"]
    ffdSectionChords = np.interp(ffdSectionEta, sectionEta, sectionChord)

    # Figure out the chordwise distance between the reference axis and the leading edge spar at the root and SOB
    wingboxLECoords = wingGeometry["wingbox"]["LESparCoords"]
    centreBoxLECoord = wingboxLECoords[0, chordIndex]
    RootRefAxisCoord = refAxisCoords[0, chordIndex]
    SOBRefAxisCoord = refAxisCoords[numRootSections, chordIndex]

    RootLESparOffset = centreBoxLECoord - RootRefAxisCoord
    SOBLESparOffset = centreBoxLECoord - SOBRefAxisCoord

    if args.twist:

        def twist(val, geo):
            if spanIndex == 1:
                twistArray = geo.rot_y["wing"]
            elif spanIndex == 2:
                twistArray = geo.rot_z["wing"]
            # We don't twist the wing at the root because we have an angle of attack DV, we will also not twist at the SOB
            # because this would make the centre wingbox section very unrealistic
            sobStartInd = numRootSections
            sobEndInd = sobStartInd + numSOBSections
            # twistArray.coef[sobStartInd:sobEndInd] = val[0]
            for i in range(sobEndInd, numRefAxPts):
                twistArray.coef[i] = val[i - sobEndInd]

        DVGeo.addGlobalDV(dvName="twist", value=[0] * numMovingSections, lower=-20.0, upper=20.0, func=twist)

    if args.taper:

        def taper(val, geo):
            # We scale the root and tip chords by the two DV values, then linearly interpolate the chord length (not the scaling
            # factor!) to the other FFD sections
            s = geo.extractS("wing")
            sobInd = numRootSections + numSOBSections - 1

            rootChord = ffdSectionChords[sobInd] * val[0]
            tipChord = ffdSectionChords[-1] * val[1]

            # Scale all of the root and SOB sections by the root chord scaling factor
            geo.scale_x["wing"].coef[:sobInd] = val[0]

            for ii in range(sobInd, numRefAxPts):
                spanwiseCoord = (s[ii] - s[sobInd]) / (s[-1] - s[sobInd])
                origChord = ffdSectionChords[ii]
                newChord = rootChord + (tipChord - rootChord) * spanwiseCoord
                geo.scale_x["wing"].coef[ii] = newChord / origChord
            # We need to shift the root section in the chordwise section to keep the centre wingbox section straight.
            # To do this, we need to know the distance between the reference axis and the leading edge spar at both the root and SOB
            C = geo.extractCoef("wing")
            C[:numRootSections, chordIndex] += (val[0] - 1.0) * (SOBLESparOffset - RootLESparOffset)
            geo.restoreCoef(C, "wing")

        DVGeo.addGlobalDV(dvName="taper", func=taper, lower=0.25, upper=2.0, value=[1.0] * 2)

    if args.span:

        def span(val, geo):
            C = geo.extractCoef("wing")
            s = geo.extractS("wing")
            sobInd = numRootSections + numSOBSections - 1
            for i in range(sobInd + 1, numRefAxPts):
                frac = (s[i] - s[sobInd]) / (s[-1] - s[sobInd])
                C[i, spanIndex] += val[0] * frac
            geo.restoreCoef(C, "wing")

        DVGeo.addGlobalDV(dvName="span", value=0.0, lower=-10.0, upper=20.0, func=span)

    if args.sweep:

        def sweep(val, geo):
            C = geo.extractCoef("wing")
            s = geo.extractS("wing")
            sobInd = numRootSections + numSOBSections - 1
            for i in range(sobInd + 1, numRefAxPts):
                frac = (s[i] - s[sobInd]) / (s[-1] - s[sobInd])
                C[i, chordIndex] += val[0] * frac
            geo.restoreCoef(C, "wing")

        DVGeo.addGlobalDV(dvName="sweep", value=0.0, lower=-10.0, upper=10.0, func=sweep)

    # We can't use typical local variables because at both the root and SOB we have 3 tightly spaced FFD sections that
    # we want to move together. We therefore need to use shape functions. We will not add DVs for the trailing edge
    # nodes because they are only useful for pinching the trailing edge, which we don't want to do. For the leading edge
    # nodes, we add a single DV for each FFD section that moves the upper and lower nodes together/apart without
    # shifting the leading edge up or down.

    # As a reminder, shape functions are defined using a list of dictionaries, each dictionary defines the shape of a
    # single DV, keys are the local ID of each node to move, values are the direction and magnitude of the motion of
    # that node in response to the DV.
    if args.shape:

        shapes = []
        ffdLocalInds = DVGeo.getLocalIndex(0)

        numChordwisePoints = ffdLocalInds.shape[0]

        direction = np.zeros(3)
        direction[verticalIndex] = 1.0

        # For each chordwise point, excluding the first and last (which are the leading and trailing edge nodes)
        for chordInd in range(1, numChordwisePoints - 1):
            # For the upper and lower nodes
            for verticalInd in range(ffdLocalInds.shape[2]):
                # Add one shape function to move this point in the root sections together
                rootShape = {}
                for spanInd in range(numRootSections):
                    rootShape[ffdLocalInds[chordInd, spanInd, verticalInd]] = direction
                shapes.append(rootShape)

                # Add one shape function to move this point in the SOB sections together
                sobShape = {}
                for spanInd in range(numRootSections, numRootSections + numSOBSections):
                    sobShape[ffdLocalInds[chordInd, spanInd, verticalInd]] = direction
                shapes.append(sobShape)

                # Add separate shape functions for each of the remaining sections
                for spanInd in range(numRootSections + numSOBSections, numRefAxPts):
                    shape = {ffdLocalInds[chordInd, spanInd, verticalInd]: direction}
                    shapes.append(shape)

        # Now add the leading edge DVs
        rootShape = {}
        for spanInd in range(numRootSections):
            rootShape[ffdLocalInds[0, spanInd, 0]] = -direction
            rootShape[ffdLocalInds[0, spanInd, -1]] = direction
        shapes.append(rootShape)
        sobShape = {}
        for spanInd in range(numRootSections, numRootSections + numSOBSections):
            sobShape[ffdLocalInds[0, spanInd, 0]] = -direction
            sobShape[ffdLocalInds[0, spanInd, -1]] = direction
        shapes.append(sobShape)

        for spanInd in range(numRootSections + numSOBSections, numRefAxPts):
            shape = {}
            shape[ffdLocalInds[0, spanInd, 0]] = -direction
            shape[ffdLocalInds[0, spanInd, -1]] = direction
            shapes.append(shape)

        DVGeo.addShapeFunctionDV("localShape", shapes, lower=-0.5, upper=0.5)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--ffdLevel", type=str, default="coarse", choices=["coarse", "med", "fine"])
    parser.add_argument("--twist", action="store_true")
    parser.add_argument("--shape", action="store_true")
    parser.add_argument("--sweep", action="store_true")
    parser.add_argument("--span", action="store_true")
    parser.add_argument("--taper", action="store_true")
    args = parser.parse_args()

    ffdFile = f"wing-ffd-advanced-{args.ffdLevel}.xyz"

    DVGeo = DVGeometry(ffdFile)

    setupDVGeo(args, DVGeo)

    # ==============================================================================
    # Write out a series of deformed FFDs to demonstrate the DVs
    # ==============================================================================
    outputDir = "DVGeoDemo"
    os.makedirs(outputDir, exist_ok=True)
    framesPerSec = 30
    secPerDV = 3

    x0 = DVGeo.getValues()

    # We need to embed some points in the FFD so that it will actually deform when we change the DVs
    dummypoints = np.array([[1.5, 1.0, 0.0]])
    DVGeo.addPointSet(dummypoints, "dummy")

    # ==============================================================================
    # Global DVs
    # ==============================================================================
    for dvName, DV in DVGeo.DV_listGlobal.items():
        lower = DV.lower
        upper = DV.upper
        numVals = len(x0[dvName])
        numFrames = framesPerSec * secPerDV // numVals
        for ii in range(numVals):
            y = [x0[dvName][ii], upper[ii], lower[ii], x0[dvName][ii]]
            spline = CubicSpline(np.linspace(0, 1, len(y)), y, bc_type="clamped")
            dvVals = spline(np.linspace(0, 1, numFrames))
            for jj in range(len(dvVals)):
                DVGeo.setDesignVars(x0)
                x = copy.deepcopy(x0)
                x[dvName][ii] = dvVals[jj]
                DVGeo.setDesignVars(x)
                DVGeo.writeTecplot(os.path.join(outputDir, f"{dvName}_{ii:02d}_{jj:03d}-FFD.dat"))
                print(f"{dvName}_{ii}_{jj}")

    # ==============================================================================
    # Local DVs
    # ==============================================================================
    np.random.seed(314)
    dvFactor = 0.2 * np.sin(np.linspace(0, 2 * np.pi, framesPerSec * secPerDV))
    for dvName, DV in DVGeo.DV_listLocal.items():
        numVals = len(x0[dvName])
        pert = DV.upper * (0.5 - np.random.rand(numVals)) * 2.0
        for jj in range(len(dvFactor)):
            DVGeo.setDesignVars(x0)
            x = copy.deepcopy(x0)
            x[dvName] = x0[dvName] + dvFactor[jj] * pert
            DVGeo.setDesignVars(x)
            DVGeo.writeTecplot(os.path.join(outputDir, f"{dvName}_{jj:03d}-FFD.dat"))
            print(f"{dvName}_{jj}")
