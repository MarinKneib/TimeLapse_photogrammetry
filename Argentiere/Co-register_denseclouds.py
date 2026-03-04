

import numpy as np
import matplotlib.pyplot as plt
import py4dgeo
from matplotlib.colors import LinearSegmentedColormap
from scipy.interpolate import griddata
from scipy.spatial import cKDTree
import rasterio
from pathlib import Path
from rasterio.errors import RasterioIOError



""" Point cloud coregistration algorithm """



def downsample_point_cloud(points, downsample_factor):
    """
    Downsample a point cloud by randomly selecting a subset of points.

    Args:
    - points (numpy.ndarray): Input point cloud (N x 3).
    - downsample_factor (float): Downsampling factor (0.0 to 1.0).

    Returns:
    - downsampled_points (numpy.ndarray): Downsampled point cloud.
    """
    num_points = points.shape[0]
    num_points_to_keep = int(num_points * downsample_factor)
    indices = np.random.choice(num_points, num_points_to_keep, replace=False)
    downsampled_points = points[indices]
    return downsampled_points

def filter_points_inside_box(points, min_bound, max_bound):
    """
    Filter points that fall inside a specified bounding box.

    Args:
    - points (numpy.ndarray): Input point cloud (N x 3).
    - min_bound (numpy.ndarray): Minimum bounds of the box (1 x 3).
    - max_bound (numpy.ndarray): Maximum bounds of the box (1 x 3).

    Returns:
    - filtered_points (numpy.ndarray): Filtered point cloud.
    """
    mask = np.all((points[:, :3] >= min_bound) & (points[:, :3] <= max_bound), axis=1)
    filtered_points = points[mask]
    return filtered_points

def filter_points_outside_box(points, min_bound, max_bound):
    """
    Filter points that fall outside a specified bounding box.

    Args:
    - points (numpy.ndarray): Input point cloud (N x 3).
    - min_bound (numpy.ndarray): Minimum bounds of the box (1 x 3).
    - max_bound (numpy.ndarray): Maximum bounds of the box (1 x 3).

    Returns:
    - filtered_points (numpy.ndarray): Filtered point cloud.
    """
    mask = ~np.all((points[:, :3] >= min_bound) & (points[:, :3] <= max_bound), axis=1)
    filtered_points = points[mask]
    return filtered_points

def filter_points(points, colors, normals, criterium, threshold):
    """
    Filter points based on given criterium.

    Args:
    - points (numpy.ndarray): Input point cloud coordinates (N x 3).
    - colors (numpy.ndarray): RGB colors corresponding to points (N x 3).
    - normals (numpy.ndarray): Point normals corresponding to points (N x 3).
    - criterium (numpy.ndarray): Vector of values used for thresholding (N x 1).
    - threshold (float): Threshold value for color intensity filtering.

    Returns:
    - filtered_data (numpy.ndarray): Filtered point cloud data (N x 9).
    """
    mask = criterium < threshold  # Filter points based on grayscale intensity
    filtered_data = np.hstack((points[mask], colors[mask], normals[mask]))
    return filtered_data

def otsu_thresholding(vector, bins_num):
    """
    Determine Otsu threshold of distribution

    Args:
    - vector (float64): input values (Nx1)
    - bins_num (int): number of bins in histogram

    Returns:
    threshold (int): Otsu threshold value
    """
     
    # Get the image histogram
    hist, bin_edges = np.histogram(vector, bins=bins_num)
     
    # Calculate centers of bins
    bin_mids = (bin_edges[:-1] + bin_edges[1:]) / 2.
     
    # Iterate over all thresholds (indices) and get the probabilities w1(t), w2(t)
    weight1 = np.cumsum(hist)
    weight2 = np.cumsum(hist[::-1])[::-1]
     
    # Get the class means mu0(t)
    mean1 = np.cumsum(hist * bin_mids) / weight1
    # Get the class means mu1(t)
    mean2 = (np.cumsum((hist * bin_mids)[::-1]) / weight2[::-1])[::-1]
     
    inter_class_variance = weight1[:-1] * weight2[1:] * (mean1[:-1] - mean2[1:]) ** 2
     
    # Maximize the inter_class_variance function val
    index_of_max_val = np.argmax(inter_class_variance)
     
    threshold = bin_mids[:-1][index_of_max_val]
    return threshold

def calculate_aspect_slope(normal):
    """
    Calculate aspect and slope from the normal vector.

    Args:
    - normal (numpy.ndarray): Normal vector of the point (Nx3).

    Returns:
    - aspect (numpy.ndarray): Aspect angle in degrees.
    - slope (numpy.ndarray): Slope angle in degrees.
    """
    # Extract x, y, z components of normal vector
    normal_x, normal_y, normal_z = normal[:, 0], normal[:, 1], normal[:, 2]

    # Calculate aspect angle
    aspect = np.arctan2(-normal_y, -normal_x) * 180 / np.pi

    # Calculate slope angle
    slope = np.arctan(np.sqrt(normal_x**2 + normal_y**2) / normal_z) * 180 / np.pi

    return aspect, slope

def save_dem(array, filename):
    with rasterio.open(
        filename,
        "w",
        driver="GTiff",
        height=array.shape[0],
        width=array.shape[1],
        count=1,
        dtype=array.dtype,
        crs=crs_epsg,
        transform=transform,
        nodata=np.nan
    ) as dst:
        dst.write(array, 1)
    print("✅ Saved:", filename)

def save_ortho(x, y, rgb, xi, yi, res, max_gap_pixels, filename):
        # Precompute DEM pixel centers
        pixels_xy = np.column_stack([xi.ravel(), yi.ravel()])

        # Build KD-tree in XY
        tree = cKDTree(np.column_stack([x, y]))

        # Nearest neighbour lookup
        dist, idx = tree.query(pixels_xy, k=1, distance_upper_bound=res * max_gap_pixels)
        # Mask out empty pixels
        mask = np.isfinite(dist)
        
        # Prepare output arrays
        r_img = np.zeros(idx.shape, dtype=np.uint8)
        g_img = np.zeros(idx.shape, dtype=np.uint8)
        b_img = np.zeros(idx.shape, dtype=np.uint8)

        r_img[mask] = rgb[idx[mask], 0]
        g_img[mask] = rgb[idx[mask], 1]
        b_img[mask] = rgb[idx[mask], 2]

        # Stack into a single image array
        H, W = xi.shape
        ortho = np.dstack([
            r_img.reshape(H, W),
            g_img.reshape(H, W),
            b_img.reshape(H, W)
        ])

        with rasterio.open(
            filename,
            "w",
            driver="GTiff",
            height=ortho.shape[0],
            width=ortho.shape[1],
            count=3,                           # three bands!
            dtype=ortho.dtype,
            crs=crs_epsg,
            transform=transform,
            nodata=0
        ) as dst:
            dst.write(ortho[:, :, 0], 1)  # Red
            dst.write(ortho[:, :, 1], 2)  # Green
            dst.write(ortho[:, :, 2], 3)  # Blue

        print("✅ Saved orthoimage:", filename)

def interpolate_and_mask(x, y, z, xi, yi, res, max_gap_pixels):
    # Interpolation (cubic)
    zi = griddata((x, y), z, (xi, yi), method='cubic')

    # Distance to nearest real point
    tree = cKDTree(np.column_stack((x, y)))
    dist, _ = tree.query(np.column_stack((xi.ravel(), yi.ravel())), k=1)
    dist = dist.reshape(xi.shape)

    # Mask far pixels
    mask = dist > (max_gap_pixels * res)
    zi_masked = np.where(mask, np.nan, zi)

    return zi_masked



# Load the point cloud data from the txt file
ref_cloud_path = Path(
    "Z:/gl_kneibm/Projects/PI/2024_CAIRN-GLOBAL/TL_photogrammetry_Argentiere/"
    "results/point_clouds_DEMs_MK/results_v1/"
    "DenseCloud_TL_Arg_2023_09_27_1300_wPGCPs_TLCAM_autom.txt"
)

#slave_cloud_dir = Path(
#    "Z:/gl_kneibm/Projects/PI/2024_CAIRN-GLOBAL/TL_photogrammetry_Argentiere/"
#    "results/Point_clouds_LB/PhotoTL/full_period/Photo_time-lapse_export_metashape"
#)
slave_cloud_dir = Path(
    "Z:/gl_kneibm/Projects/PI/2024_CAIRN-GLOBAL/TL_photogrammetry_Argentiere/"
    "results/Point_clouds_LB/PhotoTL/full_period/Sans_coreg"
)

dem_dir = Path(
    "Z:/gl_kneibm/Projects/PI/2024_CAIRN-GLOBAL/TL_photogrammetry_Argentiere/"
    "results/DEM_LB/PhotoTL/Coreg_avec_PhotoTL_27-09/"
)
PC_dir = "Z:/gl_kneibm/Projects/PI/2024_CAIRN-GLOBAL/TL_photogrammetry_Argentiere/results/Point_clouds_LB/PhotoTL/full_period/Coreg_avec_photoTL_27-09/"

# Load reference cloud once
ref_cloud = np.loadtxt(ref_cloud_path)

# Define the minimum and maximum bounds of the bounding box
min_bound = np.array([1.0106e6, 6.5445e6, 2750])  # Minimum bounds (adjust as needed)
max_bound = np.array([1.0112e6, 6.5452e6, 3300])  # Maximum bounds (adjust as needed)

# Filter points inside the bounding box
ref_cloud = filter_points_inside_box(ref_cloud[:, :], min_bound, max_bound)

# prepare ref point cloud
downsample_factor = 1
downsampled_data_ref = downsample_point_cloud(ref_cloud[:, :], downsample_factor)

coordinates_ref = downsampled_data_ref[:, :3]
rgb_color_ref = downsampled_data_ref[:, 3:6]
point_normals_ref = downsampled_data_ref[:, 6:]

aspect_ref, slope_ref = calculate_aspect_slope(point_normals_ref)

## Visualize the point cloud (by slope/color)
#fig = plt.figure()
#ax = fig.add_subplot(111, projection='3d')
#scatter = ax.scatter(coordinates_ref[:, 0], coordinates_ref[:, 1], coordinates_ref[:, 2], marker='.')
#ax.set_xlabel('X')
#ax.set_ylabel('Y')
#ax.set_zlabel('Z')
#ax.view_init(elev=30, azim=30)  # Change the angles as needed
#plt.title('Ref point cloud')
#plt.show()

# remove all points less steep than 60° 
mask = slope_ref > 60  # Filter points based on grayscale intensity
stable_points_ref = downsampled_data_ref[mask]

min_bound = np.array([1.0107e6, 6.54465e6, 2700])  # Minimum bounds (adjust as needed)
max_bound = np.array([1.0112e6, 6.5452e6, 3100])  # Maximum bounds (adjust as needed)
stable_points_ref = filter_points_outside_box(stable_points_ref[:, :], min_bound, max_bound)
min_bound = np.array([1.0106e6, 6.5445e6, 2900])  # Minimum bounds (adjust as needed)
max_bound = np.array([1.0112e6, 6.5452e6, 3300])  # Maximum bounds (adjust as needed)
stable_points_ref = filter_points_inside_box(stable_points_ref[:, :], min_bound, max_bound)
min_bound = np.array([1.01105e6, 6.5444e6, 2600])  # Minimum bounds (adjust as needed)
max_bound = np.array([1.0113e6, 6.5452e6, 3300])  # Maximum bounds (adjust as needed)
stable_points_ref = filter_points_outside_box(stable_points_ref[:, :], min_bound, max_bound)

# Visualize the point cloud (by slope/color)
fig = plt.figure()
ax = fig.add_subplot(111, projection='3d')
scatter = ax.scatter(stable_points_ref[:, 0], stable_points_ref[:, 1], stable_points_ref[:, 2], marker='.')
ax.set_xlabel('X')
ax.set_ylabel('Y')
ax.set_zlabel('Z')
ax.view_init(elev=30, azim=30)  # Change the angles as needed
plt.title('Zones de terrain stable extraites géométriquement')
plt.show()

grayscale_intensity_ref = np.mean(stable_points_ref[:, 3:6], axis=1)
ndwi_ref = (stable_points_ref[:, 5]-stable_points_ref[:, 3])/(stable_points_ref[:, 3]+stable_points_ref[:, 5])

# Separation line
a = -150/0.25
b = 150
x_values = np.linspace(min(ndwi_ref), max(ndwi_ref), 100)
y_values = a * x_values + b

# scatter plot of grayscale vs ndwi
fig = plt.figure()
ax = fig.add_subplot(111)
ax.scatter(ndwi_ref[:], grayscale_intensity_ref[:], c=stable_points_ref[:, 3:6]/255, marker='.')
ax.plot(x_values, y_values, color='red', label='Line: y = ax + b')
ax.set_xlabel('NDWI')
ax.set_ylabel('INTENSITY')
ax.set_ylim(0, 255)
plt.show()

mask = grayscale_intensity_ref-(ndwi_ref*a+b)<0
stable_points_ref = stable_points_ref[mask]

fig = plt.figure()
ax = fig.add_subplot(111, projection='3d')
# Plot each point with its RGB color
ax.scatter(stable_points_ref[:, 0], stable_points_ref[:, 1], stable_points_ref[:, 2], c=stable_points_ref[:, 3:6]/255, marker='.')
ax.set_xlabel('X')
ax.set_ylabel('Y')
ax.set_zlabel('Z')
plt.title('Zone de terrain stable - nuage ref')
# Set the start angles
ax.view_init(elev=30, azim=30)  # Change the angles as needed
plt.show()

epoch_all_ref = py4dgeo.Epoch(downsampled_data_ref[:,:3])
epoch_stable_ref = py4dgeo.Epoch(stable_points_ref[:,:3])

# for export
res = 1.0 # Define grid resolution in meters
x_ref,y_ref,z_ref=downsampled_data_ref[:, 0],downsampled_data_ref[:, 1],downsampled_data_ref[:, 2]

# Define grid bounds
xmin, xmax = np.min(x_ref), np.max(x_ref)
ymin, ymax = np.min(y_ref), np.max(y_ref)

# Create a regular grid
xi_ref = np.arange(xmin, xmax, res)
yi_ref = np.arange(ymax, ymin, -res)
xi_ref, yi_ref = np.meshgrid(xi_ref, yi_ref)

# interpolate also zones with gaps within one pixel of pixels with values
max_gap_pixels = 1

## convert to DEM and save
#zi_ref_masked = interpolate_and_mask(x_ref, y_ref, z_ref, xi_ref, yi_ref, res, max_gap_pixels)
#
## Save as GeoTIFF
#transform = rasterio.transform.from_origin(xmin, ymax, res, res)
#crs_epsg = "EPSG:2154"  # RGF93 / Lambert-93
#
#try:
#    save_dem(zi_ref_masked,   dem_dir / "DEM_PC_TL2023-09-27_1300_ref_RGF93.tif")
#except RasterioIOError as e:
#    if "Permission denied" in str(e):
#        print("⚠️ Skipping file (permission denied)")
#    else:
#        print(f"⚠️ Rasterio error: {e}")
#
######### EXPORT ORTHOIMAGES
#rgb_color_ref = downsampled_data_ref[:, 3:6]
#try:
#    save_ortho(x_ref, y_ref, rgb_color_ref, xi_ref, yi_ref, res, max_gap_pixels, dem_dir / "ORTHO_PC_TL2023-09-27_1300_ref_RGF93.tif")
#except RasterioIOError as e:
#    if "Permission denied" in str(e):
#        print("⚠️ Skipping file (permission denied)")
#    else:
#        print(f"⚠️ Rasterio error: {e}")
#
#print('Outputs saved')

# Loop over all PC*.txt files
for slave_cloud_path in sorted(slave_cloud_dir.glob("PC*.txt"))[16]:
    slave_cloud_name = slave_cloud_path.stem  # e.g. "PC_TL2025-04-10_104622"
    slave_cloud = np.loadtxt(slave_cloud_path)

    print(f"Processing {slave_cloud_name}")

    # Define the minimum and maximum bounds of the bounding box
    min_bound = np.array([1.0106e6, 6.5445e6, 2750])  # Minimum bounds (adjust as needed)
    max_bound = np.array([1.0112e6, 6.5452e6, 3300])  # Maximum bounds (adjust as needed)

    # Filter points inside the bounding box
    slave_cloud = filter_points_inside_box(slave_cloud[:, :], min_bound, max_bound)

    # # Downsample the point cloud (adjust the downsample_factor as needed)
    # downsample_factor = 1  # Adjust this value based on your preference between 0 (no points) and 1 (all points)
    # downsampled_data_ref = downsample_point_cloud(ref_cloud[:, :], downsample_factor)
    downsampled_data_slave = downsample_point_cloud(slave_cloud[:, :], downsample_factor)

    # Split the data into coordinates (x, y, z) and RGB color
    coordinates_slave = downsampled_data_slave[:, :3]
    rgb_color_slave = downsampled_data_slave[:, 3:6]
    point_normals_slave = downsampled_data_slave[:, 6:]

    aspect_slave, slope_slave = calculate_aspect_slope(point_normals_slave)

    ######## EXTRACT STABLE TERRAIN BASED ON SLOPE & COLOR ##########

    # remove all points less steep than 60° 
    mask = slope_slave > 60
    stable_points_slave = downsampled_data_slave[mask]

    # remove all points which are on the cone
    min_bound = np.array([1.0107e6, 6.54465e6, 2700])  # Minimum bounds (adjust as needed)
    max_bound = np.array([1.0112e6, 6.5452e6, 3100])  # Maximum bounds (adjust as needed)
    stable_points_slave = filter_points_outside_box(stable_points_slave[:, :], min_bound, max_bound)
    min_bound = np.array([1.0106e6, 6.5445e6, 2900])  # Minimum bounds (adjust as needed)
    max_bound = np.array([1.0112e6, 6.5452e6, 3300])  # Maximum bounds (adjust as needed)
    stable_points_slave = filter_points_inside_box(stable_points_slave[:, :], min_bound, max_bound)
    min_bound = np.array([1.01105e6, 6.5444e6, 2600])  # Minimum bounds (adjust as needed)
    max_bound = np.array([1.0113e6, 6.5452e6, 3300])  # Maximum bounds (adjust as needed)
    stable_points_slave = filter_points_outside_box(stable_points_slave[:, :], min_bound, max_bound)

    # remove all points which are more blue than red
    grayscale_intensity_slave = np.mean(stable_points_slave[:, 3:6], axis=1)
    ndwi_slave = (stable_points_slave[:, 5]-stable_points_slave[:, 3])/(stable_points_slave[:, 3]+stable_points_slave[:, 5])

    #fig = plt.figure()
    #ax = fig.add_subplot(111)
    #ax.scatter(ndwi_slave[:], grayscale_intensity_slave[:], c=stable_points_slave[:, 3:6]/255, marker='.')
    #ax.plot(x_values, y_values, color='red', label='Line: y = ax + b')
    #ax.set_xlabel('NDWI')
    #ax.set_ylabel('INTENSITY')
    #ax.set_ylim(0, 255)
    #plt.show()

    mask = grayscale_intensity_slave-(ndwi_slave*a+b)<0
    stable_points_slave = stable_points_slave[mask]

    # Visualize the final point cloud
    fig = plt.figure()
    ax = fig.add_subplot(111, projection='3d')
    ax.scatter(stable_points_slave[:, 0], stable_points_slave[:, 1], stable_points_slave[:, 2], c=stable_points_slave[:, 3:6]/255, marker='.')
    ax.set_xlabel('X')
    ax.set_ylabel('Y')
    ax.set_zlabel('Z')
    plt.title('Zone de terrain stable - nuage "slave"')
    ax.view_init(elev=30, azim=30)  # Change the angles as needed
    plt.show()

    ####### COMPARE POINT CLOUDS (M3C2 ALGORITHM) #####################

    # Load point clouds into py4dgeo objects
    epoch_all_slave = py4dgeo.Epoch(downsampled_data_slave[:,:3])
    epoch_stable_slave = py4dgeo.Epoch(stable_points_slave[:,:3])

    # Instantiate and parametrize the M3C2 algorithm object
    m3c2 = py4dgeo.M3C2(
        epochs=(epoch_stable_ref, epoch_stable_slave),
        corepoints=epoch_stable_ref.cloud[::10],
        normal_radii=(2.5,),
        cyl_radii=(2.5,),
        max_distance=(30),  #quand on décoche ça, on a toutes les distances sur le cône
        #registration_error=(0.0),
    )

    # Run the distance computation
    m3c2_distances_stableparts, uncertainties_stableparts = m3c2.run()

    print(f"Median M3C2 distances STABLE: {np.nanmedian(m3c2_distances_stableparts):.3f} m")
    print(f"Std. dev. of M3C2 distances STABLE: {np.nanstd(m3c2_distances_stableparts):.3f} m")

    ## Instantiate and parametrize the M3C2 algorithm object
    #m3c2 = py4dgeo.M3C2(
    #    epochs=(epoch_all_ref, epoch_all_slave),
    #    corepoints=epoch_all_ref.cloud[::10],
    #    normal_radii=(2.5,),
    #    cyl_radii=(2.5,),
    #    max_distance=(30),
    #    #registration_error=(0.0),
    #)
#
    ## Run the distance computation
    #m3c2_distances_allparts_orig, uncertainties_allparts_orig = m3c2.run()
#
    #print(f"Median M3C2 distances ALL: {np.nanmedian(m3c2_distances_allparts_orig):.3f} m")
    #print(f"Std. dev. of M3C2 distances ALL: {np.nanstd(m3c2_distances_allparts_orig):.3f} m")


    # # PLOT DISTANCES
    # # Create a figure with 3D axis
    # fig, ax = plt.subplots(1, 1, subplot_kw={"projection": "3d"})
# 
    # # Plot the point cloud colored by height (z values)
    # s = ax.scatter(
    #     downsampled_data_ref[::10, 0],
    #     downsampled_data_ref[::10, 1],
    #     downsampled_data_ref[::10, 2],
    #     s=1,
    #     c=m3c2_distances_allparts_orig[::], vmin = 0, vmax=3 #on met vmax=3 quand on coche les max_distance ci-dessus
    # )
    # # Label axes and add title
    # ax.set_xlabel("X [m]")
    # ax.set_ylabel("Y [m]")
    # ax.set_zlabel("Z [m]")
# 
    # # Add a colorbar
    # fig.colorbar(s, shrink=0.5, aspect=10, label="M3C2 distance [m]", ax=ax, pad=0.2)
# 
    # # Set the start angles
    # ax.view_init(elev=30, azim=30)  # Change the angles as needed
    # plt.title('Distances M3C2 avant alignement')
    # ##plt.show()


    ########## COREGISTRATION #############

    # rotations allowed relative to camera origin
    CAM_coordinates = np.array([1011523.41,	6545566.751,	2985.720033])

    trafo = py4dgeo.iterative_closest_point(
        epoch_stable_ref, epoch_stable_slave, reduction_point=CAM_coordinates
    )
    epoch_all_slave_coreg = epoch_all_slave
    epoch_stable_slave_coreg = epoch_stable_slave

    epoch_all_slave_coreg.transform(trafo)
    epoch_stable_slave_coreg.transform(trafo)

    ########## RECALCULATE DIFFERENCES ##########

    # Instantiate and parametrize the M3C2 algorithm object
    m3c2 = py4dgeo.M3C2(
        epochs=(epoch_stable_ref, epoch_stable_slave_coreg),
        corepoints=epoch_stable_ref.cloud[::10],
        normal_radii=(2.5,),
        cyl_radii=(2.5,),
        max_distance=(30),
        #registration_error=(0.0),
    )

    # Run the distance computation
    m3c2_distances_stableparts, uncertainties_stableparts = m3c2.run()

    print(f"Median M3C2 distances STABLE: {np.nanmedian(m3c2_distances_stableparts):.3f} m")
    print(f"Std. dev. of M3C2 distances STABLE: {np.nanstd(m3c2_distances_stableparts):.3f} m")

    ## Instantiate and parametrize the M3C2 algorithm object
    #m3c2 = py4dgeo.M3C2(
    #    epochs=(epoch_all_ref, epoch_all_slave_coreg),
    #    corepoints=epoch_all_ref.cloud[::10],
    #    normal_radii=(2.5,),
    #    cyl_radii=(2.5,),
    #    max_distance=(30),
    #    #registration_error=(0.0),
    #)
#
    ## Run the distance computation
    #m3c2_distances_allparts, uncertainties_allparts = m3c2.run()
#
    #print(f"Median M3C2 distances ALL: {np.nanmedian(m3c2_distances_allparts):.3f} m")
    #print(f"Std. dev. of M3C2 distances ALL: {np.nanstd(m3c2_distances_allparts):.3f} m")

    ## PLOT DISTANCES
    ## Create a figure with 3D axis
    #fig, ax = plt.subplots(1, 1, subplot_kw={"projection": "3d"})
#
    ## Plot the point cloud colored by height (z values)
    #s = ax.scatter(
    #    downsampled_data_ref[::10, 0],
    #    downsampled_data_ref[::10, 1],
    #    downsampled_data_ref[::10, 2],
    #    s=1,
    #    c=m3c2_distances_allparts[::], vmin = 0, vmax=3
    #)
    ## Label axes and add title
    #ax.set_xlabel("X [m]")
    #ax.set_ylabel("Y [m]")
    #ax.set_zlabel("Z [m]")
#
    ## Add a colorbar
    #fig.colorbar(s, shrink=0.5, aspect=10, label="M3C2 distance [m]", ax=ax, pad=0.2)
#
    ## Set the start angles
    #ax.view_init(elev=30, azim=30)  # Change the angles as needed
#
    ## Show the plot
    #plt.tight_layout()
    #plt.title('Distances m3c2 après coregistration')
    ###plt.show()


    ######### RESAMPLE M3C2 DISTANCES TO A GRID & PLOT ###############

    ## Utiliser le colormap 'plasma' de Matplotlib
    #cmap = plt.get_cmap('plasma')
#
    ## Plot the resampled data 
    #fig, axs = plt.subplots(1, 2, figsize=(10, 5))
#
    #img = axs[0].scatter(downsampled_data_ref[::10, 0], downsampled_data_ref[::10, 1], s=1, c=m3c2_distances_allparts_orig[:], cmap=cmap, vmin = 0, vmax = 3)
    #axs[0].set_xlabel("X [m]")
    #axs[0].set_ylabel("Y [m]")
    #axs[0].set_title("Before coregistration")
    #axs[0].grid(True)
    #cbar = plt.colorbar(img, ax=axs[0], orientation='vertical')
    #cbar.set_label('M3C2 distance [m]')
#
#
    #img = axs[1].scatter(downsampled_data_ref[::10, 0], downsampled_data_ref[::10, 1], s=1, c=m3c2_distances_allparts[:], cmap=cmap, vmin = 0, vmax = 3)
    #axs[1].set_xlabel("X [m]")
    #axs[1].set_ylabel("Y [m]")
    #axs[1].set_title("After coregistration")
    #axs[1].grid(True)
    #cbar = plt.colorbar(img, ax=axs[1], orientation='vertical')
    #cbar.set_label('M3C2 distance [m]')
#
    #plt.tight_layout()
#
    #plt.show()

    ######## EXPORT COREGISTERED POINT CLOUD ###########
    coordinates_slave_coreg = epoch_all_slave_coreg.cloud
    rgb_color_slave = downsampled_data_slave[:, 3:6]
    point_normals_slave = downsampled_data_slave[:, 6:]

    slave_cloud_coreg = np.column_stack((coordinates_slave_coreg, rgb_color_slave, point_normals_slave))

    np.savetxt(PC_dir+slave_cloud_name+"_coreg_TL.txt", slave_cloud_coreg, fmt='%.2f %.2f %.2f %d %d %d %.6f %.6f %.6f')

    ######## CONVERT TO DEMs & EXPORT
    x_slave1,y_slave1,z_slave1=coordinates_slave_coreg[:, 0],coordinates_slave_coreg[:, 1],coordinates_slave_coreg[:, 2]

    zi_slave1_masked = interpolate_and_mask(x_slave1, y_slave1, z_slave1, xi_ref, yi_ref, res, max_gap_pixels)

    # Save as GeoTIFF
    transform = rasterio.transform.from_origin(xmin, ymax, res, res)
    crs_epsg = "EPSG:2154"  # RGF93 / Lambert-93

    try:
        save_dem(zi_slave1_masked,   dem_dir / f"DEM_{slave_cloud_name}_coreg_RGF93.tif")
    except RasterioIOError as e:
        if "Permission denied" in str(e):
            print("⚠️ Skipping file (permission denied)")
        else:
            print(f"⚠️ Rasterio error: {e}")

    ######## EXPORT ORTHOIMAGES
    try:
        save_ortho(x_slave1, y_slave1, rgb_color_slave, xi_ref, yi_ref, res, max_gap_pixels, dem_dir / f"ORTHO_{slave_cloud_name}_coreg_RGF93.tif")
    except RasterioIOError as e:
        if "Permission denied" in str(e):
            print("⚠️ Skipping file (permission denied)")
        else:
            print(f"⚠️ Rasterio error: {e}")

    print('Outputs saved')