import numpy
import os
import unittest
import lsst.utils.tests as utilsTests
from lsst.utils import getPackageDir
import lsst.afw.image as afwImage
from lsst.sims.utils import ObservationMetaData, radiansFromArcsec, arcsecFromRadians
from lsst.sims.utils import haversine, arcsecFromRadians
from lsst.sims.catalogs.generation.db import fileDBObject
from lsst.sims.GalSimInterface import GalSimStars, GalSimDetector, SNRdocumentPSF
from lsst.sims.coordUtils import _raDecFromPixelCoords

from lsst.sims.coordUtils.utils import ReturnCamera

from testUtils import create_text_catalog


class fwhmFileDBObj(fileDBObject):
    idColKey = 'test_id'
    objectTypeId = 88
    tableid = 'test'
    raColName = 'ra'
    decColName = 'dec'
    # sedFilename

    columns = [('raJ2000', 'ra*PI()/180.0', numpy.float),
               ('decJ2000', 'dec*PI()/180.0', numpy.float),
               ('magNorm', 'mag_norm', numpy.float)]


class fwhmCat(GalSimStars):
    camera = ReturnCamera(os.path.join(getPackageDir('sims_GalSimInterface'), 'tests', 'cameraData'))
    bandpassNames = ['u']

    default_columns = GalSimStars.default_columns

    default_columns += [('sedFilename', 'sed_flat.txt', (str, 12)),
                        ('properMotionRa', 0.0, numpy.float),
                        ('properMotionDec', 0.0, numpy.float),
                        ('radialVelocity', 0.0, numpy.float),
                        ('parallax', 0.0, numpy.float),
                        ]


class GalSimFwhmTest(unittest.TestCase):

    def verify_fwhm(self, fileName, fwhm, detector, camera, obs, epoch=2000.0):
        """
        Read in a FITS image with one object on it and verify that that object
        has the expected Full Width at Half Maximum.  This is done by finding
        the brightest pixel in the image, and then drawing 1-dimensional profiles
        of the object centered on that pixel (but at different angles relative to
        the axes of the image).  The code then walks along those profiles and keeps
        track of the distance between the two points at which the flux is half of
        the maximum.

        @param [in] fileName is the name of the FITS image

        @param [in] fwhm is the expected Full Width at Half Maximum in arcseconds

        @param [in] detector is an instantiation of the afw.cameraGeom Detector
        class characterizing the detector corresponding to this image

        @param [in] camera is an instantiation of the afw.cameraGeom Camera class
        characterizing the camera to which detector belongs

        @param [in] obs is an instantiation of ObservationMetaData characterizing
        the telescope pointing

        @param [in] epoch is the epoch in Julian years of the equinox against which
        RA and Dec are measured.

        This method will raise an exception if the measured Full Width at Half Maximum
        deviates from the expected value by more than ten percent.
        """
        im = afwImage.ImageF(fileName).getArray()
        maxFlux = im.max()
        self.assertGreater(maxFlux, 100.0)  # make sure the image is not blank

        # this looks backwards, but remember: the way numpy handles
        # arrays, the first index indicates what row it is in (the y coordinate)
        _maxPixel = numpy.array([im.argmax()/im.shape[1], im.argmax()%im.shape[1]])
        maxPixel = numpy.array([_maxPixel[1], _maxPixel[0]])

        raMax, decMax = _raDecFromPixelCoords(maxPixel[:1],
                                              maxPixel[1:2],
                                              [detector.getName()],
                                              camera=camera,
                                              obs_metadata=obs,
                                              epoch=epoch)

        half_flux = 0.5*maxFlux

        # only need to consider orientations between 0 and pi because the objects
        # will be circularly symmetric (and FWHM is a circularly symmetric measure, anyway)
        for theta in numpy.arange(0.0, numpy.pi, 0.3*numpy.pi):

            slope = numpy.tan(theta)

            if numpy.abs(slope < 1.0):
                xPixList = numpy.array([ix for ix in range(0, im.shape[1])
                                        if int(slope*(ix-maxPixel[0]) + maxPixel[1]) >= 0 and
                                        int(slope*(ix-maxPixel[0])+maxPixel[1]) < im.shape[0]])

                yPixList = numpy.array([int(slope*(ix-maxPixel[0])+maxPixel[1]) for ix in xPixList])
            else:
                yPixList = numpy.array([iy for iy in range(0, im.shape[0])
                                        if int((iy-maxPixel[1])/slope + maxPixel[0]) >= 0 and
                                        int((iy-maxPixel[1])/slope + maxPixel[0]) < im.shape[1]])

                xPixList = numpy.array([int((iy-maxPixel[1])/slope + maxPixel[0]) for iy in yPixList])

            chipNameList = [detector.getName()]*len(xPixList)
            raList, decList = _raDecFromPixelCoords(xPixList, yPixList, chipNameList,
                                                    camera=camera, obs_metadata=obs, epoch=epoch)

            distanceList = arcsecFromRadians(haversine(raList, decList, raMax[0], decMax[0]))

            fluxList = numpy.array([im[iy][ix] for ix, iy in zip(xPixList, yPixList)])

            distanceToLeft = None
            distanceToRight = None

            for ix in range(1, len(xPixList)):
                if fluxList[ix] < half_flux and fluxList[ix+1] >= half_flux:
                    break

            newOrigin = ix+1

            mm = (distanceList[ix]-distanceList[ix+1])/(fluxList[ix]-fluxList[ix+1])
            bb = distanceList[ix] - mm * fluxList[ix]
            distanceToLeft = mm*half_flux + bb

            for ix in range(newOrigin, len(xPixList)-1):
                if fluxList[ix] >= half_flux and fluxList[ix+1] < half_flux:
                    break

            mm = (distanceList[ix]-distanceList[ix+1])/(fluxList[ix]-fluxList[ix+1])
            bb = distanceList[ix] - mm * fluxList[ix]
            distanceToRight = mm*half_flux + bb

            msg = "measured fwhm %e; expected fwhm %e; maxFlux %e\n" % \
                (distanceToLeft+distanceToRight, fwhm, maxFlux)

            self.assertLess(numpy.abs(distanceToLeft+distanceToRight-fwhm), 0.1*fwhm, msg=msg)

    def testFwhmOfImage(self):
        """
        Test that GalSim generates images with the expected Full Width at Half Maximum.
        """
        scratchDir = os.path.join(getPackageDir('sims_GalSimInterface'), 'tests', 'scratchSpace')
        catName = os.path.join(scratchDir, 'fwhm_test_Catalog.dat')
        imageRoot = os.path.join(scratchDir, 'fwhm_test_Image')
        dbFileName = os.path.join(scratchDir, 'fwhm_test_InputCatalog.dat')

        baseDir = os.path.join(getPackageDir('sims_GalSimInterface'), 'tests', 'cameraData')
        camera = ReturnCamera(baseDir)

        detector = camera[0]
        detName = detector.getName()
        imageName = '%s_%s_u.fits' % (imageRoot, detName)

        obs = ObservationMetaData(pointingRA = 75.0,
                                  pointingDec = -12.0,
                                  boundType = 'circle',
                                  boundLength = 4.0,
                                  rotSkyPos = 33.0,
                                  mjd = 49250.0)

        create_text_catalog(obs, dbFileName, numpy.array([3.0]),
                            numpy.array([1.0]), mag_norm=[13.0])

        db = fwhmFileDBObj(dbFileName, runtable='test')

        for fwhm in (0.5, 1.3):

            cat = fwhmCat(db, obs_metadata=obs)
            cat.camera = camera

            psf = SNRdocumentPSF(fwhm=fwhm)
            cat.setPSF(psf)

            cat.write_catalog(catName)
            cat.write_images(nameRoot=imageRoot)

            self.verify_fwhm(imageName, fwhm, detector, camera, obs)

            if os.path.exists(catName):
                os.unlink(catName)

            if os.path.exists(imageName):
                os.unlink(imageName)

        if os.path.exists(dbFileName):
            os.unlink(dbFileName)


def suite():
    utilsTests.init()
    suites = []
    suites += unittest.makeSuite(GalSimFwhmTest)

    return unittest.TestSuite(suites)


def run(shouldExit = False):
    utilsTests.run(suite(), shouldExit)
if __name__ == "__main__":
    run(True)
