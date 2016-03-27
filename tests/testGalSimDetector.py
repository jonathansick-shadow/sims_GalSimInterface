import unittest
import os
import numpy
from lsst.utils import getPackageDir
import lsst.utils.tests as utilsTests

from lsst.sims.utils import ObservationMetaData
from lsst.sims.photUtils import PhotometricParameters
from lsst.sims.coordUtils.utils import ReturnCamera
from lsst.sims.coordUtils import _raDecFromPixelCoords, \
    pupilCoordsFromPixelCoords
from lsst.sims.GalSimInterface import GalSimDetector


class GalSimDetectorTest(unittest.TestCase):

    def setUp(self):
        baseDir = os.path.join(getPackageDir('sims_GalSimInterface'),
                               'tests', 'cameraData')

        self.camera = ReturnCamera(baseDir)

        ra = 145.0
        dec = -73.0
        self.epoch = 2000.0
        mjd = 49250.0
        rotSkyPos = 45.0
        self.obs = ObservationMetaData(pointingRA=ra,
                                       pointingDec=dec,
                                       boundType='circle',
                                       boundLength=1.0,
                                       mjd=mjd,
                                       rotSkyPos=rotSkyPos)

    def testContainsRaDec(self):
        """
        Test whether or not the method containsRaDec correctly identifies
        RA and Dec that fall inside and outside the detector
        """

        photParams = PhotometricParameters()
        gsdet = GalSimDetector(self.camera[0], self.camera,
                               self.obs, self.epoch,
                               photParams=photParams)

        xxList = [gsdet.xMinPix, gsdet.xMaxPix]
        yyList = [gsdet.yMinPix, gsdet.yMaxPix]
        dxList = [-1.0, 1.0]
        dyList = [-1.0, 1.0]

        xPixList = []
        yPixList = []
        correctAnswer = []

        for xx, yy, dx, dy in zip(xxList, yyList, dxList, dyList):
            xPixList.append(xx)
            yPixList.append(yy)
            correctAnswer.append(True)

            xPixList.append(xx+dx)
            yPixList.append(yy)
            correctAnswer.append(False)

            xPixList.append(xx)
            yPixList.append(yy+dy)
            correctAnswer.append(False)

        nameList = [gsdet.name]*len(xPixList)
        xPixList = numpy.array(xPixList)
        yPixList = numpy.array(yPixList)

        raList, decList = _raDecFromPixelCoords(xPixList, yPixList,
                                                nameList,
                                                camera=self.camera,
                                                obs_metadata=self.obs,
                                                epoch=self.epoch)

        testAnswer = gsdet.containsRaDec(raList, decList)

        for c, t in zip(correctAnswer, testAnswer):
            self.assertIs(c, t)

    def testContainsPupilCoordinates(self):
        """
        Test whether or not the method containsRaDec correctly identifies
        RA and Dec that fall inside and outside the detector
        """

        photParams = PhotometricParameters()
        gsdet = GalSimDetector(self.camera[0], self.camera,
                               self.obs, self.epoch,
                               photParams=photParams)

        xxList = [gsdet.xMinPix, gsdet.xMaxPix]
        yyList = [gsdet.yMinPix, gsdet.yMaxPix]
        dxList = [-1.0, 1.0]
        dyList = [-1.0, 1.0]

        xPixList = []
        yPixList = []
        correctAnswer = []

        for xx, yy, dx, dy in zip(xxList, yyList, dxList, dyList):
            xPixList.append(xx)
            yPixList.append(yy)
            correctAnswer.append(True)

            xPixList.append(xx+dx)
            yPixList.append(yy)
            correctAnswer.append(False)

            xPixList.append(xx)
            yPixList.append(yy+dy)
            correctAnswer.append(False)

        nameList = [gsdet.name]*len(xPixList)
        xPixList = numpy.array(xPixList)
        yPixList = numpy.array(yPixList)

        xPupilList, yPupilList = \
            pupilCoordsFromPixelCoords(xPixList, yPixList,
                                       nameList,
                                       camera=self.camera)

        testAnswer = gsdet.containsPupilCoordinates(xPupilList, yPupilList)

        for c, t in zip(correctAnswer, testAnswer):
            self.assertIs(c, t)


def suite():
    utilsTests.init()
    suites = []
    suites += unittest.makeSuite(GalSimDetectorTest)

    return unittest.TestSuite(suites)


def run(shouldExit = False):
    utilsTests.run(suite(), shouldExit)
if __name__ == "__main__":
    run(True)
