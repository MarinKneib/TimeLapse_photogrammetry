# clear entire workspace (excl. packages)
rm(list = ls())
gc()

###### Upload libraries
library(raster)
library(gsubfn) # For functions with several outputs
library(CircStats) # To get aspect mean & std
library(circular)
library(readxl) # Read tracking data
library(tibble)
library(rgdal)
library(ggplot2)
library(data.tree)
library(rgeos)
library(sp)
library(rgdal)
library(matrixStats)
library(gdalUtils)
library(pracma)

# define &-sign for pasting string-elements
'&' <- function(...) UseMethod('&')
'&.default' <- .Primitive('&')
'&.character' <- function(...) paste(...,sep='')

# param
neighbCells<-8 # for slope calculation
path_data<-'path/2/data/'
path_results<-'path/2/results/'

# projection
projec<-'+proj=utm +zone=46N +datum=WGS84'

# Cliff shapefile
mask<-readOGR('path/2/cliff/outlines/Cliff_outline.shp') # can be adapted to area of interest

# list of DEMs for which to calculate the dH
DEM_list<-c(1,27,33,47,77,97,118,142,160,189,222,249,275,291,301,318,325,340,356)

# Calculate melt between every second DEM
for (kk in 1:(length(DEM_list)-2)){

  pp<-toString(DEM_list[kk])
  qq<-toString(DEM_list[kk+2])
  
  # load rasters
  DEM1<-paste(path_data,'DEM_TL',pp,'_v1_unwarped_slopecorr_emerge.tif',sep='')
  DEM1<-raster(DEM1)
  
  DEM2<-paste(path_data,'DEM_TL',qq,'_v1_unwarped_slopecorr_emerge.tif',sep='')
  DEM2<-raster(DEM2)
  
  # crop to extent
  DEM1_crop<-crop(DEM1,extent(mask))
  DEM2_crop<-crop(DEM2,extent(mask))
  
  DEM1_crop<-mask(DEM1_crop,mask)
  DEM2_crop<-mask(DEM2_crop,mask)
  
  #resample DEM2 to DEM1
  DEM2_resamp<-resample(DEM2_crop,DEM1_crop,'bilinear')
  
  # calculate dH
  dH<-DEM1_crop-DEM2_resamp
  
  # calculate slope/aspect
  slope1<-terrain(DEM1_crop,opt='slope',unit='degrees',neighbors=neighbCells)
  aspect1<-terrain(DEM1_crop,opt='aspect',unit='degrees',neighbors=neighbCells)
  
  slope2<-terrain(DEM2_crop,opt='slope',unit='degrees',neighbors=neighbCells)
  aspect2<-terrain(DEM2_crop,opt='aspect',unit='degrees',neighbors=neighbCells)
  
  # Convert to data frames with elevation, slope, aspect, dH, x and y of each pixel and of each DEM
  stack1<-stack(DEM1_crop,slope1,aspect1,dH)
  stack2<-stack(DEM2_crop,slope2,aspect2)
  
  df1<-data.frame(extract(stack1,extent(stack1)))
  df2<-data.frame(extract(stack2,extent(stack2)))
  
  idx1<-as.numeric(rownames(df1))
  coord1<-xyFromCell(stack1,idx1)
  df1<-data.frame(cbind(df1,coord1))
  colnames(df1)<-c('Elevation','Slope','Aspect','dH','x','y')
  
  idx2<-as.numeric(rownames(df2))
  coord2<-xyFromCell(stack1,idx2)
  df2<-data.frame(cbind(df2,coord2))
  colnames(df2)<-c('Elevation','Slope','Aspect','x','y')
  
  # calculate normal coordinates
  Nz1<--cos(df1$Slope*pi/180)
  Nx1<--sin(df1$Slope*pi/180)*sin(df1$Aspect*pi/180)
  Ny1<--sin(df1$Slope*pi/180)*cos(df1$Aspect*pi/180)
  
  # calculate point coordinates on normal
  Hx1<-df1$x+df1$dH*Nx1
  Hy1<-df1$y+df1$dH*Ny1
  Hz1<-df1$Elevation+df1$dH*Nz1
  
  # remove NaNs in df2
  df2_nonan<-df2
  df2_nonan<-df2_nonan[complete.cases(df2_nonan),] # no NAs
  
  ### calculate distance between all points of DEM2 and select 3 closest ones (C1, C2, C3)
  
  # initialize - vector of NaNs
  C1x<-numeric(length(Hx1))/numeric(length(Hx1))
  C1y<-numeric(length(Hx1))/numeric(length(Hx1))
  C1z<-numeric(length(Hx1))/numeric(length(Hx1))
  C2x<-numeric(length(Hx1))/numeric(length(Hx1))
  C2y<-numeric(length(Hx1))/numeric(length(Hx1))
  C2z<-numeric(length(Hx1))/numeric(length(Hx1))
  C3x<-numeric(length(Hx1))/numeric(length(Hx1))
  C3y<-numeric(length(Hx1))/numeric(length(Hx1))
  C3z<-numeric(length(Hx1))/numeric(length(Hx1))
  
  for (ii in seq(1,length(Hx1),1)){
    if (is.na(Hx1[ii])==FALSE & is.na(Hy1[ii])==FALSE & is.na(Hz1[ii])==FALSE){
      dist<-abs(df2_nonan$x-Hx1[ii])+abs(df2_nonan$y-Hy1[ii])+abs(df2_nonan$Elevation-Hz1[ii]) # calculate distance from all points
      idx1<-which.min(dist) # find closest point
      C1x[ii]<-df2_nonan$x[idx1]
      C1y[ii]<-df2_nonan$y[idx1]
      C1z[ii]<-df2_nonan$Elevation[idx1]
      dist[idx1]<-NaN # remove
      idx2<-which.min(dist) # find 2nd closest point
      C2x[ii]<-df2_nonan$x[idx2]
      C2y[ii]<-df2_nonan$y[idx2]
      C2z[ii]<-df2_nonan$Elevation[idx2]
      dist[idx2]<-NaN
      idx3<-which.min(dist) # find 3rd closest point
      C3x[ii]<-df2_nonan$x[idx3]
      C3y[ii]<-df2_nonan$y[idx3]
      C3z[ii]<-df2_nonan$Elevation[idx3]
      # Make sure the 3 points are not aligned
      while ((C1x[ii] == C2x[ii] & C1x[ii] == C3x[ii]) | (C1y[ii] == C2y[ii] & C1y[ii] == C3y[ii])){
        dist[idx3]<-NaN
        idx3<-which.min(dist) # find 3rd closest point
        C3x[ii]<-df2_nonan$x[idx3]
        C3y[ii]<-df2_nonan$y[idx3]
        C3z[ii]<-df2_nonan$Elevation[idx3]
      }
    }
  }
  # get normal of plane defined by C1, C2, C3
  C1C2x<-C2x-C1x
  C1C2y<-C2y-C1y
  C1C2z<-C2z-C1z
  
  C1C3x<-C3x-C1x
  C1C3y<-C3y-C1y
  C1C3z<-C3z-C1z
  
  nx<-C1C2y*C1C3z-C1C2z*C1C3y # vectorial product = normal
  ny<-C1C2z*C1C3x-C1C2x*C1C3z
  nz<-C1C2x*C1C3y-C1C2y*C1C3x
  
  # Calculate intersection of DEM1 normal and plane (from https://ch.mathworks.com/matlabcentral/fileexchange/17751-straight-line-and-plane-intersection)
  ux<-df1$x-Hx1
  uy<-df1$y-Hy1
  uz<-df1$Elevation-Hz1
  
  wx<-Hx1-C1x
  wy<-Hy1-C1y
  wz<-Hz1-C1z
  
  D<-nx*ux+ny*uy+nz*uz
  NN<--(nx*wx+ny*wy+nz*wz)
  
  sI<-NN/D
  
  Ix<-Hx1+sI*ux
  Iy<-Hy1+sI*uy
  Iz<-Hz1+sI*uz
  
  # Calculate melt distance
  mx<-Ix-df1$x
  my<-Iy-df1$y
  mz<-Iz-df1$Elevation
  
  M<-mx*Nx1+my*Ny1+mz*Nz1
  
  # remove weird value
  M[M< -5 | M>5]<-NaN
  
  # convert melt distance to raster
  M_df<-data.frame(cbind(df1$x,df1$y,M))
  M_r<-rasterFromXYZ(M_df)
  plot(M_r)
  
  dH_comp<-M_r*100/dH
  dH_comp[dH_comp>200 | dH_comp<0]<-NaN
  plot(dH_comp)
  
  # output rasters
  projection(M_r)<-projec
  projection(dH_comp)<-projec
  writeRaster(M_r,paste(path_results,'Melt_TL',pp,'-',qq,'.tif',sep=''),
              format='GTiff',overwrite=TRUE) 
  writeRaster(dH,paste(path_results,'dH_TL',pp,'-',qq,'.tif',sep=''),
              format='GTiff',overwrite=TRUE) 
  writeRaster(slope1,paste(path_results,'slope_TL',pp,'.tif',sep=''),
              format='GTiff',overwrite=TRUE) 
  writeRaster(aspect1,paste(path_results,'aspect_TL',pp,'.tif',sep=''),
              format='GTiff',overwrite=TRUE) 
  writeRaster(dH_comp,paste(path_results,'MeltvsdH_TL',pp,'-',qq,'_perc.tif',sep=''),
              format='GTiff',overwrite=TRUE) 
}

