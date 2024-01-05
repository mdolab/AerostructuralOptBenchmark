from baseclasses import AeroProblem
from typing import List


class FlightPoint(AeroProblem):
    def __init__(self, name: str, loadFactor: float, fuelFraction: float, failureGroups: List[str], **kwargs):
        """Define a flight condition, this is basically just an AeroProblem with a few extra attributes

        Parameters
        ----------
        name : string
            Name of the flight point, should be unique and currently must contain either "cruise" or "maneuver
        loadFactor : float
            Flight point load factor (how many G's the aircraft is pulling)
        fuelFraction : float
            What fraction of the total fuel mass is the aircraft carrying at this flight point
        failureGroups : list of strings
            Names of wingbox component groups for which to compute a failure constraint value at this flight point
        """
        super().__init__(name=name, **kwargs)

        self.loadFactor = loadFactor
        self.fuelFraction = fuelFraction
        self.failureGroups = failureGroups
