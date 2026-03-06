# -*- coding: utf-8 -*-
"""
Created on Wed Apr 14 13:09:29 2021

@author: Kneib
"""

import Metashape
import csv

# following https://github.com/agisoft-llc/metashape-scripts/blob/master/src/quick_layout.py

# Checking compatibility
compatible_major_version = "1.8"
found_major_version = ".".join(Metashape.app.version.split('.')[:2])
if found_major_version != compatible_major_version:
    raise Exception("Incompatible Metashape version: {} != {}".format(found_major_version, compatible_major_version))

Processing_dir = 'V:/gl_kneibm/Projects/PI/2024_CAIRN-GLOBAL/TL_photogrammetry_Argentiere/processing_time-lapse/processing_LB/' 
PGCP_dir = 'V:/gl_kneibm/Projects/PI/2024_CAIRN-GLOBAL/TL_photogrammetry_Argentiere/processing_time-lapse/PGCPs/'
CAMcalib_dir = 'V:/gl_kneibm/Projects/PI/2024_CAIRN-GLOBAL/TL_photogrammetry_Argentiere/data/TLCAM/CAM_calibration/'
CAMsel_dir = 'V:/gl_kneibm/Projects/PI/2024_CAIRN-GLOBAL/TL_photogrammetry_Argentiere/data/TLCAM/CAM_selection/'
Img_dir = 'V:/gl_kneibm/Projects/PI/2024_CAIRN-GLOBAL/TL_photogrammetry_Argentiere/data/TLCAM/Images/'
   
global doc
doc = Metashape.app.document
for ii in [1883]:
    # read CAM1 image names
    with open(''.join([CAMsel_dir,'CAM1_selection_Period2.csv'])) as CAM1_selection:
        CAM1_images = csv.reader(CAM1_selection, delimiter=',')
        CAM1_label = []
        for row in CAM1_images:
            CAM1_label.append(row[0])
        
    date_str = CAM1_label[ii]

    doc.clear()
    path = ''.join([Processing_dir,'TL_Arg_',date_str[5:22],'_wPGCPs_TLCAM_test_scripts.psx'])
    doc.save(path)
    
    # New chunk
    
    chunk = doc.addChunk()
    # Define paths to photos
    path_photos_CAM1 = ''.join([Img_dir,'CAM1'])
    path_photos_CAM2 = ''.join([Img_dir,'CAM2'])
    path_photos_CAM2B = ''.join([Img_dir,'CAM2B'])
    path_photos_CAM2N = ''.join([Img_dir,'CAM2N'])
    path_photos_CAM3 = ''.join([Img_dir,'CAM3'])
    path_photos_CAM4 = ''.join([Img_dir,'CAM4'])
    path_photos_CAM4B = ''.join([Img_dir,'CAM4B'])
    path_photos_CAM4N = ''.join([Img_dir,'CAM4N'])
    path_photos_CAM4QUALI = ''.join([Img_dir,'CAM4QUALI'])
    path_photos_CAM5 = ''.join([Img_dir,'CAM5'])
    
    # read image names from csv files containing image lists
    with open(''.join([CAMsel_dir,'CAM2B_selection_Period2.csv'])) as CAM2B_selection:
       CAM2B_images = csv.reader(CAM2B_selection, delimiter=',')
       CAM2B_label = []
       for row in CAM2B_images:
           CAM2B_label.append(row[0])
           
    with open(''.join([CAMsel_dir,'CAM2N_selection_Period2.csv'])) as CAM2N_selection:
       CAM2N_images = csv.reader(CAM2N_selection, delimiter=',')
       CAM2N_label = []
       for row in CAM2N_images:
           CAM2N_label.append(row[0])
           
    with open(''.join([CAMsel_dir,'CAM3_selection_Period2.csv'])) as CAM3_selection:
       CAM3_images = csv.reader(CAM3_selection, delimiter=',')
       CAM3_label = []
       for row in CAM3_images:
           CAM3_label.append(row[0])
           
    with open(''.join([CAMsel_dir,'CAM4B_selection_Period2.csv'])) as CAM4B_selection:
       CAM4B_images = csv.reader(CAM4B_selection, delimiter=',')
       CAM4B_label = []
       for row in CAM4B_images:
           CAM4B_label.append(row[0])
           
    with open(''.join([CAMsel_dir,'CAM4N_selection_Period2.csv'])) as CAM4N_selection:
       CAM4N_images = csv.reader(CAM4N_selection, delimiter=',')
       CAM4N_label = []
       for row in CAM4N_images:
           CAM4N_label.append(row[0])
           
    with open(''.join([CAMsel_dir,'CAM4QUALI_selection_Period2.csv'])) as CAM4QUALI_selection:
       CAM4QUALI_images = csv.reader(CAM4QUALI_selection, delimiter=',')
       CAM4QUALI_label = []
       for row in CAM4QUALI_images:
           CAM4QUALI_label.append(row[0])
           
    with open(''.join([CAMsel_dir,'CAM5_selection_Period2.csv'])) as CAM5_selection:
       CAM5_images = csv.reader(CAM5_selection, delimiter=',')
       CAM5_label = []
       for row in CAM5_images:
           CAM5_label.append(row[0])
    
    # Append image name to path
    photo_list=list()
    if CAM1_label[ii] != '.':
        photo_list.append(''.join([path_photos_CAM1,'/',CAM1_label[ii]]))
    if CAM2B_label[ii] != '.':
        photo_list.append(''.join([path_photos_CAM2B,'/',CAM2B_label[ii]]))
    if CAM2N_label[ii] != '.':
        photo_list.append(''.join([path_photos_CAM2N,'/',CAM2N_label[ii]]))
    if CAM3_label[ii] != '.':
        photo_list.append(''.join([path_photos_CAM3,'/',CAM3_label[ii]]))
    if CAM4B_label[ii] != '.':
        photo_list.append(''.join([path_photos_CAM4B,'/',CAM4B_label[ii]]))
    if CAM4N_label[ii] != '.':
        photo_list.append(''.join([path_photos_CAM4N,'/',CAM4N_label[ii]]))
    if CAM4QUALI_label[ii] != '.':
        photo_list.append(''.join([path_photos_CAM4QUALI,'/',CAM4QUALI_label[ii]]))
    if CAM5_label[ii] != '.':
        photo_list.append(''.join([path_photos_CAM5,'/',CAM5_label[ii]]))
    
    # load images to chunk
    print(photo_list)
    chunk.addPhotos(photo_list)
    
    # Load camera position & view angles
    chunk.importReference(path=''.join([CAMsel_dir,'Imbatch_Period2_',str(ii),'.csv']),
                        format=Metashape.ReferenceFormatCSV,
                        columns='nxyzXYZabcABC',delimiter=",")
    
    #define coordinate system
    chunk.crs = Metashape.CoordinateSystem("EPSG::4326")
    
    doc.save(path)
    
    # Import calibration parameters of cameras
    idx = 0
    for camera in chunk.cameras:
        idx = idx+1
        Group = chunk.addCameraGroup()
        # if it's camera 3 and we're 07/02/2024 or later, it has been replaced with camera 4B
        if camera.label[:4] == 'CAM3' and ii>1324:
            filename = ''.join([CAMcalib_dir,'CAMCalib_CAM4B_2023-09-27_130000.txt'])
        else:
            filename = ''.join([CAMcalib_dir,'CAMCalib_',camera.label[:len(camera.label)-17],'2023-09-27_130000.txt'])
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
    
    # Import PGCPs
    chunk.importReference(path=''.join([PGCP_dir,'PseudoGCPs_forCAM_ref.csv']),format=Metashape.ReferenceFormatCSV,\
                          columns='nxyzXYZ', delimiter=';',group_delimiters=False,\
                          skip_rows=1,crs=chunk.crs,ignore_labels=False,create_markers=True)
    # Enable rotation angles for optimization
    for camera in chunk.cameras:
        camera.reference.rotation_enabled = True
        
    ## Optimize cameras - first optimization without GCPs
    chunk.optimizeCameras(fit_f=False, fit_cx=False, fit_cy=False, fit_b1=False,\
                          fit_b2=False, fit_k1=True,fit_k2=False, fit_k3=False,\
                          fit_k4=False, fit_p1=False, fit_p2=False, fit_corrections=False,\
                          adaptive_fitting=False, tiepoint_covariance=False)
    
    ## de-fix camera calibration parameters
    for camera in chunk.cameras:
        camera.sensor.fixed = False
        
    doc.save(path)

#print("Script finished")
#
