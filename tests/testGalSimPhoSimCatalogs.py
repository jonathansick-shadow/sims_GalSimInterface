from __future__ import with_statement
import os
import numpy as np
import unittest
import lsst.utils.tests as utilsTests

from lsst.utils import getPackageDir
from lsst.sims.utils import ObservationMetaData, radiansFromArcsec
from lsst.sims.catalogs.generation.db import fileDBObject
from lsst.sims.GalSimInterface import GalSimPhoSimGalaxies, GalSimPhoSimStars, GalSimPhoSimAgn
from lsst.sims.GalSimInterface import SNRdocumentPSF
from lsst.sims.catUtils.exampleCatalogDefinitions import PhoSimCatalogSersic2D, PhoSimCatalogPoint, PhoSimCatalogZPoint
from lsst.obs.lsstSim import LsstSimMapper



class GalSimPhoSimTest(unittest.TestCase):
    """
    Class to test that GalSimPhoSim catalogs produce both GalSim images
    and PhoSim-ready InstanceCatalogs
    """

    @classmethod
    def setUpClass(cls):
        cls.dataDir = os.path.join(getPackageDir('sims_GalSimInterface'),
                                   'tests', 'scratchSpace')
        cls.n_objects = 5
        np.random.seed(45)
        pointingRA = 45.2
        pointingDec = -31.6
        phoSimMetaData = {'pointingRA': (np.radians(pointingRA), np.dtype(np.float)),
                          'pointingDec': (np.radians(pointingDec), np.dtype(np.float)),
                          'Opsim_rotskypos': (1.2, np.dtype(np.float)),
                          'Opsim_filter': ('r', np.dtype(str)),
                          'Opsim_expmjd': (57341.6, np.dtype(np.float))
                          }
        cls.obs = ObservationMetaData(phoSimMetaData=phoSimMetaData,
                                      boundLength=0.1, boundType='circle')

        cls.dtype = np.dtype([('id', int),
                              ('raJ2000', np.float),
                              ('decJ2000', np.float),
                              ('ra_deg', np.float),
                              ('dec_deg', np.float),
                              ('sedFilename', (str, 300)),
                              ('magNorm', np.float),
                              ('redshift', np.float),
                              ('majorAxis', np.float),
                              ('minorAxis', np.float),
                              ('positionAngle', np.float),
                              ('halfLightRadius', np.float),
                              ('sindex', np.float),
                              ('internalAv', np.float),
                              ('internalRv', np.float),
                              ('galacticAv', np.float),
                              ('galacticRv', np.float),
                              ('properMotionRa', np.float),
                              ('properMotionDec', np.float),
                              ('radialVelocity', np.float),
                              ('parallax', np.float)])

        # generate some galaxy bulge data
        redshift = np.random.random_sample(cls.n_objects)*1.5
        rr = np.random.random_sample(cls.n_objects)*0.05
        theta = np.random.random_sample(cls.n_objects)*2.0*np.pi
        ra = np.radians(pointingRA + rr*np.cos(theta))
        dec = np.radians(pointingDec + rr*np.sin(theta))
        magNorm = np.random.random_sample(cls.n_objects)*7.0 + 18.0
        sindex = np.random.random_sample(cls.n_objects)*4.0+1.0
        hlr = radiansFromArcsec(np.random.random_sample(cls.n_objects)*10.0 + 1.0)
        positionAngle = np.random.random_sample(cls.n_objects)*np.pi
        internalAv = np.random.random_sample(cls.n_objects)*0.5+0.1
        internalRv = np.random.random_sample(cls.n_objects)*0.5+2.7
        majorAxis = radiansFromArcsec(np.random.random_sample(cls.n_objects)*2.0 + 0.5)
        minorAxis = radiansFromArcsec(np.random.random_sample(cls.n_objects)*2.0 + 0.5)
        galacticAv = np.random.random_sample(cls.n_objects)*0.5+0.1
        galacticRv = np.random.random_sample(cls.n_objects)*0.5+2.7
        properMotionRa = np.zeros(cls.n_objects)
        properMotionDec = np.zeros(cls.n_objects)
        radialVelocity = np.zeros(cls.n_objects)
        parallax = np.zeros(cls.n_objects)
        cls.bulge_name = os.path.join(cls.dataDir, 'galSimPhoSim_test_bulge.dat')
        with open(cls.bulge_name, 'w') as output_file:
            output_file.write('# header\n')
            for ix in range(cls.n_objects):
                output_file.write('%d %f %f %f %f Const.79E06.002Z.spec %f %f %f %f %f %f %f %f %f %f %f %f %f %f %f\n' %
                                  (ix, ra[ix], dec[ix], np.degrees(ra[ix]), np.degrees(dec[ix]),
                                  magNorm[ix], redshift[ix],
                                  max(majorAxis[ix], minorAxis[ix]), min(majorAxis[ix], minorAxis[ix]),
                                  positionAngle[ix], hlr[ix], sindex[ix], internalAv[ix], internalRv[ix],
                                  galacticAv[ix], galacticRv[ix],
                                  properMotionRa[ix], properMotionDec[ix], radialVelocity[ix], parallax[ix]))


        # generate some galaxy disk data
        redshift = np.random.random_sample(cls.n_objects)*1.5
        rr = np.random.random_sample(cls.n_objects)*0.05
        theta = np.random.random_sample(cls.n_objects)*2.0*np.pi
        ra = np.radians(pointingRA + rr*np.cos(theta))
        dec = np.radians(pointingDec + rr*np.sin(theta))
        magNorm = np.random.random_sample(cls.n_objects)*7.0 + 18.0
        sindex = np.random.random_sample(cls.n_objects)*4.0+1.0
        hlr = radiansFromArcsec(np.random.random_sample(cls.n_objects)*10.0 + 1.0)
        positionAngle = np.random.random_sample(cls.n_objects)*np.pi
        internalAv = np.random.random_sample(cls.n_objects)*0.5+0.1
        internalRv = np.random.random_sample(cls.n_objects)*0.5+2.7
        majorAxis = radiansFromArcsec(np.random.random_sample(cls.n_objects)*2.0 + 0.5)
        minorAxis = radiansFromArcsec(np.random.random_sample(cls.n_objects)*2.0 + 0.5)
        galacticAv = np.random.random_sample(cls.n_objects)*0.5+0.1
        galacticRv = np.random.random_sample(cls.n_objects)*0.5+2.7
        properMotionRa = np.zeros(cls.n_objects)
        properMotionDec = np.zeros(cls.n_objects)
        radialVelocity = np.zeros(cls.n_objects)
        parallax = np.zeros(cls.n_objects)
        cls.disk_name = os.path.join(cls.dataDir, 'galSimPhoSim_test_disk.dat')
        with open(cls.disk_name, 'w') as output_file:
            output_file.write('# header\n')
            for ix in range(cls.n_objects):
                output_file.write('%d %f %f %f %f Inst.79E06.02Z.spec %f %f %f %f %f %f %f %f %f %f %f %f %f %f %f\n' %
                                  (ix, ra[ix], dec[ix], np.degrees(ra[ix]), np.degrees(dec[ix]),
                                  magNorm[ix], redshift[ix],
                                  max(majorAxis[ix], minorAxis[ix]), min(majorAxis[ix], minorAxis[ix]),
                                  positionAngle[ix], hlr[ix], sindex[ix], internalAv[ix], internalRv[ix],
                                  galacticAv[ix], galacticRv[ix],
                                  properMotionRa[ix], properMotionDec[ix], radialVelocity[ix], parallax[ix]))


        # generate some agn data
        redshift = np.random.random_sample(cls.n_objects)*1.5
        rr = np.random.random_sample(cls.n_objects)*0.05
        theta = np.random.random_sample(cls.n_objects)*2.0*np.pi
        ra = np.radians(pointingRA + rr*np.cos(theta))
        dec = np.radians(pointingDec + rr*np.sin(theta))
        magNorm = np.random.random_sample(cls.n_objects)*7.0 + 18.0
        sindex = np.zeros(cls.n_objects)
        hlr = np.zeros(cls.n_objects)
        positionAngle = np.zeros(cls.n_objects)
        internalAv = np.zeros(cls.n_objects)
        internalRv = np.zeros(cls.n_objects)
        majorAxis = np.zeros(cls.n_objects)
        minorAxis = np.zeros(cls.n_objects)
        galacticAv = np.random.random_sample(cls.n_objects)*0.5+0.1
        galacticRv = np.random.random_sample(cls.n_objects)*0.5+2.7
        properMotionRa = np.zeros(cls.n_objects)
        properMotionDec = np.zeros(cls.n_objects)
        radialVelocity = np.zeros(cls.n_objects)
        parallax = np.zeros(cls.n_objects)
        cls.agn_name = os.path.join(cls.dataDir, 'galSimPhoSim_test_agn.dat')
        with open(cls.agn_name, 'w') as output_file:
            output_file.write('# header\n')
            for ix in range(cls.n_objects):
                output_file.write('%d %f %f %f %f agn.spec %f %f %f %f %f %f %f %f %f %f %f %f %f %f %f\n' %
                                  (ix, ra[ix], dec[ix], np.degrees(ra[ix]), np.degrees(dec[ix]),
                                  magNorm[ix], redshift[ix],
                                  max(majorAxis[ix], minorAxis[ix]), min(majorAxis[ix], minorAxis[ix]),
                                  positionAngle[ix], hlr[ix], sindex[ix], internalAv[ix], internalRv[ix],
                                  galacticAv[ix], galacticRv[ix],
                                  properMotionRa[ix], properMotionDec[ix], radialVelocity[ix], parallax[ix]))

        # generate some star data
        redshift = np.random.random_sample(cls.n_objects)*1.5
        rr = np.random.random_sample(cls.n_objects)*0.05
        theta = np.random.random_sample(cls.n_objects)*2.0*np.pi
        ra = np.radians(pointingRA + rr*np.cos(theta))
        dec = np.radians(pointingDec + rr*np.sin(theta))
        magNorm = np.random.random_sample(cls.n_objects)*7.0 + 18.0
        sindex = np.zeros(cls.n_objects)
        hlr = np.zeros(cls.n_objects)
        positionAngle = np.zeros(cls.n_objects)
        internalAv = np.zeros(cls.n_objects)
        internalRv = np.zeros(cls.n_objects)
        majorAxis = np.zeros(cls.n_objects)
        minorAxis = np.zeros(cls.n_objects)
        galacticAv = np.random.random_sample(cls.n_objects)*0.5+0.1
        galacticRv = np.random.random_sample(cls.n_objects)*0.5+2.7
        properMotionRa = radiansFromArcsec(np.random.random_sample(cls.n_objects)*0.0002)
        properMotionDec = radiansFromArcsec(np.random.random_sample(cls.n_objects)*0.0002)
        radialVelocity = np.random.random_sample(cls.n_objects)*200.0
        parallax = radiansFromArcsec(np.random.random_sample(cls.n_objects)*0.0002)
        cls.star_name = os.path.join(cls.dataDir, 'galSimPhoSim_test_star.dat')
        with open(cls.star_name, 'w') as output_file:
            output_file.write('# header\n')
            for ix in range(cls.n_objects):
                output_file.write('%d %f %f %f %f km30_5000.fits_g10_5040 %f %f %f %f %f %f %f %f %f %f %f %f %f %f %f\n' %
                                  (ix, ra[ix], dec[ix], np.degrees(ra[ix]), np.degrees(dec[ix]),
                                  magNorm[ix], redshift[ix],
                                  max(majorAxis[ix], minorAxis[ix]), min(majorAxis[ix], minorAxis[ix]),
                                  positionAngle[ix], hlr[ix], sindex[ix], internalAv[ix], internalRv[ix],
                                  galacticAv[ix], galacticRv[ix],
                                  properMotionRa[ix], properMotionDec[ix], radialVelocity[ix], parallax[ix]))


    @classmethod
    def tearDownClass(cls):
        if os.path.exists(cls.bulge_name):
            os.unlink(cls.bulge_name)

        if os.path.exists(cls.disk_name):
            os.unlink(cls.disk_name)

        if os.path.exists(cls.agn_name):
            os.unlink(cls.agn_name)

        if os.path.exists(cls.star_name):
            os.unlink(cls.star_name)


    def testGalSimPhoSimCat(self):
        """
        Run a GalSimPhoSim catalog on some data. Then, generate an ordinary PhoSim catalog using
        the same data.  Verify that the two resulting PhoSim catalogs are identical.
        """

        galsim_cat_name = os.path.join(self.dataDir, 'galSimPhoSim_galsim_cat.txt')
        phosim_cat_name = os.path.join(self.dataDir, 'galSimPhoSim_phosim_cat.txt')
        galsim_image_root = os.path.join(self.dataDir, 'galSimPhoSim_images')
        db = fileDBObject(self.bulge_name, dtype=self.dtype, runtable='test_bulges', idColKey='id')
        db.raColName = 'ra_deg'
        db.decColName = 'dec_deg'
        db.objectTypeId = 55

        gs_cat = GalSimPhoSimGalaxies(db, obs_metadata=self.obs)
        gs_cat.bandpassNames = self.obs.bandpass
        gs_cat.PSF = SNRdocumentPSF()
        gs_cat.write_catalog(galsim_cat_name)

        gs_cat_0 = gs_cat

        ps_cat = PhoSimCatalogSersic2D(db, obs_metadata=self.obs)
        ps_cat.write_catalog(phosim_cat_name)

        db = fileDBObject(self.disk_name, dtype=self.dtype, runtable='test_disks', idColKey='id')
        db.raColName = 'ra_deg'
        db.decColName = 'dec_deg'
        db.objectTypeId = 155

        gs_cat = GalSimPhoSimGalaxies(db, obs_metadata=self.obs)
        gs_cat.bandpassNames = self.obs.bandpass
        gs_cat.copyGalSimInterpreter(gs_cat_0)
        gs_cat.write_catalog(galsim_cat_name, write_header=False, write_mode='a')

        gs_cat_0 = gs_cat

        ps_cat = PhoSimCatalogSersic2D(db, obs_metadata=self.obs)
        ps_cat.write_catalog(phosim_cat_name, write_header=False, write_mode='a')

        db = fileDBObject(self.agn_name, dtype=self.dtype, runtable='test_agn', idColKey='id')
        db.raColName = 'ra_deg'
        db.decColName = 'dec_deg'
        db.objectTypeId = 255

        gs_cat = GalSimPhoSimAgn(db, obs_metadata=self.obs)
        gs_cat.bandpassNames = self.obs.bandpass
        gs_cat.copyGalSimInterpreter(gs_cat_0)
        gs_cat.write_catalog(galsim_cat_name, write_header=False, write_mode='a')

        gs_cat_0 = gs_cat

        ps_cat = PhoSimCatalogZPoint(db, obs_metadata=self.obs)
        ps_cat.write_catalog(phosim_cat_name, write_header=False, write_mode='a')

        db = fileDBObject(self.star_name, dtype=self.dtype, runtable='test_agn', idColKey='id')
        db.raColName = 'ra_deg'
        db.decColName = 'dec_deg'
        db.objectTypeId = 255

        gs_cat = GalSimPhoSimStars(db, obs_metadata=self.obs)
        gs_cat.bandpassNames = self.obs.bandpass
        gs_cat.copyGalSimInterpreter(gs_cat_0)
        gs_cat.write_catalog(galsim_cat_name, write_header=False, write_mode='a')

        ps_cat = PhoSimCatalogPoint(db, obs_metadata=self.obs)
        ps_cat.write_catalog(phosim_cat_name, write_header=False, write_mode='a')

        written_files = gs_cat.write_images(nameRoot=galsim_image_root)
        self.assertGreater(len(written_files), 0)
        for name in written_files:
            os.unlink(name)

        with open(galsim_cat_name, 'r') as galsim_input:
            with open(phosim_cat_name, 'r') as phosim_input:
                galsim_lines = galsim_input.readlines()
                phosim_lines = phosim_input.readlines()
                self.assertEqual(len(galsim_lines), len(phosim_lines))
                self.assertEqual(len(galsim_lines), 4*self.n_objects+5)
                for line in galsim_lines:
                    self.assertIn(line, phosim_lines)
                for line in phosim_lines:
                    self.assertIn(line, galsim_lines)

        if os.path.exists(galsim_cat_name):
            os.unlink(galsim_cat_name)

        if os.path.exists(phosim_cat_name):
            os.unlink(phosim_cat_name)


def suite():
    utilsTests.init()
    suites = []
    suites += unittest.makeSuite(GalSimPhoSimTest)

    return unittest.TestSuite(suites)

def run(shouldExit = False):
    utilsTests.run(suite(), shouldExit)

if __name__ == "__main__":
    run(True)
