import re
import galsim
import numpy
import lsst.afw.geom as afwGeom
from lsst.afw.cameraGeom import PUPIL, PIXELS, FOCAL_PLANE
from lsst.sims.utils import arcsecFromRadians, radiansFromArcsec
from lsst.sims.coordUtils import _raDecFromPixelCoords, \
    _pixelCoordsFromRaDec, \
    pixelCoordsFromPupilCoords
from lsst.sims.GalSimInterface.wcsUtils import tanSipWcsFromDetector

__all__ = ["GalSimDetector"]


class GalSim_afw_TanSipWCS(galsim.wcs.CelestialWCS):
    """
    This class uses methods from afw.geom and meas_astrom to
    fit a TAN-SIP WCS to an afw.cameraGeom.Detector and then wrap
    that WCS into something that GalSim can parse.

    For documentation on the TAN-SIP WCS see

    Shupe and Hook (2008)
    http://fits.gsfc.nasa.gov/registry/sip/SIP_distortion_v1_0.pdf
    """

    def __init__(self, afwDetector, afwCamera, obs_metadata, epoch, photParams=None, wcs=None):
        """
        @param [in] afwDetector is an instantiation of afw.cameraGeom.Detector

        @param [in] afwCamera is an instantiation of afw.cameraGeom.Camera

        @param [in] obs_metadata is an instantiation of ObservationMetaData
        characterizing the telescope pointing

        @param [in] epoch is the epoch in Julian years of the equinox against
        which RA and Dec are measured

        @param [in] photParams is an instantiation of PhotometricParameters
        (it will contain information about gain, exposure time, etc.)

        @param [in] wcs is a kwarg that is used by the method _newOrigin().
        The wcs kwarg in this constructor method should not be used by users.
        """

        if wcs is None:
            self._tanSipWcs = tanSipWcsFromDetector(afwDetector, afwCamera, obs_metadata, epoch)
        else:
            self._tanSipWcs = wcs

        self.afwDetector = afwDetector
        self.afwCamera = afwCamera
        self.obs_metadata = obs_metadata
        self.photParams = photParams
        self.epoch = epoch

        self.fitsHeader = self._tanSipWcs.getFitsMetadata()
        self.fitsHeader.set("EXTTYPE", "IMAGE")

        if self.obs_metadata.bandpass is not None:
            if not isinstance(self.obs_metadata.bandpass, list) and not isinstance(self.obs_metadata.bandpass, numpy.ndarray):
                self.fitsHeader.set("FILTER", self.obs_metadata.bandpass)

        if self.obs_metadata.mjd is not None:
            self.fitsHeader.set("MJD-OBS", self.obs_metadata.mjd.TAI)

        if self.photParams is not None:
            self.fitsHeader.set("EXPTIME", self.photParams.nexp*self.photParams.exptime)

        self.crpix1 = self.fitsHeader.get("CRPIX1")
        self.crpix2 = self.fitsHeader.get("CRPIX2")

        self.afw_crpix1 = self.crpix1
        self.afw_crpix2 = self.crpix2

        self.crval1 = self.fitsHeader.get("CRVAL1")
        self.crval2 = self.fitsHeader.get("CRVAL2")

        self.origin = galsim.PositionD(x=self.crpix1, y=self.crpix2)

    def _radec(self, x, y):
        """
        This is a method required by the GalSim WCS API

        Convert pixel coordinates into ra, dec coordinates.
        x and y already have crpix1 and crpix2 subtracted from them.
        Return ra, dec in radians.
        """

        chipNameList = [self.afwDetector.getName()]

        if type(x) is numpy.ndarray:
            chipNameList = chipNameList * len(x)

        ra, dec = _raDecFromPixelCoords(x + self.afw_crpix1, y + self.afw_crpix2, chipNameList,
                                        camera=self.afwCamera,
                                        obs_metadata=self.obs_metadata,
                                        epoch=self.epoch)

        if type(x) is numpy.ndarray:
            return (ra, dec)
        else:
            return (ra[0], dec[0])

    def _xy(self, ra, dec):
        """
        This is a method required by the GalSim WCS API

        Convert ra, dec in radians into x, y in pixel space with crpix subtracted.
        """

        chipNameList = [self.afwDetector.getName()]

        if type(ra) is numpy.ndarray:
            chipNameLIst = chipNameList * len(ra)

        xx, yy = calculatePixelCoordinates(ra=ra, dec=dec, chipNames=chipNameList,
                                           obs_metadata=self.obs_metadata,
                                           epoch=self.epoch,
                                           camera = self.afwCamera)

        if type(ra) is numpy.ndarray:
            return (xx-self.crpix1, yy-self.crpix2)
        else:
            return (xx[0]-self.crpix1, yy-self.crpix2)

    def _newOrigin(self, origin):
        """
        This is a method required by the GalSim WCS API.  It returns
        a copy of self, but with the pixel-space origin translated to a new
        position.

        @param [in] origin is an instantiation of a galsim.PositionD representing
        the a point in pixel space to which you want to move the origin of the WCS

        @param [out] _newWcs is a WCS identical to self, but with the origin
        in pixel space moved to the specified origin
        """
        _newWcs = GalSim_afw_TanSipWCS(self.afwDetector, self.afwCamera, self.obs_metadata, self.epoch,
                                       photParams=self.photParams, wcs=self._tanSipWcs)
        _newWcs.crpix1 = origin.x
        _newWcs.crpix2 = origin.y
        _newWcs.fitsHeader.set('CRPIX1', origin.x)
        _newWcs.fitsHeader.set('CRPIX2', origin.y)
        return _newWcs

    def _writeHeader(self, header, bounds):
        for key in self.fitsHeader.getOrderedNames():
            header[key] = self.fitsHeader.get(key)

        return header


class GalSimDetector(object):
    """
    This class stores information about individual detectors for use by the GalSimInterpreter
    """

    def __init__(self, afwDetector, afwCamera, obs_metadata, epoch, photParams=None):
        """
        @param [in] afwDetector is an instaniation of afw.cameraGeom.Detector

        @param [in] afwCamera is an instantiation of afw.cameraGeom.camera

        @param [in] photParams is an instantiation of the PhotometricParameters class that carries
        details about the photometric response of the telescope.

        This class will generate its own internal variable self.fileName which is
        the name of the detector as it will appear in the output FITS files
        """

        if photParams is None:
            raise RuntimeError("You need to specify an instantiation of PhotometricParameters " +
                               "when constructing a GalSimDetector")

        self._wcs = None  # this will be created when it is actually called for
        self._name = afwDetector.getName()
        self._afwDetector = afwDetector
        self._afwCamera = afwCamera
        self._obs_metadata = obs_metadata
        self._epoch = epoch

        bbox = afwDetector.getBBox()
        self._xMinPix = bbox.getMinX()
        self._xMaxPix = bbox.getMaxX()
        self._yMinPix = bbox.getMinY()
        self._yMaxPix = bbox.getMaxY()

        self._bbox = afwGeom.Box2D(bbox)

        pupilSystem = afwDetector.makeCameraSys(PUPIL)
        pixelSystem = afwDetector.makeCameraSys(PIXELS)

        centerPoint = afwDetector.getCenter(FOCAL_PLANE)
        centerPupil = afwCamera.transform(centerPoint, pupilSystem).getPoint()
        self._xCenterArcsec = arcsecFromRadians(centerPupil.getX())
        self._yCenterArcsec = arcsecFromRadians(centerPupil.getY())
        centerPixel = afwCamera.transform(centerPoint, pixelSystem).getPoint()
        self._xCenterPix = centerPixel.getX()
        self._yCenterPix = centerPixel.getY()

        self._xMinArcsec = None
        self._yMinArcsec = None
        self._xMaxArcsec = None
        self._yMaxArcsec = None
        cornerPointList = afwDetector.getCorners(FOCAL_PLANE)
        for cornerPoint in cornerPointList:
            cameraPoint = afwDetector.makeCameraPoint(cornerPoint, FOCAL_PLANE)
            cameraPointPupil = afwCamera.transform(cameraPoint, pupilSystem).getPoint()

            xx = arcsecFromRadians(cameraPointPupil.getX())
            yy = arcsecFromRadians(cameraPointPupil.getY())
            if self._xMinArcsec is None or xx < self._xMinArcsec:
                self._xMinArcsec = xx
            if self._xMaxArcsec is None or xx > self._xMaxArcsec:
                self._xMaxArcsec = xx
            if self._yMinArcsec is None or yy < self._yMinArcsec:
                self._yMinArcsec = yy
            if self._yMaxArcsec is None or yy > self._yMaxArcsec:
                self._yMaxArcsec = yy

        self._photParams = photParams
        self._fileName = self._getFileName()

    def _getFileName(self):
        """
        Format the name of the detector to add to the name of the FITS file
        """
        detectorName = self.name
        detectorName = detectorName.replace(',', '_')
        detectorName = detectorName.replace(':', '_')
        detectorName = detectorName.replace(' ', '_')

        name = detectorName
        return name

    def pixelCoordinatesFromRaDec(self, ra, dec):
        """
        Convert RA, Dec into pixel coordinates on this detector

        @param [in] ra is a numpy array or a float indicating RA in radians

        @param [in] dec is a numpy array or a float indicating Dec in radians

        @param [out] xPix is a numpy array indicating the x pixel coordinate

        @param [out] yPix is a numpy array indicating the y pixel coordinate
        """

        nameList = [self.name]
        if type(ra) is numpy.ndarray:
            nameList = nameList*len(ra)
            raLocal = ra
            decLocal = dec
        else:
            raLocal = numpy.array([ra])
            decLocal = numpy.array([dec])

        xPix, yPix = _pixelCoordsFromRaDec(raLocal, decLocal, chipNames=nameList,
                                           obs_metadata=self._obs_metadata,
                                           epoch=self._epoch,
                                           camera=self._afwCamera)

        return xPix, yPix

    def pixelCoordinatesFromPupilCoordinates(self, xPupil, yPupil):
        """
        Convert pupil coordinates into pixel coordinates on this detector

        @param [in] xPupil is a numpy array or a float indicating x pupil coordinates
        in radians

        @param [in] yPupil a numpy array or a float indicating y pupil coordinates
        in radians

        @param [out] xPix is a numpy array indicating the x pixel coordinate

        @param [out] yPix is a numpy array indicating the y pixel coordinate
        """

        nameList = [self._name]
        if type(xPupil) is numpy.ndarray:
            nameList = nameList*len(xPupil)
            xp = xPupil
            yp = yPupil
        else:
            xp = numpy.array([xPupil])
            yp = numpy.array([yPupil])

        xPix, yPix = pixelCoordsFromPupilCoords(xp, yp, chipNames=nameList,
                                                camera=self._afwCamera)

        return xPix, yPix

    def containsRaDec(self, ra, dec):
        """
        Does a given RA, Dec fall on this detector?

        @param [in] ra is a numpy array or a float indicating RA in radians

        @param [in] dec is a numpy array or a float indicating Dec in radians

        @param [out] answer is an array of booleans indicating whether or not
        the corresponding RA, Dec pair falls on this detector
        """

        xPix, yPix = self.pixelCoordinatesFromRaDec(ra, dec)
        points = [afwGeom.Point2D(xx, yy) for xx, yy in zip(xPix, yPix)]
        answer = [self._bbox.contains(pp) for pp in points]
        return answer

    def containsPupilCoordinates(self, xPupil, yPupil):
        """
        Does a given set of pupil coordinates fall on this detector?

        @param [in] xPupil is a numpy array or a float indicating x pupil coordinates
        in radians

        @param [in] yPupuil is a numpy array or a float indicating y pupil coordinates
        in radians

        @param [out] answer is an array of booleans indicating whether or not
        the corresponding RA, Dec pair falls on this detector
        """
        xPix, yPix = self.pixelCoordinatesFromPupilCoordinates(xPupil, yPupil)
        points = [afwGeom.Point2D(xx, yy) for xx, yy in zip(xPix, yPix)]
        answer = [self._bbox.contains(pp) for pp in points]
        return answer

    @property
    def xMinPix(self):
        """Minimum x pixel coordinate of the detector"""
        return self._xMinPix

    @xMinPix.setter
    def xMinPix(self, value):
        raise RuntimeError("You should not be setting xMinPix on the fly; "
                           + "just instantiate a new GalSimDetector")

    @property
    def xMaxPix(self):
        """Maximum x pixel coordinate of the detector"""
        return self._xMaxPix

    @xMaxPix.setter
    def xMaxPix(self, value):
        raise RuntimeError("You should not be setting xMaxPix on the fly; "
                           + "just instantiate a new GalSimDetector")

    @property
    def yMinPix(self):
        """Minimum y pixel coordinate of the detector"""
        return self._yMinPix

    @yMinPix.setter
    def yMinPix(self, value):
        raise RuntimeError("You should not be setting yMinPix on the fly; "
                           + "just instantiate a new GalSimDetector")

    @property
    def yMaxPix(self):
        """Maximum y pixel coordinate of the detector"""
        return self._yMaxPix

    @yMaxPix.setter
    def yMaxPix(self, value):
        raise RuntimeError("You should not be setting yMaxPix on the fly; "
                           + "just instantiate a new GalSimDetector")

    @property
    def xCenterPix(self):
        """Center x pixel coordinate of the detector"""
        return self._xCenterPix

    @xCenterPix.setter
    def xCenterPix(self, value):
        raise RuntimeError("You should not be setting xCenterPix on the fly; "
                           + "just instantiate a new GalSimDetector")

    @property
    def yCenterPix(self):
        """Center y pixel coordinate of the detector"""
        return self._yCenterPix

    @yCenterPix.setter
    def yCenterPix(self, value):
        raise RuntimeError("You should not be setting yCenterPix on the fly; "
                           + "just instantiate a new GalSimDetector")

    @property
    def xMaxArcsec(self):
        """Maximum x pupil coordinate of the detector in arcseconds"""
        return self._xMaxArcsec

    @xMaxArcsec.setter
    def xMaxArcsec(self, value):
        raise RuntimeError("You should not be setting xMaxArcsec on the fly; "
                           + "just instantiate a new GalSimDetector")

    @property
    def xMinArcsec(self):
        """Minimum x pupil coordinate of the detector in arcseconds"""
        return self._xMinArcsec

    @xMinArcsec.setter
    def xMinArcsec(self, value):
        raise RuntimeError("You should not be setting xMinArcsec on the fly; "
                           + "just instantiate a new GalSimDetector")

    @property
    def yMaxArcsec(self):
        """Maximum y pupil coordinate of the detector in arcseconds"""
        return self._yMaxArcsec

    @yMaxArcsec.setter
    def yMaxArcsec(self, value):
        raise RuntimeError("You should not be setting yMaxArcsec on the fly; "
                           + "just instantiate a new GalSimDetector")

    @property
    def yMinArcsec(self):
        """Minimum y pupil coordinate of the detector in arcseconds"""
        return self._yMinArcsec

    @yMinArcsec.setter
    def yMinArcsec(self, value):
        raise RuntimeError("You should not be setting yMinArcsec on the fly; "
                           + "just instantiate a new GalSimDetector")

    @property
    def xCenterArcsec(self):
        """Center x pupil coordinate of the detector in arcseconds"""
        return self._xCenterArcsec

    @xCenterArcsec.setter
    def xCenterArcsec(self, value):
        raise RuntimeError("You should not be setting xCenterArcsec on the fly; "
                           + "just instantiate a new GalSimDetector")

    @property
    def yCenterArcsec(self):
        """Center y pupil coordinate of the detector in arcseconds"""
        return self._yCenterArcsec

    @yCenterArcsec.setter
    def yCenterArcsec(self, value):
        raise RuntimeError("You should not be setting yCenterArcsec on the fly; "
                           + "just instantiate a new GalSimDetector")

    @property
    def epoch(self):
        """Epoch of the equinox against which RA and Dec are measured in Julian years"""
        return self._epoch

    @epoch.setter
    def epoch(self, value):
        raise RuntimeError("You should not be setting epoch on the fly; "
                           + "just instantiate a new GalSimDetector")

    @property
    def obs_metadata(self):
        """ObservationMetaData instantiation describing the telescope pointing"""
        return self._obs_metadata

    @obs_metadata.setter
    def obs_metadata(self, value):
        raise RuntimeError("You should not be setting obs_metadata on the fly; "
                           + "just instantiate a new GalSimDetector")

    @property
    def name(self):
        """Name of the detector"""
        return self._name

    @name.setter
    def name(self, value):
        raise RuntimeError("You should not be setting name on the fly; "
                           + "just instantiate a new GalSimDetector")

    @property
    def photParams(self):
        """PhotometricParameters instantiation characterizing the detector"""
        return self._photParams

    @photParams.setter
    def photParams(self, value):
        raise RuntimeError("You should not be setting photParams on the fly; "
                           + "just instantiate a new GalSimDetector")

    @property
    def fileName(self):
        """Name of the FITS file corresponding to this detector"""
        return self._fileName

    @fileName.setter
    def fileName(self, value):
        raise RuntimeError("You should not be setting fileName on the fly; "
                           + "just instantiate a new GalSimDetector")

    @property
    def afwCamera(self):
        """afw.cameraGeom.Camera instantiation corresponding to this detector"""
        return self._afwCamera

    @afwCamera.setter
    def afwCamera(self, value):
        raise RuntimeError("You should not be setting afwCamera on the fly; "
                           + "just instantiate a new GalSimDetector")

    @property
    def afwDetector(self):
        """afw.cameraGeom.Detector instantiation corresponding to this detector"""
        return self._afwDetector

    @afwDetector.setter
    def afwDetector(self, value):
        raise RuntimeError("You should not be setting afwDetector on the fly; "
                           + "just instantiate a new GalSimDetector")

    @property
    def wcs(self):
        """WCS corresponding to this detector"""
        if self._wcs is None:
            self._wcs = GalSim_afw_TanSipWCS(self.afwDetector, self.afwCamera,
                                             self.obs_metadata, self.epoch,
                                             photParams=self.photParams)

            if re.match('R_[0-9]_[0-9]_S_[0-9]_[0-9]', self.fileName) is not None:
                # This is an LSST camera; format the FITS header to feed through DM code

                wcsName = self.fileName.replace('_', '')
                wcsName = wcsName.replace('S', '_S')

                self._wcs.fitsHeader.set("CHIPID", wcsName)

                obshistid = 9999

                if self.obs_metadata.phoSimMetaData is not None:
                    if 'Opsim_obshistid' in self.obs_metadata.phoSimMetaData:
                        self._wcs.fitsHeader.set("OBSID", self.obs_metadata.phoSimMetaData[
                                                 'Opsim_obshistid'][0])
                        obshistid = self.obs_metadata.phoSimMetaData['Opsim_obshistid'][0]

                bp = self.obs_metadata.bandpass
                if not isinstance(bp, list) and not isinstance(bp, numpy.ndarray):
                    filt_num = {'u': 0, 'g': 1, 'r': 2, 'i': 3, 'z': 4, 'y': 5}[bp]
                else:
                    filt_num = 2

                out_name = 'lsst_e_%d_f%d_%s_E000' % (obshistid, filt_num, wcsName)
                self._wcs.fitsHeader.set("OUTFILE", out_name)

        return self._wcs

    @wcs.setter
    def wcs(self, value):
        raise RuntimeError("You should not be setting wcs on the fly; "
                           + "just instantiate a new GalSimDetector")

