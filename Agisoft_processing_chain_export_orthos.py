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
    doc = Metashape.app.document
    path = ''.join(['path/2/agisoft_folder/TL',str(ii),'_v1.psx'])
    doc.open(path)
    chunk = doc.chunk
	
    # Checking compatibility
    compatible_major_version = "1.7"
    found_major_version = ".".join(Metashape.app.version.split('.')[:2])
    if found_major_version != compatible_major_version:
        raise Exception("Incompatible Metashape version: {} != {}".format(found_major_version, compatible_major_version))
    
    ## export dem & point cloud
    #chunk.exportModel(path=''.join([resultsdir,'PC_TL',str(ii),'_v5.obj']), texture_format=Metashape.ImageFormatTIFF,save_texture=True,\
    #                  save_uv=True,save_normals=True,save_colors=True,save_confidence=True,\
    #                  save_cameras=True,save_markers=True,save_udim=True,\
    #                  save_alpha=True,embed_texture=True,strip_extensions=False,\
    #                  raster_transform=Metashape.RasterTransformNone,colors_rgb_8bit=True,\
    #                  format=Metashape.ModelFormatOBJ,clip_to_boundary=True)
    #
    #
    chunk.buildDem(source_data=Metashape.DenseCloudData,interpolation=Metashape.DisabledInterpolation)
    doc.save(path)
    chunk.buildOrthomosaic(surface_data=Metashape.DataSource.ElevationData, fill_holes=False,\
                       resolution=0.24, resolution_x=0.24, resolution_y=0.24, flip_x=False, flip_y=False,\
                       flip_z=False, subdivide_task=True)
    doc.save(path)

    chunk.exportRaster(path=''.join([resultsdir,'Ortho_TL',str(ii),'_v1.tif']),\
                       format=Metashape.RasterFormat.RasterFormatTiles,image_format=Metashape.ImageFormat.ImageFormatTIFF,\
                       raster_transform=Metashape.RasterTransformType.RasterTransformNone,\
                       resolution=0.24,resolution_x=0.24,resolution_y=0.24,\
                       source_data=Metashape.DataSource.OrthomosaicData)
    
    
    
    
    #print("Script finished")
    #
