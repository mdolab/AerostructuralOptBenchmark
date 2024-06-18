"""
==============================================================================
MACH Tutorial wing aircraft and mission specifications
==============================================================================
@File    :   STWSpecs.py
@Date    :   2023/10/05
@Author  :   Alasdair Christison Gray
@Description :
"""

# ==============================================================================
# Standard Python modules
# ==============================================================================
import sys
import os

# ==============================================================================
# External Python modules
# ==============================================================================
import numpy as np
import openmdao.api as om
from openconcept.aerodynamics import ParasiteDragCoefficient_JetTransport

# ==============================================================================
# Extension modules
# ==============================================================================
from STWFlightPoints import standardCruise

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../geometry"))
from wingGeometry import wingGeometry  # noqa: E402


# ==============================================================================
# Aircraft Data
# ==============================================================================
# --- Specs based on the high gross weight version of the Boeing 717 ---
# https://en.wikipedia.org/wiki/Boeing_717#Specifications
REF_AREA = wingGeometry["wing"]["planformArea"]  # half-wing in m^2
REF_CHORD = wingGeometry["wing"]["meanAerodynamicChord"]  # meters
REF_MTOW = 55e3  # kg
REF_WING_LOADING = REF_MTOW / (2 * REF_AREA)  # kg/m^2
RANGE = 3815e3  # meters
PAYLOAD_MASS = 14.5e3  # kg
AIRFRAME_MASS = 25e3  # kg (approx based on true empty weight of 31,100 kg)

# --- Fuel parameters ---
RESERVE_FUEL_MASS = 2e3  # kg
WINGBOX_FUEL_VOLUME_FRACTION = (
    0.85  # Fraction of the wingbox volume that can be used to store fuel, I chose this number completely arbitrarily
)
AUX_FUEL_VOLUME = 2.763  # m^3, volume of the auxiliary fuel tanks not in the wingbox (730 gallons)
FUEL_DENSITY = 804.0  # kg/m^3
TSFC = (
    18.1e-6 * 9.81
)  # (kg/N-s) * g, based on wikipedia value for the BR700 (the 717 uses the BR715) https://en.wikipedia.org/wiki/Thrust-specific_fuel_consumption#Typical_values_of_SFC_for_thrust_engines


# --- Climb specs ---
CLIMB_SPEED = 350.0 / 2.25  # 350. mph in m/s
CLIMB_RANGE = (
    180.0 * 1609.34
)  # 180. miles in meters (this is roughly based on some flight data of a Boeing 717 I looked at on flightaware.com)
CLIMB_ANGLE = np.arctan(standardCruise.altitude / CLIMB_RANGE)  # radians

# --- Misc specs ---
MAX_WING_LOADING = 600.0  # kg/m^2 Max allowable wing loading

# ==============================================================================
# Airframe drag estimate
# ==============================================================================
fuselageLaminarFrac = 0.05  # Raymer table 12.4
tailLaminarFrac = 0.1  # Raymer table 12.4

nacelle = wingGeometry["nacelle"]
nacelle_f = nacelle["length"] / nacelle["diameter"]
nacelleFormFactor = 1.0 + 0.35 / (nacelle_f)  # Raymer sec 12.5.4 eq 12.32
nacelleFormFactor *= (
    1.3  # Multiply by form factor of 1.3 for nacelle mounted with one diameter of fuselage, Raymer sec 12.5.5
)

QTail = 1.03  # Interference factor for clean tail, presumably from Raymer sec 12?

tailThickness = 0.1  # Guess of tail t/c
maxThickLoc = 0.5  # Guess of tail max thickness location


dragProb = om.Problem()
dragProb.model = ParasiteDragCoefficient_JetTransport(
    include_wing=False,
    FF_nacelle=nacelleFormFactor,
    Q_tail=QTail,
    fuselage_laminar_frac=fuselageLaminarFrac,
    hstab_laminar_frac=tailLaminarFrac,
    vstab_laminar_frac=tailLaminarFrac,
)
dragProb.setup()
dragProb.set_val("fltcond|Utrue", standardCruise.a * standardCruise.mach)
dragProb.set_val("fltcond|rho", standardCruise.rho)
dragProb.set_val("fltcond|T", standardCruise.T)
dragProb.set_val("ac|geom|fuselage|length", wingGeometry["fuselage"]["length"])
dragProb.set_val("ac|geom|fuselage|height", wingGeometry["fuselage"]["width"])
dragProb.set_val("ac|geom|fuselage|S_wet", wingGeometry["fuselage"]["area"])
dragProb.set_val("ac|geom|hstab|S_ref", wingGeometry["hTail"]["planformArea"] * 2)
dragProb.set_val("ac|geom|hstab|AR", wingGeometry["hTail"]["aspectRatio"])
dragProb.set_val("ac|geom|hstab|taper", wingGeometry["hTail"]["taperRatio"])
dragProb.set_val("ac|geom|hstab|toverc", tailThickness)
dragProb.set_val("ac|geom|vstab|S_ref", wingGeometry["vTail"]["planformArea"])
dragProb.set_val("ac|geom|vstab|AR", wingGeometry["vTail"]["aspectRatio"])
dragProb.set_val("ac|geom|vstab|taper", wingGeometry["vTail"]["taperRatio"])
dragProb.set_val("ac|geom|vstab|toverc", tailThickness)
dragProb.set_val("ac|geom|wing|S_ref", REF_AREA * 2)
dragProb.set_val("ac|geom|nacelle|length", nacelle["length"])
dragProb.set_val("ac|geom|nacelle|S_wet", nacelle["area"])
dragProb.set_val("ac|propulsion|num_engines", 2)
dragProb.run_model()
EXTRA_DRAG_COEFF = dragProb.get_val("CD0")[0]

aircraftSpecs = {
    "refArea": REF_AREA,
    "refChord": REF_CHORD,
    "refMTOW": REF_MTOW,
    "range": RANGE,
    "payloadMass": PAYLOAD_MASS,
    "airframeMass": AIRFRAME_MASS,
    "reserveFuelMass": RESERVE_FUEL_MASS,
    "wingboxFuelVolumeFraction": WINGBOX_FUEL_VOLUME_FRACTION,
    "auxFuelVolume": AUX_FUEL_VOLUME,
    "extraDragCoeff": EXTRA_DRAG_COEFF,
    "tsfc": TSFC,
    "fuelDensity": FUEL_DENSITY,
    "maxWingLoading": MAX_WING_LOADING,
    "climbAngle": CLIMB_ANGLE,
    "climbSpeed": CLIMB_SPEED,
    "climbRange": CLIMB_RANGE,
}
