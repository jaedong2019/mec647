#!/usr/bin/env python3

from mpi4py import MPI


def mesh_bar_gmshapi(name,
                     Lx,
                     Ly,
                     lc,
                     tdim,
                     order=1,
                     msh_file=None,
                     comm=MPI.COMM_WORLD):
    """
    Create mesh of 3d tensile test specimen according to ISO 6892-1:2019 using the Python API of Gmsh.
    """
    # Perform Gmsh work only on rank = 0

    if comm.rank == 0:

        import gmsh

        # Initialise gmsh and set options
        gmsh.initialize()
        gmsh.option.setNumber("General.Terminal", 1)

        gmsh.option.setNumber("Mesh.Algorithm", 6)
        model = gmsh.model()
        model.add("Rectangle")
        model.setCurrent("Rectangle")
        p0 = model.geo.addPoint(0.0, 0.0, 0, lc, tag=0)
        p1 = model.geo.addPoint(Lx, 0.0, 0, lc, tag=1)
        p2 = model.geo.addPoint(Lx, Ly, 0.0, lc, tag=2)
        p3 = model.geo.addPoint(0, Ly, 0, lc, tag=3)
        # points = [p0, p1, p2, p3]
        bottom = model.geo.addLine(p0, p1, tag=0)
        right = model.geo.addLine(p1, p2, tag=1)
        top = model.geo.addLine(p2, p3, tag=2)
        left = model.geo.addLine(p3, p0, tag=3)
        cloop1 = model.geo.addCurveLoop([bottom, right, top, left])
        # surface_1 =
        model.geo.addPlaneSurface([cloop1])

        model.geo.synchronize()
        surface_entities = [model[1] for model in model.getEntities(tdim)]
        model.addPhysicalGroup(tdim, surface_entities, tag=5)
        model.setPhysicalName(tdim, 5, "Rectangle surface")

        # Set mesh size via points
        # gmsh.model.mesh.setSize(points, lc)  # heuristic

        # gmsh.model.mesh.optimize("Netgen")

        # Set geometric order of mesh cells
        gmsh.model.mesh.setOrder(order)

        # Define physical groups for subdomains (! target tag > 0)
        # domain = 1
        # gmsh.model.addPhysicalGroup(tdim, [v[1] for v in volumes], domain)
        # gmsh.model.setPhysicalName(tdim, domain, 'domain')
        gmsh.model.addPhysicalGroup(tdim - 1, [3], tag=6)
        gmsh.model.setPhysicalName(tdim - 1, 6, "left")
        gmsh.model.addPhysicalGroup(tdim - 1, [1], tag=7)
        gmsh.model.setPhysicalName(tdim - 1, 7, "right")
        gmsh.model.addPhysicalGroup(tdim - 1, [2], tag=8)
        gmsh.model.setPhysicalName(tdim - 1, 8, "top")
        gmsh.model.addPhysicalGroup(tdim - 1, [0], tag=9)
        gmsh.model.setPhysicalName(tdim - 1, 9, "bottom")

        model.mesh.generate(tdim)

        # Optional: Write msh file
        if msh_file is not None:
            gmsh.write(msh_file)
            # gmsh.write(name + ".step")

    return gmsh.model if comm.rank == 0 else None, tdim


def mesh_circle_gmshapi(name,
                        R,
                        lc,
                        tdim,
                        order=1,
                        msh_file=None,
                        comm=MPI.COMM_WORLD):
    """
    Create 2d circle mesh using the Python API of Gmsh.
    """
    # Perform Gmsh work only on rank = 0

    if comm.rank == 0:
        import gmsh

        # Initialise gmsh and set options
        gmsh.initialize()
        gmsh.option.setNumber("General.Terminal", 1)

        gmsh.option.setNumber("Mesh.Algorithm", 6)
        model = gmsh.model()
        model.add("Circle")
        model.setCurrent("Circle")
        p0 = model.geo.addPoint(0.0, 0.0, 0, lc, tag=0)
        p1 = model.geo.addPoint(R, 0.0, 0, lc, tag=1)
        p2 = model.geo.addPoint(0.0, R, 0.0, lc, tag=2)
        p3 = model.geo.addPoint(-R, 0, 0, lc, tag=3)
        p4 = model.geo.addPoint(0, -R, 0, lc, tag=4)
        # points = [p0, p1, p2, p3]
        c1 = gmsh.model.geo.addCircleArc(p1, p0, p2)
        c2 = gmsh.model.geo.addCircleArc(p2, p0, p3)
        c3 = gmsh.model.geo.addCircleArc(p3, p0, p4)
        c4 = gmsh.model.geo.addCircleArc(p4, p0, p1)

        circle = model.geo.addCurveLoop([c1, c2, c3, c4])
        model.geo.addPlaneSurface([circle])

        model.geo.synchronize()
        surface_entities = [model[1] for model in model.getEntities(tdim)]
        model.addPhysicalGroup(tdim, surface_entities, tag=5)
        model.setPhysicalName(tdim, 5, "Film surface")

        gmsh.model.mesh.setOrder(order)

        model.mesh.generate(tdim)

        # Optional: Write msh file
        if msh_file is not None:
            gmsh.write(msh_file)

    return gmsh.model if comm.rank == 0 else None, tdim


if __name__ == "__main__":
    import sys

    sys.path.append("../../damage")
    from xdmf import XDMFFile
    from mesh import gmsh_to_dolfin

    # , merge_meshtags, locate_dofs_topological
    from mpi4py import MPI
    from pathlib import Path
    import dolfinx.plot

    gmsh_model, tdim = mesh_bar_gmshapi("bar",
                                        1,
                                        0.1,
                                        0.01,
                                        2,
                                        msh_file="output/bar.msh")
    mesh, mts = gmsh_to_dolfin(gmsh_model, tdim, prune_z=True)
    Path("output").mkdir(parents=True, exist_ok=True)
    with XDMFFile(MPI.COMM_WORLD, "output/bar.xdmf", "w") as ofile:
        ofile.write_mesh_meshtags(mesh, mts)

    import pyvista
    from pyvista.utilities import xvfb

    xvfb.start_xvfb(wait=0.05)
    pyvista.OFF_SCREEN = True
    plotter = pyvista.Plotter(title="Bar mesh")
    topology, cell_types = dolfinx.plot.create_vtk_topology(
        mesh, mesh.topology.dim)
    grid = pyvista.UnstructuredGrid(topology, cell_types, mesh.geometry.x)
    # plotter.subplot(0, 0)
    actor_1 = plotter.add_mesh(grid, show_edges=True)

    plotter.view_xy()
    if not pyvista.OFF_SCREEN:
        plotter.show()
    figure = plotter.screenshot("output/bar.png")
