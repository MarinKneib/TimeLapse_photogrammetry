# -*- coding: utf-8 -*-
"""
Created on Wed Apr 14 13:09:29 2021

@author: Kneib
"""

import Metashape
import csv

# following https://github.com/agisoft-llc/metashape-scripts/blob/master/src/quick_layout.py

# Checking compatibility
compatible_major_version = "1.7"
found_major_version = ".".join(Metashape.app.version.split('.')[:2])
if found_major_version != compatible_major_version:
    raise Exception("Incompatible Metashape version: {} != {}".format(found_major_version, compatible_major_version))

global doc
doc = Metashape.app.document

# loop through all image pairs to process
for ii in [317,318]:
	# Create psx document
    doc.clear()
    path = ''.join(['path/2/agisoft_folder/TL',str(ii),'_v1.psx'])
    doc.save(path)
    
    # New chunk
    chunk = doc.addChunk()
    
    # Define paths to photos (one folder for each TL camera)
    path_photos_dslr1 = 'path/2/images/dslr/dslr1'
    path_photos_dslr2 = 'path/2/images/dslr/dslr2'
    path_photos_dslr3 = 'path/2/images/dslr/dslr3'
    path_photos_dslr4 = 'path/2/images/dslr/dslr4'
    
	# define other directories
    homedir = 'path/2/homedir/'
    resultsdir = 'path/2/resultsdir/'
    
    # read image names from csv files containing image lists + parameters (see csv)
        
    with open(''.join([resultsdir,'DSLR1_selection.csv'])) as DSLR1_selection:
       DSLR1_images = csv.reader(DSLR1_selection, delimiter=',')
       DSLR1_label = []
       for row in DSLR1_images:
           DSLR1_label.append(''.join([row[0][0:15],'jpg']))
           
    with open(''.join([resultsdir,'DSLR2_selection.csv'])) as DSLR2_selection:
       DSLR2_images = csv.reader(DSLR2_selection, delimiter=',')
       DSLR2_label = []
       for row in DSLR2_images:
           DSLR2_label.append(''.join([row[0][0:15],'jpg']))
           
    with open(''.join([resultsdir,'DSLR3_selection.csv'])) as DSLR3_selection:
       DSLR3_images = csv.reader(DSLR3_selection, delimiter=',')
       DSLR3_label = []
       for row in DSLR3_images:
           DSLR3_label.append(''.join([row[0][0:15],'jpg']))
           
    with open(''.join([resultsdir,'DSLR4_selection.csv'])) as DSLR4_selection:
       DSLR4_images = csv.reader(DSLR4_selection, delimiter=',')
       DSLR4_label = []
       for row in DSLR4_images:
           DSLR4_label.append(''.join([row[0][0:15],'jpg']))
    
    # Append image name to path
    photo_list=list()
    photo_list.append(''.join([path_photos_dslr1,'/',DSLR1_label[ii]]))
    photo_list.append(''.join([path_photos_dslr2,'/',DSLR2_label[ii]]))
    photo_list.append(''.join([path_photos_dslr3,'/',DSLR3_label[ii]]))
    photo_list.append(''.join([path_photos_dslr4,'/',DSLR4_label[ii]]))
    
    # load images to chunk
    print(photo_list)
    chunk.addPhotos(photo_list)
    
    # Load camera position & view angles (see csv)
    chunk.importReference(path=''.join([resultsdir,'IMG_batch_',str(ii),'.csv']),
                        format=Metashape.ReferenceFormatCSV,
                        columns='nxyzXYZabcABC',delimiter=",")
    
    #define coordinate system (change as needed)
    chunk.crs = Metashape.CoordinateSystem("EPSG::32646")
    
    doc.save(path)
    
    # Import calibration parameters of cameras (see txt)
    idx = 0
    for camera in chunk.cameras:
        idx = idx+1
        Group = chunk.addCameraGroup()
        filename = ''.join([resultsdir,'CAMCalib_',camera.label[0:5],'.txt'])
        calib = Metashape.Calibration()
        calib.load(filename, format = Metashape.CalibrationFormatAustralis)
        sensor = chunk.addSensor()
        sensor.width = calib.width
        sensor.height = calib.height
        sensor.type = calib.type
        sensor.user_calib = calib
        sensor.fixed = True
        camera.group = Group
        camera.sensor = sensor
    #    camera.calibration.load(filename, format = Metashape.CalibrationFormatAustralis)
    
    
    doc.save(path)
    
    # Match photos
    accuracy = 0  # equivalent to highest accuracy
    keypoints = 200000 #align photos key point limit
    tiepoints = 20000 #align photos tie point limit
    chunk.matchPhotos(downscale=accuracy, generic_preselection = True,reference_preselection=False,\
                      filter_mask = False, keypoint_limit = keypoints, tiepoint_limit = tiepoints)
    
    # Align cameras
    chunk.alignCameras(adaptive_fitting=False) #align cameras without adaptive fitting of distorsion coefficients
    
    # Import PGCPs (see csv)
    chunk.importReference(path=''.join([resultsdir,'TL002_REF_PGCPs.csv']),format=Metashape.ReferenceFormatCSV,\
                          columns='nxyzXYZ', delimiter=',',group_delimiters=False,\
                          skip_rows=1,crs=chunk.crs,ignore_labels=False,create_markers=True)
    # Enable rotation angles for optimization
    for camera in chunk.cameras:
        camera.reference.rotation_enabled = True
        
    ## Optimize cameras - first optimization without GCPs
    chunk.optimizeCameras(fit_f=False, fit_cx=False, fit_cy=False, fit_b1=False,\
                          fit_b2=False, fit_k1=False,fit_k2=False, fit_k3=False,\
                          fit_k4=False, fit_p1=False, fit_p2=False, fit_corrections=False,\
                          adaptive_fitting=False, tiepoint_covariance=False)
    
    ## de-fix camera calibration parameters
    for camera in chunk.cameras:
        camera.sensor.fixed = False
        
    doc.save(path)

#print("Script finished")
#
