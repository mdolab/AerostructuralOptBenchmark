# Wing geometry

## File descriptions:

- **`wing.igs/tin/dat`:** Geometry files of the wing outer mold line (OML)
- **`rae2822.dat`:** Airfoil coordinates for the RAE2822 airfoil
- **`wing-ffd-coarse/med/fine.xyz`:** FFD control volume definitions compatible with [pyGeo](github.com/mdolab/pygeo)
- **`generateOML.py`:** Python script that generates the wing OML geometry and FFD files using [pyGeo](github.com/mdolab/pygeo)
- **`wingGeometry.py`:** Python script that defines a bunch of stuff about the wing geometry, designed to be imported into other scripts, specifically the `wingGeometry` dictionary.
