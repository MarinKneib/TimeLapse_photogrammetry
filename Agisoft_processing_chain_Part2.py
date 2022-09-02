# -*- coding: utf-8 -*-
"""
Created on Wed Apr 14 13:09:29 2021

@author: Kneib
"""

import Metashape

# define directories
resultsdir = 'path/2/resultsdir/'
# loop through all image pairs to process
for ii in [317,318]:
	# open psx document
    doc = Metashape.app.document
    path = ''.join(['path/2/agisoft_folder/TL',str(ii),'_v1.psx'])
    doc.open(path)
    chunk = doc.chunk
    # Checking compatibility
    compatible_major_version = "1.7"
    found_major_version = ".".join(Metashape.app.version.split('.')[:2])
    if found_major_version != compatible_major_version:
        raise Exception("Incompatible Metashape version: {} != {}".format(found_major_version, compatible_major_version))
    
    ## Optimize cameras - second optimization with PGCPs
    chunk.optimizeCameras(fit_f=False, fit_cx=False, fit_cy=False, fit_b1=False,\
                          fit_b2=False, fit_k1=True,fit_k2=True, fit_k3=True,\
                          fit_k4=False, fit_p1=False, fit_p2=False, fit_corrections=False,\
                          adaptive_fitting=False, tiepoint_covariance=True)
    
    # build dense cloud
    chunk.buildDepthMaps(downscale=4, filter_mode=Metashape.AggressiveFiltering)
    chunk.buildDenseCloud(point_colors = True, point_confidence = True, keep_depth = True)
    doc.save(path)
	
    # build DEM
    chunk.buildDem(source_data=Metashape.DenseCloudData,interpolation=Metashape.DisabledInterpolation)
    doc.save(path)
    
    ## export dem & point cloud
    #chunk.exportModel(path=''.join([resultsdir,'PC_TL',str(ii),'_v5.obj']), texture_format=Metashape.ImageFormatTIFF,save_texture=True,\
    #                  save_uv=True,save_normals=True,save_colors=True,save_confidence=True,\
    #                  save_cameras=True,save_markers=True,save_udim=True,\
    #                  save_alpha=True,embed_texture=True,strip_extensions=False,\
    #                  raster_transform=Metashape.RasterTransformNone,colors_rgb_8bit=True,\
    #                  format=Metashape.ModelFormatOBJ,clip_to_boundary=True)
    #
    #
    chunk.exportRaster(path=''.join([resultsdir,'DEM_TL',str(ii),'_v1.tif']),\
                       format=Metashape.RasterFormat.RasterFormatTiles,image_format=Metashape.ImageFormat.ImageFormatTIFF,\
                       raster_transform=Metashape.RasterTransformType.RasterTransformNone,\
                       resolution=0.24,resolution_x=0.24,resolution_y=0.24,\
                       source_data=Metashape.DataSource.ElevationData)
    
    
    
    
    #print("Script finished")
    #
