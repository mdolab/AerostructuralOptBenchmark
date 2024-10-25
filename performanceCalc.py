"""
==============================================================================
Basic aircraft mission performance calculations
==============================================================================
@File    :   performanceCalc.py
@Date    :   2023/04/26
@Author  :   Alasdair Christison Gray
@Description :
"""

# ==============================================================================
# Standard Python modules
# ==============================================================================

# ==============================================================================
# External Python modules
# ==============================================================================
import openmdao.api as om
import numpy as np

# ==============================================================================
# Extension modules
# ==============================================================================

# ==============================================================================
# Individual components
# ==============================================================================


# --- Mass calculation components ---
def computeSegmentInitMass(lift, drag, finalMass, R, tsfc, climbAngle, v):
    """Compute the mass at the start of a segment given the mass at the end of the segment using the Breguet range equation

    Parameters
    ----------
    lift : float/complex
        Lift force
    drag : float/complex
        drag force
    finalWeight : float/complex
        Weight at end of segment
    R : float/complex
        Segment range
    tsfc : float/complex
        Thrust specific fuel consumption
    climbAngle : float/complex
        CLimb angle of segment in radians
    v : float/complex
        Flight speed
    """
    LoverD = np.sqrt((lift / drag) ** 2)
    initMass = finalMass * np.exp(R * tsfc / v * (np.cos(climbAngle) / LoverD + np.sin(climbAngle)))
    return initMass


class BreguetRangeSegmentComp(om.ExplicitComponent):
    def initialize(self):
        self.options.declare("R", desc="Segment range")
        self.options.declare("tsfc", desc="Thrust-specific fuel consumption")
        self.options.declare("climbAngle", desc="Climb angle of segment")
        self.options.declare("v", desc="Flight speed")

    def setup(self):
        self.add_input("lift", shape=1, units="N")
        self.add_input("drag", shape=1, units="N")
        self.add_input("finalMass", shape=1, units="kg")
        self.add_output("initMass", shape=1, units="kg")

    def setup_partials(self):
        self.declare_partials("*", "*", method="cs")

    def compute(self, inputs, outputs):
        outputs["initMass"] = computeSegmentInitMass(
            lift=inputs["lift"],
            drag=inputs["drag"],
            finalMass=inputs["finalMass"],
            R=self.options["R"],
            tsfc=self.options["tsfc"],
            climbAngle=self.options["climbAngle"],
            v=self.options["v"],
        )
        # if self.comm.rank == 0:
        #     print(f"SegmentInitMass = {outputs['initMass'][0]: 11.7e}")


def elhamRegression(wingboxMass):
    # Estimate total mass of a wing based on mass of single wingbox using Elham's EMWET regression (see https://doi.org/10.1017/s0001924000008563)
    return 10.147 * wingboxMass**0.8162


class WingMassRegressionComp(om.ExplicitComponent):
    def setup(self):
        self.add_input("wingboxMass", shape=1, units="kg")
        self.add_output("wingMass", shape=1, units="kg")

    def setup_partials(self):
        self.declare_partials(of="*", wrt="*")

    def compute(self, inputs, outputs):
        outputs["wingMass"] = elhamRegression(inputs["wingboxMass"])
        # if self.comm.rank == 0:
        #     print(f"wingMass = {outputs['wingMass'][0]: 11.7e}")

    def compute_partials(self, inputs, partials):
        partials["wingMass", "wingboxMass"] = 10.147 * 0.8162 * inputs["wingboxMass"] ** (0.8162 - 1.0)


def computeLandingGrossMass(wingMass, payloadMass, airframeMass, reserveFuelMass):
    """Compute the landing mass of an aircraft

    Parameters
    ----------
    wingMass : float/complex
        Total mass of one wing
    payloadMass : float/complex
        Mass of the payload
    airframeMass : float/complex
        Mass of the airframe excluding the wings (e.g fuselage, engines, systems weight)
    reserveFuelMass : float/complex
        Reserve fuel mass that needs to be left over at the end of the mission

    Returns
    -------
    float/complex
        Aircraft landing gross mass
    """
    return 2 * wingMass + payloadMass + airframeMass + reserveFuelMass


class LandingGrossMass(om.ExplicitComponent):
    def initialize(self):
        self.options.declare("payloadMass", desc="Mass of the payload")
        self.options.declare(
            "airframeMass",
            types=float,
            desc="Mass of the airframe excluding the wings (e.g fuselage, engines, systems weight)",
        )
        self.options.declare(
            "reserveFuelMass",
            types=float,
            desc="Reserve fuel mass that needs to be left over at the end of the mission",
        )

    def setup(self):
        self.add_input("wingMass", shape=1, units="kg")
        self.add_output("landingGrossMass", shape=1, units="kg")

    def setup_partials(self):
        self.declare_partials(of="landingGrossMass", wrt="wingMass", val=2.0)

    def compute(self, inputs, outputs):
        opt = self.options
        outputs["landingGrossMass"] = computeLandingGrossMass(
            wingMass=inputs["wingMass"],
            payloadMass=opt["payloadMass"],
            airframeMass=opt["airframeMass"],
            reserveFuelMass=opt["reserveFuelMass"],
        )
        # if self.comm.rank == 0:
        #     print(f"landingGrossMass = {outputs['landingGrossMass'][0]: 11.7e}")


def computeMidSegmentMass(initialMass, finalMass):
    """Compute the "mid-segment" Mass for a given segment

    Because the rate of fuel-burn in a segment is not constant,
    a geometric average of the start and end Massses is used to
    estimate the Mass at the mid-point of the segment

    Parameters
    ----------
    initialMass : float/complex
        Segment start mass
    finalMass : float/complex
        Segment end mass
    """
    return np.sqrt(finalMass * initialMass)


class MidSegmentMassComp(om.ExplicitComponent):
    def setup(self):
        self.add_input("initialMass", shape=1, units="kg")
        self.add_input("finalMass", shape=1, units="kg")
        self.add_output("midSegmentMass", shape=1, units="kg")

    def setup_partials(self):
        self.declare_partials(of="*", wrt="*")

    def compute(self, inputs, outputs):
        outputs["midSegmentMass"] = computeMidSegmentMass(
            initialMass=inputs["initialMass"], finalMass=inputs["finalMass"]
        )
        # if self.comm.rank == 0:
        #     print(f"midSegmentMass = {outputs['midSegmentMass'][0]: 11.7e}")

    def compute_partials(self, inputs, partials):
        partials["midSegmentMass", "initialMass"] = (
            0.5 * inputs["finalMass"] / np.sqrt(inputs["finalMass"] * inputs["initialMass"])
        )
        partials["midSegmentMass", "finalMass"] = (
            0.5 * inputs["initialMass"] / np.sqrt(inputs["finalMass"] * inputs["initialMass"])
        )


def computeCorrectedDrag(drag, extraDragCoeff, wingArea, dynPressure):
    return drag + extraDragCoeff * wingArea * dynPressure


# --- Lift and drag calculations ---
class CorrectedDragComp(om.ExplicitComponent):
    def initialize(self):
        self.options.declare("extraDragCoeff", types=float, desc="Extra drag coefficient")
        self.options.declare("wingArea", types=float, desc="Wing area")
        self.options.declare("dynPressure", types=float, desc="Dynamic pressure")

    def setup(self):
        self.add_input("drag", shape=1, units="N")
        self.add_output("correctedDrag", shape=1, units="N")

    def setup_partials(self):
        self.declare_partials(of="correctedDrag", wrt="drag", val=1.0)

    def compute(self, inputs, outputs):
        outputs["correctedDrag"] = computeCorrectedDrag(
            drag=inputs["drag"],
            extraDragCoeff=self.options["extraDragCoeff"],
            wingArea=self.options["wingArea"],
            dynPressure=self.options["dynPressure"],
        )
        # if self.comm.rank == 0:
        #     print(f"correctedDrag = {outputs['correctedDrag'][0]: 11.7e}")


class LiftConstraintComp(om.ExplicitComponent):
    def initialize(self):
        self.options.declare("loadFactor", types=float, desc="Load factor")
        self.options.declare("fuelFraction", types=float, desc="Mass of the aircraft", default=None)

    def setup(self):
        self.add_input("lift", shape=1, units="N")
        self.add_input("mass", shape=1, units="kg")
        if self.options["fuelFraction"] is not None:
            self.add_input("fuelMass", shape=1, units="kg")
        self.add_output("liftDiff", shape=1, units="N")

    def setup_partials(self):
        self.declare_partials(of="liftDiff", wrt="lift", val=2.0)
        self.declare_partials(of="liftDiff", wrt="mass", val=-self.options["loadFactor"] * 9.81)
        if self.options["fuelFraction"] is not None:
            self.declare_partials(of="liftDiff", wrt="fuelMass", val=-self.options["loadFactor"] * 9.81)

    def compute(self, inputs, outputs):
        mass = inputs["mass"]
        if self.options["fuelFraction"] is not None:
            mass += inputs["fuelMass"] * self.options["fuelFraction"]

        outputs["liftDiff"] = 2.0 * inputs["lift"] - mass * self.options["loadFactor"] * 9.81

        # if self.comm.rank == 0:
        #     print(f"liftDiff = {outputs['liftDiff'][0]: 11.7e}")


# --- Misc ---
def computeFuelTankUsage(fuelBurn, wingboxVolume, reserveFuelMass, fuelDensity, wingboxVolumeFraction, auxTankVolume):
    """Compute the percentage of available fuel tank volume used during a mission

    Parameters
    ----------
    fuelBurn : float/complex
        Mass of fuel burned during mission
    wingboxVolume : float/complex
        Volume of one wingbox
    reserveFuelMass : float/complex
        Mass of reserve fuel required at end of mission
    fuelDensity : float/complex
        Density of fuel
    wingboxVolumeFraction : float/complex
        Fraction of the wingbox which assumed to be fuel tank
    auxTankVolume : float/complex
        Volume of auxiliary fuel tanks not in wingbox

    Returns
    -------
    float/complex
        Fuel volume margin, 1.0 = Completely full, 0.0 = Completely empty
    """
    boxVolume = 2.0 * wingboxVolumeFraction * wingboxVolume
    fuelVolume = (fuelBurn + reserveFuelMass) / fuelDensity - auxTankVolume
    return fuelVolume / boxVolume


class FuelTankUsageComp(om.ExplicitComponent):
    def initialize(self):
        self.options.declare("reserveFuelMass", desc="Mass of reserve fuel required at end of mission")
        self.options.declare("fuelDensity", desc="Density of fuel")
        self.options.declare("wingboxVolumeFraction", desc="Fraction of the wingbox which assumed to be fuel tank")
        self.options.declare("auxTankVolume", desc="Volume of auxiliary fuel tanks not in wingbox")

    def setup(self):
        self.add_input("fuelBurn", shape=1, units="kg")
        self.add_input("wingboxVolume", shape=1, units="m**3")
        self.add_output("fuelTankUsage", shape=1)

    def setup_partials(self):
        self.declare_partials("*", "*", method="cs")

    def compute(self, inputs, outputs):
        outputs["fuelTankUsage"] = computeFuelTankUsage(
            fuelBurn=inputs["fuelBurn"],
            wingboxVolume=inputs["wingboxVolume"],
            reserveFuelMass=self.options["reserveFuelMass"],
            fuelDensity=self.options["fuelDensity"],
            wingboxVolumeFraction=self.options["wingboxVolumeFraction"],
            auxTankVolume=self.options["auxTankVolume"],
        )
        # if self.comm.rank == 0:
        #     print(f"fuelTankUsage = {outputs['fuelTankUsage'][0]: 11.7e}")


def computeWingLoading(wingArea, MTOM):
    """Compute the wing loading of an aircraft

    Parameters
    ----------
    MTOM : float/complex
        Aircraft maximum take-off mass
    wingArea : float/complex
        Planform area of a single wing

    Returns
    -------
    float/complex
        Wing loading in units of mass/area
    """
    return MTOM / (2.0 * wingArea)


class WingLoadingComp(om.ExplicitComponent):
    def setup(self):
        self.add_input("wingArea", shape=1, units="m**2")
        self.add_input("MTOM", shape=1, units="kg")
        self.add_output("wingLoading", shape=1, units="kg/m**2")

    def setup_partials(self):
        self.declare_partials(of="*", wrt="*")

    def compute(self, inputs, outputs):
        outputs["wingLoading"] = computeWingLoading(wingArea=inputs["wingArea"], MTOM=inputs["MTOM"])
        # if self.comm.rank == 0:
        #     print(f"wingLoading = {outputs['wingLoading'][0]: 11.7e}")

    def compute_partials(self, inputs, partials):
        partials["wingLoading", "wingArea"] = -inputs["MTOM"] / (2.0 * inputs["wingArea"] ** 2)
        partials["wingLoading", "MTOM"] = 1.0 / (2.0 * inputs["wingArea"])


# ==============================================================================
# OpenMDAO group combining components needed to compute aircraft empty mass
# ==============================================================================
class AirframeMassGroup(om.Group):
    def initialize(self):
        self.options.declare("aircraftSpecs", types=dict)
        self.options.declare("flightPoints", types=list)

    def setup(self):
        self.specs = self.options["aircraftSpecs"]
        self.flightPoints = self.options["flightPoints"]

        # --- Compute wing mass from wingbox mass ---
        wingMassComp = WingMassRegressionComp()
        self.add_subsystem("WingMassRegression", wingMassComp, promotes=["*"])

        # --- Compute landing gross mass ---
        LGMComp = LandingGrossMass(
            payloadMass=self.specs["payloadMass"],
            airframeMass=self.specs["airframeMass"],
            reserveFuelMass=self.specs["reserveFuelMass"],
        )
        self.add_subsystem("MassSummation", LGMComp, promotes=["*"])


# ==============================================================================
# OpenMDAO group combining components needed to compute aircraft fuel burn
# ==============================================================================
class FuelBurnGroup(om.Group):
    def initialize(self):
        self.options.declare("aircraftSpecs", types=dict)
        self.options.declare("flightPoints", types=list)

    def setup(self):
        self.specs = self.options["aircraftSpecs"]
        self.flightPoints = self.options["flightPoints"]

        # --- Drag correction ---
        addedDragComp = CorrectedDragComp(
            extraDragCoeff=self.specs["extraDragCoeff"],
            wingArea=self.specs["refArea"],
            dynPressure=self.flightPoints[0].q,
        )
        self.add_subsystem(
            "dragCorrection", addedDragComp, promotes_inputs=[("drag", "cruiseDrag")], promotes_outputs=["*"]
        )

        # --- Breguet range calculations ---
        # First compute the cruise fuelburn to go from the landing gross mass to the weight at the start of cruise
        cruiseFuelburnComp = BreguetRangeSegmentComp(
            R=self.specs["range"],
            tsfc=self.specs["tsfc"],
            climbAngle=0.0,
            v=self.flightPoints[0].V,
        )
        self.add_subsystem(
            "CruiseFuelBurn",
            cruiseFuelburnComp,
            promotes_outputs=[("initMass", "cruiseStartMass")],
            promotes_inputs=[("lift", "cruiseLift"), ("finalMass", "landingGrossMass")],
        )
        self.connect("correctedDrag", "CruiseFuelBurn.drag")

        # Then compute the takeoff mass by using the cruise start mass as the final mass for the climb segment
        climbFuelburnComp = BreguetRangeSegmentComp(
            R=self.specs["climbRange"],
            tsfc=self.specs["tsfc"],
            climbAngle=self.specs["climbAngle"],
            v=self.specs["climbSpeed"],
        )
        self.add_subsystem(
            "climbFuelBurn",
            climbFuelburnComp,
            promotes_outputs=[("initMass", "TakeoffMass")],
            promotes_inputs=[("lift", "cruiseLift")],
        )
        self.connect("cruiseStartMass", "climbFuelBurn.finalMass")
        self.connect("correctedDrag", "climbFuelBurn.drag")

        # Finally compute the fuelburn as the difference between the takeoff mass and the landing gross mass
        totalFuelBurnComp = om.AddSubtractComp(
            output_name="TotalFuelBurn", input_names=["TakeoffMass", "landingGrossMass"], scaling_factors=[1.0, -1.0]
        )
        self.add_subsystem("totalFuelBurnComp", totalFuelBurnComp, promotes=["*"])


# ==============================================================================
# Top level group combining all performance components/groups
# ==============================================================================
class AircraftPerformanceGroup(om.Group):
    def initialize(self):
        self.options.declare("aircraftSpecs", types=dict)
        self.options.declare("flightPoints", types=list)

    def setup(self):
        self.specs = self.options["aircraftSpecs"]
        self.flightPoints = self.options["flightPoints"]

        massComp = AirframeMassGroup(
            aircraftSpecs=self.specs,
            flightPoints=self.flightPoints,
        )
        self.add_subsystem("airframeMass", massComp, promotes=["landingGrossMass", "wingboxMass"])

        # We can only compute the fuel burn, mid cruise mass, wing loading, and fuel volume if we have a cruise point
        hasCruisePoint = any("cruise" in flightPoint.name.lower() for flightPoint in self.flightPoints)

        if hasCruisePoint:
            fuelBurnComp = FuelBurnGroup(
                aircraftSpecs=self.specs,
                flightPoints=self.flightPoints,
            )
            self.add_subsystem(
                "fuelBurn",
                fuelBurnComp,
                promotes_inputs=["cruiseDrag", "cruiseLift", "landingGrossMass"],
                promotes_outputs=["TotalFuelBurn", "cruiseStartMass", "TakeoffMass"],
            )

            # --- Compute the mid-cruise mass ---
            cruiseMass = MidSegmentMassComp()
            self.add_subsystem("midCruiseMass", cruiseMass, promotes_outputs=[("midSegmentMass", "midCruiseMass")])
            self.connect("landingGrossMass", "midCruiseMass.finalMass")
            self.connect("cruiseStartMass", "midCruiseMass.initialMass")

            # --- Wingbox volume computation ---
            fuelVolumeComp = FuelTankUsageComp(
                reserveFuelMass=self.specs["reserveFuelMass"],
                fuelDensity=self.specs["fuelDensity"],
                wingboxVolumeFraction=self.specs["wingboxFuelVolumeFraction"],
                auxTankVolume=self.specs["auxFuelVolume"],
            )
            self.add_subsystem(
                "fuelVolumeComp", fuelVolumeComp, promotes_outputs=["*"], promotes_inputs=["wingboxVolume"]
            )
            self.connect("TotalFuelBurn", "fuelVolumeComp.fuelBurn")

            # --- Wing loading constraint ---
            wingLoadingComp = WingLoadingComp()
            self.add_subsystem("wingLoadingComp", wingLoadingComp, promotes_outputs=["*"], promotes_inputs=["wingArea"])
            self.connect("TakeoffMass", "wingLoadingComp.MTOM")

        # --- Add a lift constrain for each flight point ---
        for flightPoint in self.flightPoints:
            name = flightPoint.name
            hasFuelInput = False
            if "cruise" in flightPoint.name.lower():
                # This is a cruise flight point, so the target lift is the mid-cruise weight
                flightPointMassVariable = "midCruiseMass"
                LiftConstraint = LiftConstraintComp(loadFactor=flightPoint.loadFactor)
            else:
                # This is a maneuver flight point, so the target lift is the landing gross weight + a fraction of the fuel weight
                hasFuelInput = flightPoint.fuelFraction != 0
                flightPointMassVariable = "landingGrossMass"
                LiftConstraint = LiftConstraintComp(
                    loadFactor=flightPoint.loadFactor, fuelFraction=flightPoint.fuelFraction if hasFuelInput else None
                )
            self.add_subsystem(
                f"{name}LiftConstraint",
                LiftConstraint,
                promotes_inputs=[("lift", f"{name}Lift")],
                promotes_outputs=[("liftDiff", f"{name}LiftDiff")],
            )
            self.connect(flightPointMassVariable, f"{name}LiftConstraint.mass")

            if hasFuelInput:
                self.connect("TotalFuelBurn", f"{name}LiftConstraint.fuelMass")


# Test the performance group derivatives
if __name__ == "__main__":
    import os
    import sys

    sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../AircraftSpecs"))
    from AircraftSpecs.STWSpecs import aircraftSpecs  # noqa: E402
    from AircraftSpecs.STWFlightPoints import flightPointSets  # noqa: E402

    prob = om.Problem()
    prob.model = AircraftPerformanceGroup(aircraftSpecs=aircraftSpecs, flightPoints=flightPointSets["3pt"])
    prob.setup()
    # Set some reasonable input values
    prob.set_val("wingboxMass", 1000.0, units="kg")
    prob.set_val("wingboxVolume", 6.0, units="m**3")
    prob.set_val("wingArea", aircraftSpecs["refArea"], units="m**2")
    for fp in flightPointSets["3pt"]:
        prob.set_val(f"{fp.name}Lift", fp.loadFactor * aircraftSpecs["refMTOW"] * 9.81 / 2.0)
    prob.set_val("cruiseDrag", aircraftSpecs["refMTOW"] * 9.81 / 2.0 / 20)
    prob.run_model()
    prob.model.list_outputs()
    prob.check_partials(compact_print=True, form="central", step=1e-6)
    om.n2(prob, show_browser=True)
