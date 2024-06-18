"""
==============================================================================
Definition of MACH Tutorial wing flight points
==============================================================================
@File    :   STWFlightPoints.py
@Date    :   2023/10/05
@Author  :   Alasdair Christison Gray
@Description :
"""

# ==============================================================================
# Standard Python modules
# ==============================================================================

# ==============================================================================
# External Python modules
# ==============================================================================

# ==============================================================================
# Extension modules
# ==============================================================================
from FlightPoint import FlightPoint

# ==============================================================================
# Cruise conditions
# ==============================================================================
# Standard cruise condition taken from https://en.wikipedia.org/wiki/Boeing_717#Specifications
CRUISE_ALTITUDE = 10.4e3  # meters
CRUISE_MACH = 0.77
standardCruise = FlightPoint(
    "cruise",
    loadFactor=1.0,
    fuelFraction=1.0,
    failureGroups=[],
    mach=CRUISE_MACH,
    altitude=CRUISE_ALTITUDE,
    alpha=3.874,
    evalFuncs=["lift", "drag", "cl", "cd"],
)

# ==============================================================================
# Maneuver conditions
# ==============================================================================
# The maneuver flight condition is taken from:
# https://www.flyradius.com/boeing-717/200-specifications-dimensions
# I converted the KCAS (263 @ 0 ft) value to a Mach number using https://aerotoolbox.com/airspeed-conversions/
# I then boost the flight speed by 15% so that we're not trying to simulate the aircraft right at CL max
MANEUVER_MACH = 0.398 * 1.15
MANEUVER_ALTITUDE = 0.0
MANEUVER_FUEL_LOAD_FRACTION = (
    0.0  # Perform the maneuver with zero fuel mass since we are not modelling the fuel's inertial relief in TACS
)

seaLevelLowSpeedPullUp = FlightPoint(
    "mnver_sealevel_va_pullup",
    loadFactor=2.5,
    fuelFraction=MANEUVER_FUEL_LOAD_FRACTION,
    failureGroups=["l_skin", "u_skin", "spar", "rib"],
    mach=MANEUVER_MACH,
    altitude=MANEUVER_ALTITUDE,
    alpha=10.3,
    evalFuncs=["lift", "drag", "cl", "cd"],
)

seaLevelLowSpeedPushDown = FlightPoint(
    "mnver_sealevel_va_pushdown",
    loadFactor=-1.0,
    fuelFraction=MANEUVER_FUEL_LOAD_FRACTION,
    failureGroups=["l_skin"],
    mach=MANEUVER_MACH,
    altitude=MANEUVER_ALTITUDE,
    alpha=-6.4,
    evalFuncs=["lift", "drag", "cl", "cd"],
)

# ==============================================================================
# Define sets of flight points
# ==============================================================================
flightPointSets = {
    "cruise": [standardCruise],
    "mnver_sealevel_va_pullup": [seaLevelLowSpeedPullUp],
    "mnver_sealevel_va_pushdown": [seaLevelLowSpeedPushDown],
    "3pt": [standardCruise, seaLevelLowSpeedPullUp, seaLevelLowSpeedPushDown],
    "2pt": [standardCruise, seaLevelLowSpeedPullUp],
    "maneuverOnly": [seaLevelLowSpeedPullUp, seaLevelLowSpeedPushDown],
}
