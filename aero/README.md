# Aerodynamic meshes

**Important:** These meshes are not the ones used in our original paper (hope they're better). You can find the original meshes in the [v0.0.1 release of this repo](https://github.com/mdolab/AerostructuralOptBenchmark/tree/v0.0.1/aero).

Currently, there are 3 mesh levels available for the wing:

- **L1 - 7.7m cells:** Fine grid, for grid convergence studies
- **L2 - 1.0m cells:** Medium grid, for optimizations
- **L3 - 180k cells:** Coarse grid, for debugging

## File descriptions:

- **`wing_surf_S1.cgns`:** Level 1 surface mesh of the wing
- **`genVolMesh.py`:** Python script for extruding volume meshes using [pyHyp](github.com/mdolab/pyhyp)
- **`ExtrudeMeshes.sh`:** Bash script which will run `genVolMesh.py` for you to generate the family of volume meshes