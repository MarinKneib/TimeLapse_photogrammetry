These are the scripts used for the automated SfM processing of time-lapse camera images using Agisoft Metashape, along with example datasets.

The scripts are used as follows:

Agisoft_processing_chain_Part1.py: Takes the image sets as inputs and does all the processing steps (image matching, camera alignement, first optimization without GCPs) until a sparse cloud is obtained.
				Takes as inputs the images sets, the camera parameters (CAMCalib_DSLR1.txt,DSLR1_selection.csv,IMG_batch_1) and the coordinates of the GCPs (TL002_REF_PGCPs)

Agisoft_processing_chain_Part2.py: Once the GCP position has been adjusted manually in the images, this script conducts the optimization, buidls and exports the dense cloud and DEM.

Agisoft_processing_chain_export_orthos.py: This script outputs the orthomosaics

Melt_calc.r: Calculates the slope-perpendicular melt and thinning from a series of overlapping DEMs


Author: Marin Kneib
Work address: Swiss Federal Research Institute WSL
Email: marin.kneib@wsl.ch
