# -*- coding: utf-8 -*-
"""
Created on Wed Apr 14 13:09:29 2021

@author: Kneib
"""

import Metashape

# resultsdir = 'X:/Partage/MESANGE/argentiere_courtes_time-lapse/RESULTS_v1/'
for ii in [1757]:
    # read CAM1 image names
    with open(''.join([CAMsel_dir,'CAM1_selection_Period2.csv'])) as CAM1_selection:
        CAM1_images = csv.reader(CAM1_selection, delimiter=',')
        CAM1_label = []
        for row in CAM1_images:
            CAM1_label.append(row[0])
        
    date_str = CAM1_label[ii]
    
    doc = Metashape.app.document
    path = ''.join(['X:/Partage/MESANGE/argentiere_courtes_time-lapse/TL_Arg_',date_str[5:22],'_wPGCPs_TLCAM.psx'])
    doc.open(path)
    chunk = doc.chunk
    
    ## Optimize cameras - second optimization with GCPs
    chunk.optimizeCameras(fit_f=False, fit_cx=False, fit_cy=False, fit_b1=False,\
                          fit_b2=False, fit_k1=True,fit_k2=True, fit_k3=True,\
                          fit_k4=False, fit_p1=False, fit_p2=False, fit_corrections=False,\
                          adaptive_fitting=False, tiepoint_covariance=True)
    
    # build dense cloud
    chunk.buildDepthMaps(downscale=2, filter_mode=Metashape.MildFiltering) # downscale (int) – Depth map quality (1 - Ultra high, 2 - High, 4 - Medium, 8 - Low, 16 - Lowest).
    chunk.buildDenseCloud(point_colors = True, point_confidence = True, keep_depth = True)
    doc.save(path)
    
    # build DEM
    chunk.buildDem(source_data=Metashape.DenseCloudData,interpolation=Metashape.DisabledInterpolation)
    doc.save(path)
    
    crs_export = Metashape.CoordinateSystem("EPSG::2154")
    ## export dem & point cloud
    
    #chunk.exportModel(path=''.join([resultsdir,'PC_TL',date_str[5:22],'.obj']), texture_format=Metashape.ImageFormatTIFF,save_texture=True,\
    #                  save_uv=True,save_normals=True,save_colors=True,save_confidence=True,\
    #                  save_cameras=True,save_markers=True,save_udim=True,\
    #                  save_alpha=True,embed_texture=True,strip_extensions=False,\
    #                  raster_transform=Metashape.RasterTransformNone,colors_rgb_8bit=True,\
    #                  format=Metashape.ModelFormatOBJ,clip_to_boundary=True)
    chunk.exportPoints(path=''.join([resultsdir,'PC_TL',date_str[5:22],'.txt']), binary=True,
                        save_colors=True, save_normals=True, save_classes=False, format=Metashape.PointsFormat.PointsFormatXYZ,
                        save_confidence=False, raster_transform=Metashape.RasterTransformType.RasterTransformNone, 
                        colors_rgb_8bit=True, crs=crs_export)
    
    #chunk.exportRaster(path=''.join([resultsdir,'DEM_TL_Arg_',date_str[5:22],'_wPGCPs_TLCAM_autom.tif']),projection=crs_export,
    #                   source_data=Metashape.DataSource.ElevationData,
    #                   image_format=Metashape.ImageFormat.ImageFormatTIFF,
    #                   raster_transform=Metashape.RasterTransformType.RasterTransformNone,
    #                   resolution=0.40,resolution_x=0.40,resolution_y=0.40)
    
    
    
    
    #print("Script finished")
    #
