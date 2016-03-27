#
# LSST Data Management System
# Copyright 2008, 2009, 2010 LSST Corporation.
#
# This product includes software developed by the
# LSST Project (http://www.lsst.org/).
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the LSST License Statement and
# the GNU General Public License along with this program.  If not,
# see <http://www.lsstcorp.org/LegalNotices/>.
#

"""
2015 December 10:
This is a modified version of the approximateWcs.py script from
meas_astrom
"""

import numpy as np
import lsst.afw.image as afwImage
import lsst.afw.table as afwTable
import lsst.afw.geom as afwGeom
import lsst.afw.coord as afwCoord
from lsst.meas.base import SingleFrameMeasurementTask
from lsst.meas.astrom.sip import makeCreateWcsWithSip
from lsst.afw.image.basicUtils import assertWcsNearlyEqualOverBBox
from lsst.sims.coordUtils import raDecFromPixelCoords

__all__ = ["approximateWcs"]


def approximateWcs(wcs, bbox, camera=None, detector=None, obs_metadata=None,
                   order=3, nx=20, ny=20, iterations=3,
                   skyTolerance=0.001*afwGeom.arcseconds, pixelTolerance=0.02,
                   useTanWcs=False):
    """Approximate an existing WCS as a TAN-SIP WCS

    The fit is performed by evaluating the WCS at a uniform grid of points within a bounding box.

    @param[in] wcs  wcs to approximate
    @param[in] bbox  the region over which the WCS will be fit
    @param[in] camera is an instantiation of afw.cameraGeom.camera
    @param[in] detector is a detector from camera
    @param[in] obs_metadata is an ObservationMetaData characterizing the telescope pointing
    @param[in] order  order of SIP fit
    @param[in] nx  number of grid points along x
    @param[in] ny  number of grid points along y
    @param[in] iterations number of times to iterate over fitting
    @param[in] skyTolerance maximum allowed difference in world coordinates between
               input wcs and approximate wcs (default is 0.001 arcsec)
    @param[in] pixelTolerance maximum allowed difference in pixel coordinates between
               input wcs and approximate wcs (default is 0.02 pixels)
    @param[in] useTanWcs  send a TAN version of wcs to the fitter? It is documented to require that,
        but I don't think the fitter actually cares
    @return the fit TAN-SIP WCS
    """
    if useTanWcs:
        crCoord = wcs.getSkyOrigin()
        crPix = wcs.getPixelOrigin()
        cdMat = wcs.getCDMatrix()
        tanWcs = afwImage.makeWcs(crCoord, crPix, cdMat[0, 0], cdMat[0, 1], cdMat[1, 0], cdMat[1, 1])
    else:
        tanWcs = wcs

    # create a matchList consisting of a grid of points covering the bbox
    refSchema = afwTable.SimpleTable.makeMinimalSchema()
    refCoordKey = afwTable.CoordKey(refSchema["coord"])
    refCat = afwTable.SimpleCatalog(refSchema)

    sourceSchema = afwTable.SourceTable.makeMinimalSchema()
    SingleFrameMeasurementTask(schema=sourceSchema)  # expand the schema
    sourceCentroidKey = afwTable.Point2DKey(sourceSchema["slot_Centroid"])

    sourceCat = afwTable.SourceCatalog(sourceSchema)

    matchList = afwTable.ReferenceMatchVector()

    bboxd = afwGeom.Box2D(bbox)
    for x in np.linspace(bboxd.getMinX(), bboxd.getMaxX(), nx):
        for y in np.linspace(bboxd.getMinY(), bboxd.getMaxY(), ny):
            pixelPos = afwGeom.Point2D(x, y)

            ra, dec = raDecFromPixelCoords(np.array([x]), np.array([y]),
                                           [detector.getName()],
                                           camera=camera,
                                           obs_metadata=obs_metadata,
                                           epoch=2000.0,
                                           includeDistortion=True)

            skyCoord = afwCoord.Coord(afwGeom.Point2D(ra[0], dec[0]))

            refObj = refCat.addNew()
            refObj.set(refCoordKey, skyCoord)

            source = sourceCat.addNew()
            source.set(sourceCentroidKey, pixelPos)

            matchList.append(afwTable.ReferenceMatch(refObj, source, 0.0))

    # The TAN-SIP fitter is fitting x and y separately, so we have to iterate to make it converge
    for indx in range(iterations):
        sipObject = makeCreateWcsWithSip(matchList, tanWcs, order, bbox)
        tanWcs = sipObject.getNewWcs()
    fitWcs = sipObject.getNewWcs()

    return fitWcs
