# -*- coding: utf-8 -*-
"""
Simplified script to loop through DEMs, calculate dh relative to a reference,
and plot elevation change profiles.

@author: kneibm
"""
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pathlib 
import geoutils as gu
import geopandas as gpd
from rasterio import features
from rasterio.mask import mask as rio_mask
from datetime import datetime
import matplotlib.cm as cm
import matplotlib.colors as colors
import matplotlib.dates as mdates
from scipy.ndimage import binary_erosion
from scipy.ndimage import uniform_filter
import scipy.ndimage as ndi
from scipy.interpolate import griddata
from shapely.geometry import LineString
from typing import Dict, List, Tuple
from matplotlib.lines import Line2D
import xdem
import rasterio

# --- 1. CONFIGURATION & SWITCHES ---
#YEAR_SWITCH = 1        # 1 for 2023, 2 for 2024
PLOT_FONTSIZE = 16     # Increased fontsize
SMOOTHING_WINDOW = 10  # meters
OUTLIER_THRESH = 15    # meters
OUTLIER_DIST = 300     # distance threshold in meters
MAX_PIXEL_SIZE = 100   # Max gap size to interpolate in Ref DEM
reproj_res = 1
reproj_bounds = {"left": 1010500, "bottom": 6544500, "right": 1011226, "top": 6545200}
SAMPLE_DISTANCES = [120, 280, 500]
AOI_SHAPEFILE = "Z:/gl_kneibm/Projects/PI/2024_CAIRN-GLOBAL/TL_photogrammetry_Argentiere/data/GIS/from_Louise/Entire_cone.shp"
SUBMERGENCE_TIF = "Z:/gl_kneibm/Projects/PI/2024_CAIRN-GLOBAL/TL_photogrammetry_Argentiere/results/UAV/submergence/Submergence_2023.tif" # m/yr
#METEO_FILE = "Z:/gl_kneibm/Projects/PI/2024_CAIRN-GLOBAL/TL_photogrammetry_Argentiere/data/Meteo/Donnees_MeteoFrance/Donnees_journalieres_2023-2024/Q_74_previous-1950-2024_RR-T-Vent.csv.gz"
#PRECIP_FILE = "Z:/gl_kneibm/Projects/PI/2024_CAIRN-GLOBAL/TL_photogrammetry_Argentiere/data/Meteo/Donnees_MeteoFrance/Donnees_journalieres_2023-2024/Donnees_precip_journalieres_Chamonix_aout23-mai24.txt"
#TEMP_FILE = "Z:/gl_kneibm/Projects/PI/2024_CAIRN-GLOBAL/TL_photogrammetry_Argentiere/data/Meteo/Donnees_MeteoFrance/Donnees_journalieres_2023-2024/Chamonix_journalieres.xlsx"
METEO_FILE = "Z:/gl_kneibm/Projects/PI/2024_CAIRN-GLOBAL/TL_photogrammetry_Argentiere/data/GLACIOCLIM/AWS_Argentiere_upd.csv"
#POINTS_OF_INTEREST = {
#    "Top of cone": (1010738,  6544682), 
#    "LU":(1010918, 6544738),
#    "RU": (1010723, 6544882),
#    "CU": (1010788, 6544885),
#    "LD": (1011034, 6544854),
#    "CD": (1010880, 6544987),
#    "RD": (1010698, 6544993)
#} 
POINTS_OF_INTEREST = {
    "Top of cone": (1010738,  6544682), 
    "Center of cone": (1010839,  6544760),
    "Bottom of cone": (1011012,  6544896)
}# coordinates of the points at 120, 280 and 500 m along profile 2
BOX_SIZE = 50 # in meters, for spatial averaging

# Useful functions
def generate_dh_labels(time_labels, active_ref_date):
    """Generates 'Slave_Date - Ref_Date' labels for the legend."""
    labels = []
    for i, slave_date in enumerate(time_labels):
        labels.append(f'{active_ref_date} - {slave_date}')
    return labels

def apply_spatial_smoothing(raster_obj, box_size_m, res):
    """
    Applies a box-mean filter to the entire raster.
    """
    # Calculate box size in pixels
    pixel_size = int(box_size_m / res)
    if pixel_size < 1:
        return raster_obj.data
    
    # We use a copy of the data to avoid modifying the original
    data = raster_obj.data.copy()
    
    # Handle NaNs: uniform_filter doesn't ignore NaNs by default
    # We replace NaNs with 0, filter, then divide by the filtered mask
    mask = (~np.isnan(data)).astype(float)
    data_zeroed = np.nan_to_num(data)
    
    weighted_sum = uniform_filter(data_zeroed, size=pixel_size)
    weights = uniform_filter(mask, size=pixel_size)
    
    # Avoid division by zero and restore NaNs where no data was present
    with np.errstate(divide='ignore', invalid='ignore'):
        smoothed_data = weighted_sum / weights
        smoothed_data[weights == 0] = np.nan
        
    return smoothed_data

def sample_profile(dem, line: LineString, spacing=0.2, box_size=None):
    # Extract vertices
    x, y = line.xy
    
    # distances along vertices and total length
    dist_vert = np.r_[0, np.cumsum(np.sqrt(np.diff(x)**2 + np.diff(y)**2))]
    length = dist_vert[-1]

    # New sampling positions
    sample_dist = np.arange(0, length + 1e-8, spacing)  # include endpoint

    # Interpolate x,y positions along line
    x_s = np.interp(sample_dist, dist_vert, x)
    y_s = np.interp(sample_dist, dist_vert, y)

    ## Fill valid points
    if box_size is None or box_size <= 0:
        z_s = dem.interp_points((x_s,y_s))
    else:
        # Spatial box-mean sampling
        z_s = []
        half = box_size / 2
        for xi, yi in zip(x_s, y_s):
            extent = [xi - half, yi - half, xi + half, yi + half]
            try:
                # Using the geoutils crop method as seen in your get_mean_elevation helper
                subset = raster.crop(extent)
                z_s.append(np.nanmean(subset.data))
            except Exception:
                z_s.append(np.nan)
        z_s = np.array(z_s)

    return sample_dist, z_s

def interpolate_dem(dem):
    # Extract DEM data
    dem_data = dem.data  # Supposons que le DEM a une seule couche

    # Obtenir les coordonnées des pixels
    x = np.arange(dem_data.shape[1])
    y = np.arange(dem_data.shape[0])
    xx, yy = np.meshgrid(x, y)

    # Masquer les valeurs NaN pour l'interpolation
    valid_mask = ~np.isnan(dem_data)
    points = np.column_stack((xx[valid_mask], yy[valid_mask]))
    values = dem_data[valid_mask]

    # Interpoler les valeurs NaN
    dem_data_filled = griddata(points, values, (xx, yy), method='linear')

    return dem_data_filled

def identify_large_gaps(gap_mask: np.ndarray, max_size: int = 100) -> np.ndarray:
    """
    Identifies connected components (gaps) in a boolean mask that exceed a 
    specified maximum size (number of pixels).

    Args:
        gap_mask (np.ndarray): A 2D boolean NumPy array where True indicates
                               a gap (or "no data" area).
        max_size (int): The maximum number of pixels an area can have before 
                        it is considered a "large gap". Defaults to 100.

    Returns:
        np.ndarray: A new 2D boolean mask where True indicates areas from the 
                    original gap_mask that belong to connected components 
                    larger than max_size.
    """
    # 1. Label connected components
    # 'label' assigns a unique integer to each connected region (gap).
    # 'num_labels' is the total number of unique gaps found.
    labeled_array, num_labels = ndi.label(gap_mask) # <-- Use ndi.label
    
    # If no gaps are found, return an array of False
    if num_labels == 0:
        return np.zeros_like(gap_mask, dtype=bool)

    # 2. Calculate the size (sum of pixels) for each component
    # ndi.sum calculates the sum of the input array (gap_mask) for each unique label.
    # The third argument specifies the labels (indices) to sum over.
    component_sizes = ndi.sum(gap_mask, labeled_array, range(1, num_labels + 1)) # <-- Use ndi.sum (replaces the problematic 'sum')

    # 3. Identify labels that are too large
    # 'large_labels_mask' is a boolean array: True where component_size > max_size
    large_labels_mask = component_sizes > max_size
    
    # Create a mapping array: 
    # Index 0 is ignored (background). 
    # Index 1 to num_labels maps to the result of large_labels_mask
    label_is_large = np.insert(large_labels_mask, 0, False)
    
    # 4. Map the large labels back to the original array structure
    # This uses the labeled_array values as indices into the 'label_is_large' map.
    # The result is a mask where True is only assigned to the pixels belonging 
    # to the large components.
    large_gap_mask_output = label_is_large[labeled_array]

    return large_gap_mask_output

def parse_date_for_sort(label: str) -> datetime:
    """
    Extracts the comparison date (the second date) from the label string 
    and converts it to a datetime object for sorting.
    """
    try:
        # Split by ' - ' to isolate the reference date and the comparison date/label
        date_part = label.split(' - ')[1]
        
        # Remove the reference marker if present (e.g., '27/09/23 (Ref)' -> '27/09/23')
        date_str = date_part.replace(' (Ref)', '').strip()
        
        # Parse the DD/MM/YY format
        return datetime.strptime(date_str, '%d/%m/%y')
    except (IndexError, ValueError) as e:
        # Fallback for unexpected formats, assigning a very early date ensures they sort first
        print(f"Warning: Could not parse date from label '{label}'. Sorting as minimum value.")
        return datetime.min

def parse_date_to_day_of_year(label: str) -> int:
    """
    Extracts the comparison date (the second date) from the label and 
    returns its Day of the Year (1 for Jan 1st, up to 365/366).
    """
    try:
        # 1. Isolate the comparison date string
        date_part = label.split(' - ')[1]
        date_str = date_part.replace(' (Ref)', '').strip()
        
        # 2. Parse the DD/MM/YY format
        dt = datetime.strptime(date_str, '%d/%m/%y')
        
        # 3. Return the Day of the Year
        return dt.timetuple().tm_yday
    except (IndexError, ValueError) as e:
        # Handle the reference label or badly formatted strings
        if '(Ref)' in label:
            # For the reference line, use its actual Day of Year
            ref_date_str = label.split(' - ')[0]
            dt = datetime.strptime(ref_date_str, '%d/%m/%y')
            return dt.timetuple().tm_yday
        
        # Fallback for unexpected formats (e.g., set to a minimum DoY)
        return 1

def setup_normalized_data(profiles: Dict[str, List[Tuple[np.ndarray, np.ndarray]]], all_labels: List[str]):
    """
    Combines profile data, labels, and calculates the Day of Year (DoY) for 
    each line, sorting them for clean iteration.
    """
    processed_data = {}
    
    for title, profiles_list in profiles.items():
        combined = []
        for (dist, z), label in zip(profiles_list, all_labels):
            doy = parse_date_to_day_of_year(label)
            combined.append({
                'doy': doy,
                'dist': dist,
                'z': z,
                'label': label
            })
        
        # Sort by DoY to ensure the legend and plotting order is clean
        combined.sort(key=lambda x: x['doy'])
        processed_data[title] = combined
        
    return processed_data

def parse_date_to_datetime(label: str) -> datetime:
    """Extracts the comparison date and returns a datetime object."""
    try:
        date_part = label.split(' - ')[1]
        date_str = date_part.replace(' (Ref)', '').strip()
        return datetime.strptime(date_str, '%d/%m/%y')
    except:
        return datetime.min

def get_mean_elevation(raster: gu.Raster, x: float, y: float, box_size: float):
    """Extracts mean elevation in a square box around a point."""
    # Define the bounding box for the crop
    half = box_size / 2
    extent = [x - half, y - half, x + half, y + half]
    try:
        # Crop raster to the 10x10 area
        subset = raster.crop(extent)
        # Calculate mean ignoring NaNs
        return np.nanmean(subset.data)
    except Exception:
        return np.nan

# Load UAD DH
uav_dir = "Z:/gl_kneibm/Projects/PI/2024_CAIRN-GLOBAL/TL_photogrammetry_Argentiere/results/UAV/co-registered/"
uav_ref = xdem.DEM(uav_dir+"DEM_2023_09_27_ref_1m.tif")
uav_slave1 = xdem.DEM(uav_dir+"DEM_2023_05_04_coreg_1m.tif")
uav_slave2 = xdem.DEM(uav_dir+"DEM_2024_05_28_coreg_1m.tif")
uav_slave3 = xdem.DEM(uav_dir+"DEM_2024_10_23_coreg_1m.tif")
ortho_sept23 = rasterio.open(uav_dir+"ORTHO_2023_09_27_ref_1m.tif")

# Load cone shapefile
aoi_vector = gu.Vector(AOI_SHAPEFILE)

# Compute elevation difference
dhuav_slave1_ref = uav_ref - uav_slave1
dhuav_ref_slave2 = uav_slave2 - uav_ref
dhuav_slave2_slave3 = uav_slave3 - uav_slave2

# Paths
gis_dir = "Z:/gl_kneibm/Projects/PI/2024_CAIRN-GLOBAL/TL_photogrammetry_Argentiere/data/GIS/"
dir_base_slave = pathlib.Path("Z:/gl_kneibm/Projects/PI/2024_CAIRN-GLOBAL/TL_photogrammetry_Argentiere/results/DEM_LB/PhotoTL/Coreg_avec_PhotoTL_27-09")

# To avoid interpolation in plt.imshow
plt.rcParams['image.interpolation'] = 'none'

# Define all slave files and their corresponding plot labels
SLAVE_DEM_Y1_CONFIGS = [
    ("DEM_PC_TL2023-03-04_100002_coreg_RGF93.tif", '04/03/23'),
    ("DEM_PC_TL2023-03-16_130002_coreg_RGF93.tif", '16/03/23'),
    ("DEM_PC_TL2023-04-02_120003_coreg_RGF93.tif", '02/04/23'),
    ("DEM_PC_TL2023-04-14_110003_coreg_RGF93.tif", '14/04/23'),
    ("DEM_PC_TL2023-05-04_110003_coreg_RGF93.tif", '04/05/23'),
    ("DEM_PC_TL2023-05-17_100003_coreg_RGF93.tif", '17/05/23'),
    ("DEM_PC_TL2023-06-01_120003_coreg_RGF93.tif", '01/06/23'),
    ("DEM_PC_TL2023-07-03_110003_coreg_RGF93.tif", '03/07/23'),
    ("DEM_PC_TL2023-07-15_110003_coreg_RGF93.tif", '15/07/23'),
    ("DEM_PC_TL2023-08-03_100003_coreg_RGF93.tif", '03/08/23'),
    ("DEM_PC_TL2023-08-15_1000_coreg_RGF93.tif", '15/08/23'),
    ("DEM_PC_TL2023-09-03_120003_coreg_RGF93.tif", '03/09/23'),
    ("DEM_PC_TL2023-09-15_110000_coreg_RGF93.tif", '15/09/23'),
    ("DEM_PC_TL2023-09-27_130003_ref_RGF93.tif", "27/09/23"),
    ("DEM_PC_TL2023-10-15_120002_coreg_RGF93.tif", '15/10/23'),
    ("DEM_PC_TL2023-11-01_110003_coreg_RGF93.tif", '01/11/23'),
    ("DEM_PC_TL2023-11-13_120003_coreg_RGF93.tif", '13/11/23'),
    ("DEM_PC_TL2023-11-24_1200_coreg_RGF93.tif", '24/11/23'),
    ("DEM_PC_TL2023-12-15_130003_coreg_RGF93.tif", '15/12/23'),
    ("DEM_PC_TL2024-01-04_130003_coreg_RGF93.tif", '04/01/24'),
    ("DEM_PC_TL2024-01-13_140003_coreg_RGF93.tif", '13/01/24'),
    ("DEM_PC_TL2024-02-03_140003_coreg_RGF93.tif", '03/02/24'),
    ("DEM_PC_TL2024-02-17_110003_coreg_RGF93.tif", '17/02/24'),
    ("DEM_PC_TL2024-03-04_110003_coreg_RGF93.tif", '04/03/24')
]

SLAVE_DEM_Y2_CONFIGS = [
    ("DEM_PC_TL2024-03-04_110003_coreg_RGF93.tif", '04/03/24'),
    ("DEM_PC_TL2024-03-15_100000_coreg_RGF93.tif", '15/03/24'),
    ("DEM_PC_TL2024-04-02_130002_coreg_RGF93.tif", '02/04/24'),
    ("DEM_PC_TL2024-04-12_140003_coreg_RGF93.tif", '12/04/24'),
    ("DEM_PC_TL2024-05-03_110003_coreg_RGF93.tif", '03/05/24'),
    ("DEM_PC_TL2024-05-14_100003_coreg_RGF93.tif", '14/05/24'),
    ("DEM_PC_TL2024-05-28_150003_coreg_RGF93.tif", '28/05/24'),
    ("DEM_PC_TL2024-06-13_110003_coreg_RGF93.tif", '13/06/24'),
    ("DEM_PC_TL2024-06-16_110003_coreg_RGF93.tif", '16/06/24'),
    ("DEM_PC_TL2024-06-30_110000_coreg_RGF93.tif", '30/06/24'),
    ("DEM_PC_TL2024-07-14_110000_coreg_RGF93.tif", '14/07/24'),
    ("DEM_PC_TL2024-07-30_110000_coreg_RGF93.tif", '30/07/24'),
    ("DEM_PC_TL2024-08-15_110000_coreg_RGF93.tif", '15/08/24'),
    ("DEM_PC_TL2024-08-31_110003_coreg_RGF93.tif", '31/08/24'),
    ("DEM_PC_TL2024-09-15_110000_coreg_RGF93.tif", '15/09/24'),
    ("DEM_PC_TL2024-09-29_110000_coreg_RGF93.tif", '29/09/24'),
    ("DEM_PC_TL2024-10-12_120002_coreg_RGF93.tif", '12/10/24'),
    ("DEM_PC_TL2024-10-31_100002_coreg_RGF93.tif", '31/10/24'),
    ("DEM_PC_TL2024-11-15_120002_coreg_RGF93.tif", '15/11/24'),
    ("DEM_PC_TL2024-11-30_120002_coreg_RGF93.tif", '30/11/24'),
    ("DEM_PC_TL2024-12-16_120002_coreg_RGF93.tif", '16/12/24'),
    ("DEM_PC_TL2024-12-31_110002_coreg_RGF93.tif", '31/12/24'),
    ("DEM_PC_TL2025-01-15_110002_coreg_RGF93.tif", '15/01/25'),
    ("DEM_PC_TL2025-01-31_110002_coreg_RGF93.tif", '31/01/25'),
    ("DEM_PC_TL2025-02-15_110002_coreg_RGF93.tif", '15/02/25'),
    ("DEM_PC_TL2025-02-28_110002_coreg_RGF93.tif", '28/02/25')
]

# Year-specific configurations in a dictionary for easy looping
YEAR_CONFIGS = {
    "2023": {"ref_date": "27/09/23", "slaves": SLAVE_DEM_Y1_CONFIGS},
    "2024": {"ref_date": "29/09/24", "slaves": SLAVE_DEM_Y2_CONFIGS}
}

crev_files = ["crevasses_2023_05_04.shp", "crevasses_2023_09_27.shp", "crevasses_2024_05_28.shp", "crevasses_2024_10_23.shp"]

# --- 3. DATA LOADING & PROCESSING ---
# Data storage for time series
ts_data = [] # Will store {date, dist, dh}
aoi_ts_data = []

seasonal_colors = ['#4A86E8', '#1FD0B8', '#E69138', '#A61C00', '#4A86E8']
cmap = colors.LinearSegmentedColormap.from_list("seasonal_doy", seasonal_colors)
norm = colors.Normalize(vmin=1, vmax=366)

for year_str, config in YEAR_CONFIGS.items():
    print(f"\n--- Processing Year {year_str} ---")
    
    # 4.1 Setup Reference
    ref_file = next(f for f, l in config["slaves"] if l == config["ref_date"])
    dem_dh_ref = gu.Raster(dir_base_slave / ref_file).reproject(res=reproj_res, bounds=reproj_bounds, resampling="cubic")
    
    # Gap handling
    ref_gap_mask = np.isnan(dem_dh_ref.data)
    ref_gap_mask_eroded = binary_erosion(ref_gap_mask, iterations=1)
    large_gaps = identify_large_gaps(ref_gap_mask_eroded, MAX_PIXEL_SIZE)
    dem_dh_ref.data = interpolate_dem(dem_dh_ref.data)
    dem_dh_ref.data[large_gaps] = np.nan

    # 4.2 Setup Transects & Crevasses (static)
    transects = {f"Profile {i}": gpd.read_file(f"{gis_dir}Profile{i}.shp").geometry.iloc[0] for i in [1,2,3]}
    ref_profiles = {name: sample_profile(dem_dh_ref, line) for name, line in transects.items()}

    combined_crev = gpd.GeoDataFrame(pd.concat([gpd.read_file(gis_dir + f) for f in crev_files]), crs=dem_dh_ref.crs)
    crevasse_mask = features.rasterize([(g, 1) for g in combined_crev.geometry], 
                                    out_shape=dem_dh_ref.data.shape[:], 
                                    transform=dem_dh_ref.transform, fill=0, dtype='uint8')
    crevasse_raster = gu.Raster.from_array(crevasse_mask, dem_dh_ref.transform, dem_dh_ref.crs)
    
    # Process Profiles for this year
    year_profiles = {name: [] for name in transects.keys()}
    crev_profiles = {name: sample_profile(crevasse_raster, line) for name, line in transects.items()}
    
    for filename, label in config["slaves"]:
        print(f'processing {filename}')
        dem_slave = gu.Raster(dir_base_slave / filename).reproject(res=reproj_res, bounds=reproj_bounds, resampling="cubic")
        current_dt = parse_date_to_datetime(f"{config['ref_date']} - {label}")

        # We calculate the difference raster once for the spatial box-mean extraction
        dh_raster_full = dem_slave - dem_dh_ref
        
        # --- AOI SHAPEFILE EXTRACTION ---
        try:
            # Crop/Mask the dh_raster using the shapefile geometry
            cone_mask = aoi_vector.create_mask(dh_raster_full)
            dh_copy = dh_raster_full.copy()
            dh_copy[(cone_mask == 0)] = np.nan
            dh_copy = dh_copy.data[~np.isnan(dh_copy.data)]
            
            aoi_mean_dh = np.nanmean(dh_copy.data)
            
            aoi_ts_data.append({
                'date': current_dt,
                'label': label,
                'mean_dh': aoi_mean_dh,
                'year': year_str
            })
        except Exception as e:
            print(f"AOI extraction failed for {label}: {e}")


        # --- PROFILE EXTRACTION ---
        for name, line in transects.items():
            dist, z_slave = sample_profile(dem_slave, line)
            dh = z_slave - ref_profiles[name][1]
            dh[(dist > OUTLIER_DIST) & (np.abs(dh) > OUTLIER_THRESH)] = np.nan
            
            ## Smoothing
            window = int(SMOOTHING_WINDOW / 0.2)
            dh_sm = pd.Series(dh).rolling(window=window, center=True, min_periods=1).mean().values
            year_profiles[name].append({'dist': dist, 'z': dh_sm, 'doy': current_dt.timetuple().tm_yday, 'label': label})
            
            # 2/ TIME SERIES EXTRACTION (Spatial Box Mean - Profile 2 only)
            if name == "Profile 2":
                for d_target in SAMPLE_DISTANCES:
                    # Get exact (x, y) at the target distance along the line
                    target_point = line.interpolate(d_target)
                    tx, ty = target_point.x, target_point.y

                    # Define 50x50m box
                    half = 50 / 2 
                    extent = [tx - half, ty - half, tx + half, ty + half]

                    try:
                        # Extract spatial mean from the difference raster
                        box_subset = dh_raster_full.crop(extent)
                        # np.nanmean handles NaNs inside the box robustly
                        spatial_dh = np.nanmean(box_subset.data)
                    except Exception:
                        # Fallback if crop is outside bounds
                        spatial_dh = np.nan

                    ts_data.append({
                        'date': current_dt,
                        'dist_bin': d_target,
                        'dh': spatial_dh
                    })

    # 4.3 PLOTTING (One Fig per Year)
    fig, axs = plt.subplots(3, 1, figsize=(14, 20), constrained_layout=True)

    for ax, (title, data_list) in zip(axs, year_profiles.items()):
        # Crevasse Shading
        dist_c, val_c = crev_profiles[title]
        ax.fill_between(dist_c, -40, 40, where=(val_c > 0), color='gray', alpha=0.15, label='Crevasses')

        for item in data_list:
            ax.plot(item['dist'], item['z'], color=cmap(norm(item['doy'])), linewidth=2, alpha=0.9)

        if title == "Profile 2":
            for d in SAMPLE_DISTANCES:
                ax.axvline(d, color='black', linestyle=':', linewidth=2.5, alpha=0.8)

        ax.set_title(title, fontsize=PLOT_FONTSIZE, fontweight='bold')
        ax.set_ylabel("Elevation Change (m)", fontsize=PLOT_FONTSIZE)
        ax.tick_params(labelsize=PLOT_FONTSIZE)
        ax.set_ylim(-10, 35)
        ax.set_xlim(0, 600)
        ax.grid(True, alpha=0.3)

    # Add Colorbar
    sm = cm.ScalarMappable(cmap=cmap, norm=norm)
    cbar = fig.colorbar(sm, ax=axs, location='right', shrink=0.7, ticks=[1, 91, 182, 274, 366])
    cbar.ax.set_yticklabels(['Jan 1', 'Apr 1', 'Jul 1', 'Oct 1', 'Dec 31'])
    cbar.ax.tick_params(labelsize=PLOT_FONTSIZE)

    
    fig.suptitle(f"Elevation Changes - Reference {config['ref_date']}", fontsize=20, fontweight='bold')

    plt.show()


    # Hovmöller diagram
    common_dist = np.linspace(0, 600, 600) # Adjust 600 to your max distance

    fig, axs = plt.subplots(3, 1, figsize=(16, 18), constrained_layout=True)

    for ax, (title, data_list) in zip(axs, year_profiles.items()):
        # 2. Extract and Sort Data by Time (X-axis)
        data_list = sorted(data_list, key=lambda x: x['doy'])
        doys = [item['doy'] for item in data_list]
        
        # Create the 2D grid: Rows = Distance, Columns = Time
        # We build it by interpolating each time slice onto our distance grid
        z_matrix = []
        for item in data_list:
            z_interp = np.interp(common_dist, item['dist'], item['z'])
            z_matrix.append(z_interp)
        
        # Convert to array and Transpose so shape is (len(common_dist), len(doys))
        z_matrix = np.array(z_matrix).T 

        # 3. Plotting
        # X = Time, Y = Distance, Color = Elevation Change
        mesh = ax.pcolormesh(doys, common_dist, z_matrix, cmap='RdBu', 
                            shading='gouraud', vmin=-10, vmax=10)

        # 4. Vertical Crevasse Shading (since Distance is now the Y-axis)
        dist_c, val_c = crev_profiles[title]
        ax.fill_betweenx(dist_c, doys[0], doys[-1], where=(val_c > 0), 
                        color='black', alpha=0.1, label='Crevasses')

        ax.set_title(f"Spatiotemporal Change: {title}", fontsize=16, fontweight='bold')
        ax.set_xlabel("Day of Year", fontsize=14)
        ax.set_ylabel("Distance along profile (m)", fontsize=14)
        
        # Set X-ticks to match your previous colorbar style
        ax.set_xticks([1, 91, 182, 274, 366])
        ax.set_xticklabels(['Jan 1', 'Apr 1', 'Jul 1', 'Oct 1', 'Dec 31'])

    # Add a single colorbar for the whole figure
    cbar = fig.colorbar(mesh, ax=axs, location='right', shrink=0.6)
    cbar.set_label("Elevation Change (m)", fontsize=14)

    plt.show()


# --- LOAD METEO DATA ---
df_meteo = pd.read_csv(METEO_FILE, 
                       encoding='utf-8-sig', 
                       sep=';')
df_meteo.columns = df_meteo.columns.str.strip()
df_meteo['TIMESTAMP'] = pd.to_datetime(df_meteo['TIMESTAMP'], dayfirst=True)
df_meteo.columns = ['TIMESTAMP', 'TM', 'RR']
df_meteo['TM'] = pd.to_numeric(df_meteo['TM'], errors='coerce')
df_meteo['RR'] = pd.to_numeric(df_meteo['RR'], errors='coerce')
print(df_meteo.info())
print(df_meteo.head())

#chamonix_df = df_meteo[df_meteo['NOM_USUEL'] == 'CHAMONIX'].copy()
#print(chamonix_df.head())
#
#cols_to_keep = ['AAAAMMJJ', 'TM', 'RR']
#chamonix_df = chamonix_df[cols_to_keep]
#
## Convert temperatures/precip from 1/10ths to standard units
#chamonix_df['TM'] = chamonix_df['TM'] 
#chamonix_df['RR'] = chamonix_df['RR'] 
#
## convert date
#chamonix_df['date'] = pd.to_datetime(chamonix_df['AAAAMMJJ'], format='%Y%m%d')

# Adjusting from Chamonix (1042m) to Bergschrund
#chamonix_df['TM'] = chamonix_df['TM'] + (-0.0065 * (3150 - 1042))

# Aggregate to month-end ('ME')
df_meteo = df_meteo.set_index('TIMESTAMP')
df_precip_monthly = df_meteo['RR'].resample('MS').sum()
df_temp_monthly = df_meteo['TM'].resample('MS').mean()

# Shift date from 1st day of month to middle of the month
df_temp_monthly.index = df_temp_monthly.index + pd.Timedelta(days=14)
df_precip_monthly.index = df_precip_monthly.index + pd.Timedelta(days=14)

# --- MASS BALANCE TIME SERIES
# Load Submergence Velocity
v_sub_raster = gu.Raster(SUBMERGENCE_TIF)
v_sub_values = {name: get_mean_elevation(v_sub_raster, px, py, BOX_SIZE) 
                for name, (px, py) in POINTS_OF_INTEREST.items()}
cone_mask = aoi_vector.create_mask(v_sub_raster)
v_sub_aoi = v_sub_raster.copy()
v_sub_aoi[(cone_mask == 0)] = np.nan
v_sub_aoi = v_sub_aoi.data[~np.isnan(v_sub_aoi.data)]
v_sub_aoi = np.nanmean(v_sub_aoi.data)

#point_x = [1010738, 1010918, 1010723, 1010788, 1011034, 1010880, 1010698]
#point_y = [6544682, 6544738, 6544882, 6544885, 6544854, 6544987, 6544993]
point_x = [1010713, 1010839, 1011012]
point_y = [6544661, 6544760, 6544896]
from shapely.geometry import Point
geometry = [Point(x, y) for x, y in zip(point_x, point_y)]
gdf = gpd.GeoDataFrame(geometry=geometry, crs=v_sub_raster.crs)
boxes = gdf.buffer(distance=25, cap_style=3)

fig, ax = plt.subplots(figsize=(10, 8))
v_sub_raster.plot(ax=ax, cmap='RdBu', vmin=-30, vmax=30, cbar_title="Elevation Change (m)")
boxes.boundary.plot(ax=ax, color='black', linewidth=1.5, label='20x20m Sample Area')
gdf.plot(ax=ax, color='yellow', markersize=5)
plt.legend()
plt.show()


# --- submergence ---
df_ts = pd.DataFrame(ts_data)
df_ts_aoi = pd.DataFrame(aoi_ts_data)

dist_to_name = {
    120: "Top of cone",
    280: "Center of cone",
    500: "Bottom of cone"
}

df_elev = df_ts.pivot_table(index='date', columns='dist_bin', values='dh', aggfunc='mean')
df_elev_aoi = df_ts_aoi.pivot_table(index='date', values='mean_dh', aggfunc='mean')

# Rename columns for clarity
df_elev.columns = df_elev.columns.astype(int) # Ensure 120.0 becomes 120
df_elev = df_elev.rename(columns=dist_to_name)

# Sort the index to ensure chronological order
df_elev = df_elev.sort_index()
df_elev_aoi = df_elev_aoi.sort_index()

# dh_corrected = (z_obs - (v_sub * time_delta_years))* density
density = 0.55
ref_date = df_elev.index[0]
df_corrected = df_elev.copy()
df_aoi_corrected = df_elev_aoi.copy()

years_passed = (df_elev.index - ref_date).days / 365.25
for name in POINTS_OF_INTEREST.keys():
    # Subtract the cumulative emergence/submergence 
    # (Note: if v_sub is negative for submergence, subtracting it adds elevation back)
    df_corrected[name] = (df_elev[name] - (v_sub_values[name] * years_passed))*density

df_aoi_corrected['mean_dh'] = (df_elev_aoi['mean_dh'] - (v_sub_aoi * years_passed))*density

# Subtract the first valid elevation value from each column to show change (dh)
first_valid_values = df_corrected.bfill().iloc[0]
df_corrected = df_corrected - first_valid_values

first_valid_values_aoi = df_aoi_corrected.bfill().iloc[0]
df_aoi_corrected = df_aoi_corrected - first_valid_values_aoi

# Reindex to daily to ensure the 40-day window is time-accurate
df_daily_interp = df_corrected.reindex(pd.date_range(df_corrected.index.min(), df_corrected.index.max(), freq='D')).interpolate(method='linear')
df_smooth = df_daily_interp.rolling(window=40, center=True, min_periods=1).mean()

df_daily_interp_aoi = df_aoi_corrected.reindex(pd.date_range(df_aoi_corrected.index.min(), df_aoi_corrected.index.max(), freq='D')).interpolate(method='linear')
df_smooth_aoi = df_daily_interp_aoi.rolling(window=40, center=True, min_periods=1).mean()

# ---- Avalanches observations

# Setup Categorical Mapping for Avalanches
# Order: Top to Bottom (T, LU, CU, RU, LD, CD, RD)
sector_order = ['T', 'LU', 'CU', 'RU', 'LD', 'CD', 'RD']
sector_y = {s: i for i, s in enumerate(reversed(sector_order))}

size_colors = {
    'small': '#ffcccc',   # Light Red
    'medium': '#ff6666',  # Medium Red
    'large': '#cc0000'    # Dark Red
}
cone_sectors = ['T', 'CU', 'LU', 'RU', 'LD', 'CD', 'RD']

# Load Avalanche Excel file
# Replace 'path_to_your_file.xlsx' with your actual file path
df_avalanche = pd.read_excel(r'Z:\gl_kneibm\Projects\PI\2024_CAIRN-GLOBAL\TL_photogrammetry_Argentiere\data\TLCAM\Qualitative_obs\Arg_avalancheTL.xlsx')

# Extract the date from the 'file_name' column
# The regex r'(\d{4}-\d{2}-\d{2})' looks for the pattern YYYY-MM-DD
df_avalanche['datetime'] = pd.to_datetime(
    df_avalanche['file_name'].str.extract(r'(\d{4}-\d{2}-\d{2})')[0]
)

# Sort by date to ensure the plot lines up correctly
df_avalanche = df_avalanche.sort_values('datetime')

# Display the first few rows to verify
print(df_avalanche.head())


# --- UNCERTAINTY CALCULATIONS ---
mu = 1.8
sigma_raw = 6.8
n_eff = 16.5
n_eff_aoi = 1197
sigma_dh = np.sqrt(mu**2 + (sigma_raw**2 / np.sqrt(n_eff)))
sigma_dh_aoi = np.sqrt(mu**2 + (sigma_raw**2 / np.sqrt(n_eff_aoi)))

# Constants for SMB propagation
sigma_rho = 0.08  # Converting 80 kg/m3 to t/m3 to match density 0.55
sigma_s = 1.0 * 365/146    # submergence was calculated over a period of 146 days

# --- TIME SERIES PLOT (The Whole 2 Years) ---

# Define unique styles for the 3 points
point_names = list(POINTS_OF_INTEREST.keys())
plot_colors = ['#1f77b4', '#ff7f0e', '#2ca02c'] # Blue, Orange, Green
line_styles = ['-', '-', '-'] # Solid, Dashed, Dotted

# Setup Figure: 4 subplots 
fig = plt.figure(figsize=(20, 14))
gs = fig.add_gridspec(4, 4, width_ratios=[1, 1, 1, 1.2], hspace=0.3)

ax_meteo = fig.add_subplot(gs[0, :3])
ax_ava   = fig.add_subplot(gs[1, :3], sharex=ax_meteo)
ax_elev  = fig.add_subplot(gs[2, :3], sharex=ax_meteo)
ax_smb   = fig.add_subplot(gs[3, :3], sharex=ax_meteo)
ax_map   = fig.add_subplot(gs[2:, 3]) # Map positioned in the bottom right
ax_leg   = fig.add_subplot(gs[:2, 3]) # Legend area in the top right
ax_leg.axis('off')

# Meteo Data
# Precipitation (Bars)
ax_meteo.bar(df_precip_monthly.index, df_precip_monthly, width=20, 
             color='royalblue', alpha=0.3, label='Monthly Precip')
ax_meteo.set_ylabel("Precipitation (mm)", color='royalblue', fontsize=14)

# Temperature (Twin Axis)
ax_temp = ax_meteo.twinx()
ax_temp.plot(df_temp_monthly.index, df_temp_monthly, color='crimson', 
             marker='o', markersize=4, linewidth=1.5, label='Monthly Temperature')
ax_temp.set_ylabel("Temperature (°C)", color='crimson', fontsize=14)
ax_temp.axhline(0, color='black', linestyle='--', linewidth=1)
ax_meteo.tick_params(axis='both', which='major', labelsize=12)

#  Avalanche Occurrence 
for _, row in df_avalanche.iterrows():
    y_val = sector_y.get(row['sector'])
    if y_val is not None:
        color = size_colors.get(row['size_class'], 'red')
        edge = 'none' if row['release_location'] in cone_sectors else 'black'
        
        ax_ava.scatter(row['datetime'], y_val, color=color, edgecolors=edge, 
                       linewidths=1.2, s=120, marker='s', zorder=5)

# Formatting the Avalanche Axis
ax_ava.set_yticks(list(sector_y.values()))
ax_ava.set_yticklabels(list(sector_y.keys()))
ax_ava.set_ylim(-0.5, len(sector_order) - 0.5)
ax_ava.set_ylabel("Deposit Sector", fontsize=14)
ax_ava.tick_params(axis='both', which='major', labelsize=12)

# Grouping Lines
ax_ava.axhline(y=5.5, color='black', linestyle='--', linewidth=0.8, alpha=0.4) # Separator above LU
ax_ava.axhline(y=2.5, color='black', linestyle='--', linewidth=0.8, alpha=0.4) # Separator above LD

# Avalanche Legend
ava_legend_elements = [
    Line2D([0], [0], marker='s', color='w', label='Small', markerfacecolor=size_colors['small'], markersize=8),
    Line2D([0], [0], marker='s', color='w', label='Medium', markerfacecolor=size_colors['medium'], markersize=8),
    Line2D([0], [0], marker='s', color='w', label='Large', markerfacecolor=size_colors['large'], markersize=8),
    Line2D([0], [0], marker='s', color='w', label='Upslope release', 
           markerfacecolor='gray', markeredgecolor='black', markeredgewidth=1, markersize=8),
]
ax_ava.grid(axis='x', alpha=0.2)

# Elevation 
df_daily_interp_elev = df_elev.reindex(pd.date_range(df_elev.index.min(), df_elev.index.max(), freq='D')).interpolate(method='linear')
df_smooth_elev = df_daily_interp_elev.rolling(window=40, center=True, min_periods=1).mean()

df_daily_interp_elev_aoi = df_elev_aoi.reindex(pd.date_range(df_elev_aoi.index.min(), df_elev_aoi.index.max(), freq='D')).interpolate(method='linear')
df_smooth_elev_aoi = df_daily_interp_elev_aoi.rolling(window=40, center=True, min_periods=1).mean()

for (name, color) in zip(POINTS_OF_INTEREST.keys(), plot_colors):
    # Scatter for raw data
    ax_elev.errorbar(df_elev.index, df_elev[name], yerr = sigma_dh, fmt='none',
                       color=color, alpha=0.3, ecolor=color, elinewidth=1.5, capsize=2)
    # Line for the 60d smooth trend
    ax_elev.plot(df_smooth_elev.index, df_smooth_elev[name], 
                    color=color, linewidth=2.5, label=f'{name}')
ax_elev.errorbar(df_elev_aoi.index, df_elev_aoi['mean_dh'], yerr = sigma_dh_aoi, fmt='none',
                       color='black', alpha=0.3, ecolor='black', elinewidth=1.5, capsize=2)
# Line for the 60d smooth trend
ax_elev.plot(df_smooth_elev_aoi.index, df_smooth_elev_aoi['mean_dh'], 
                color='black', linewidth=2.5, label='Entire cone')
ax_elev.set_ylabel("Elevation change (m)", fontsize=14)
ax_elev.tick_params(axis='both', which='major', labelsize=12)
ax_elev.grid(True, alpha=0.2)

# SMB

# Applying: MB = (dh - (v_sub * years)) * density
# Propagated Sigma: sqrt( (MB/rho * sigma_rho)^2 + (rho * t * sigma_s)^2 + (rho * sigma_dh)^2 )

for i, (name, color) in enumerate(zip(POINTS_OF_INTEREST.keys(), plot_colors)):
    # Density uncertainty
    term_rho = ((df_corrected[name] / density) * sigma_rho )**2
    term_dh_s = (density * np.sqrt(sigma_dh**2 + (sigma_s*(df_corrected.index - ref_date).days / 365.25)**2))**2
    current_sigma_smb = np.sqrt(term_rho + term_dh_s)

    # Scatter for raw data (subtle)
    ax_smb.errorbar(df_corrected.index, df_corrected[name], yerr=current_sigma_smb,
                       color=color, alpha=0.3, fmt='none', ecolor=color, elinewidth=1.5, capsize=2)
    # Line for the 60d smooth trend
    ax_smb.plot(df_smooth.index, df_smooth[name], 
                    color=color, linewidth=2.5, label=f'{name}')

# whole cone

# Density uncertainty
term_rho = ((df_aoi_corrected['mean_dh'] / density) * sigma_rho)**2
term_dh_s = (density * np.sqrt(sigma_dh_aoi**2 + (sigma_s*(df_aoi_corrected.index - ref_date).days / 365.25)**2))**2
current_sigma_smb = np.sqrt(term_rho + term_dh_s)

# Scatter for raw data (subtle)
ax_smb.errorbar(df_aoi_corrected.index, df_aoi_corrected['mean_dh'], yerr=current_sigma_smb,
                    color='black', alpha=0.3, fmt='none', ecolor='black', elinewidth=1.5, capsize=2)
# Line for the 60d smooth trend
ax_smb.plot(df_smooth_aoi.index, df_smooth_aoi['mean_dh'], 
                color='black', linewidth=2.5, label='Entire cone')

ax_smb.set_ylabel("Cumulative MB (m w. eq.)", fontsize=14)
ax_smb.set_xlabel("Time", fontsize=14)
ax_smb.grid(True, alpha=0.2)
ax_smb.tick_params(axis='both', which='major', labelsize=12)

# Global Settings
ax_smb.set_xlim(pd.Timestamp('2023-02-01'), pd.Timestamp('2025-04-01'))

# --- MAP (Right Side) ---
rasterio.plot.show(ortho_sept23, ax=ax_map, cmap='gray', alpha=0.8)
for i, (color, ls) in enumerate(zip(plot_colors, line_styles)):
    boxes.iloc[[i]].plot(ax=ax_map, facecolor='none', edgecolor=color, 
                         linestyle=ls, linewidth=2)

aoi_vector.plot(ax=ax_map, facecolor="none", edgecolor="black", linewidth=2, alpha=0.8)

ax_map.set_xlabel("Easting (m)", fontsize=14)
ax_map.set_ylabel("Northing (m)", fontsize=14)
ax_map.yaxis.tick_right()
ax_map.yaxis.set_label_position("right")
ax_map.ticklabel_format(useOffset=False, style='plain')
plt.setp(ax_map.get_yticklabels(), rotation=30, ha='left') 
ax_map.tick_params(axis='both', which='major', labelsize=12)

# --- 5. CENTRALIZED LEGEND ---
# Moving legends to the ax_leg space to clean up the plots
handles_elev, labels_elev = ax_elev.get_legend_handles_labels()

ax_leg.legend(handles=handles_elev + ava_legend_elements, 
              labels=labels_elev + [e.get_label() for e in ava_legend_elements],
              loc='center', fontsize=16, frameon=True)

plt.gcf().autofmt_xdate()
plt.tight_layout()

# Set format to 'Day Month Year' (e.g., 15 Feb 2023)
ax_meteo.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
ax_meteo.xaxis.set_major_locator(mdates.MonthLocator(interval=3))

plt.show()





### Calculate the precipitation accumulating on headwall
START_DATE = '2023-03-01'
area_face = 180438 # m2
area_cone = 160534 # m2

df_filtered = df_meteo.loc[START_DATE:].copy()

# Load spatial data
dem = rasterio.open('Z:/glazio/projects/8045-VAW_CAIRN-GLOBAL/SMB_inversions/2024_Argentiere/argentiere_pleiades_smb/data/dem_lowres/Mt_Blanc_small_UTM32N.tif')
shapefile = gpd.read_file('Z:/gl_kneibm/Projects/PI/2024_CAIRN-GLOBAL/TL_photogrammetry_Argentiere/data/GIS/from_Louise/Aire_face_utm32N.shp')
aoi_shapefile = gpd.read_file('Z:/gl_kneibm/Projects/PI/2024_CAIRN-GLOBAL/TL_photogrammetry_Argentiere/data/GIS/from_Louise/Entire_cone_utm32N.shp')

# Ensure CRS matches
shapefile = shapefile.to_crs(dem.crs)

# Mask the DEM to the shapefile area
out_image, out_transform = rio_mask(dem, shapefile.geometry, crop=True)
dem_data = out_image[0]

out_image, out_transform = rio_mask(dem, aoi_shapefile.geometry, crop=True)
aoi_data = out_image[0]

# Replace NoData values with NaN for calculations
dem_data = dem_data.astype('float32')
dem_data[(dem_data == dem.nodata) | (dem_data==0)] = np.nan

plt.figure(figsize=(10, 8))
plt.imshow(dem_data, cmap='terrain')
plt.colorbar(label='Elevation (m)')
plt.title("Masked DEM Area")
plt.show()

aoi_data = aoi_data.astype('float32')
aoi_data[(aoi_data == dem.nodata) | (aoi_data==0)] = np.nan

plt.figure(figsize=(10, 8))
plt.imshow(aoi_data, cmap='terrain')
plt.colorbar(label='Elevation (m)')
plt.title("Masked DEM Area")
plt.show()

# Define the reference elevation where df_meteo was recorded
REF_ELEVATION = 2435  
LAPSE_RATE = -0.0065  # K/m

results = []
results_aoi = []

for index, row in df_filtered.iterrows():
    t_ref = row['TM']
    p_ref = row['RR'] / 1000.0  # Convert mm to m w.e.
    
    if np.isnan(t_ref) or np.isnan(p_ref):
        results.append(np.nan)
        results_aoi.append(np.nan)
        continue

    # Distribute temperature across the DEM
    t_dist = t_ref + LAPSE_RATE * (dem_data - REF_ELEVATION)
    t_aoi = t_ref + LAPSE_RATE * (aoi_data - REF_ELEVATION)
    
    # Calculate Snow Fraction (fs)
    # Start with 0, then fill based on conditions
    fs = np.where(t_dist <= 0, 1.0, 
         np.where(t_dist >= 2, 0.0, 
         1.0 - (t_dist / 2.0)))
    fs_aoi = np.where(t_aoi <= 0, 1.0, 
         np.where(t_aoi >= 2, 0.0, 
         1.0 - (t_aoi / 2.0)))
    
    # Calculate snow depth (m w.e.) per pixel
    snow_pixels = fs * p_ref
    snow_pixels_aoi = fs_aoi * p_ref
    
    # Store the mean snow depth over the shapefile area
    results.append(np.nanmean(snow_pixels))
    results_aoi.append(np.nanmean(snow_pixels_aoi))

df_filtered['snow_m_we'] = results
df_filtered['cum_snow_m_we'] = df_filtered['snow_m_we'].fillna(0).cumsum()*area_cone/area_face
df_filtered['snow_m_we_aoi'] = results_aoi
df_filtered['cum_snow_m_we_aoi'] = df_filtered['snow_m_we_aoi'].fillna(0).cumsum()
df_filtered['sum_snowfall'] = df_filtered['cum_snow_m_we_aoi']+df_filtered['cum_snow_m_we']

# add density
density = 0.5
density_err = 0.08

periods = [
    {'start': '2023-05-04', 'end': '2023-09-27', 'depth': 6.6},
    {'start': '2024-05-29', 'end': '2024-10-23', 'depth': 5.7}
]

# Initialize arrays for ablation and uncertainty
ablation_series = np.zeros(len(df_filtered))
uncertainty_series = np.zeros(len(df_filtered))

# Calculate linear daily loss for each period
for p in periods:
    mask = (df_filtered.index >= p['start']) & (df_filtered.index <= p['end'])
    num_days = mask.sum()
    
    if num_days > 0:
        total_we = p['depth'] * density
        total_err = p['depth'] * density_err
        
        # Calculate daily loss (negative)
        daily_loss = -total_we / num_days
        daily_err = total_err / num_days
        
        # Apply only to the specific period
        ablation_series[mask] = daily_loss
        uncertainty_series[mask] = daily_err

# Calculate cumulative patterns
df_filtered['cum_ablation'] = np.cumsum(ablation_series)
df_filtered['cum_uncertainty'] = np.cumsum(uncertainty_series)

# Net Mass Balance = Accumulation (Snow) + Ablation (Negative)
df_filtered['net_mass_balance'] = df_filtered['sum_snowfall'] + df_filtered['cum_ablation']

plt.figure(figsize=(12, 6))
ax = plt.gca()
plt.plot(df_filtered.index, df_filtered['net_mass_balance'], 
         color='navy', linewidth=2, label='Mass balance from AWS data')
plt.plot(df_filtered.index, df_filtered['sum_snowfall'], 
         color='green', linewidth=2, label='Accumulation only from AWS data')
plt.errorbar(df_aoi_corrected.index, df_aoi_corrected['mean_dh'], yerr=current_sigma_smb,
        color='black', alpha=0.3, fmt='none', ecolor='black', elinewidth=1.5, capsize=2)
plt.plot(df_smooth_aoi.index, df_smooth_aoi['mean_dh'], 
                color='black', linewidth=2.5, label='Mass balance from photogrammetry')
plt.xlabel('Time', fontsize = 14)
plt.ylabel('Cumulative mass balance [m w.e.]', fontsize = 14)
plt.grid(True, linestyle='--', alpha=0.7)
plt.xlim(pd.Timestamp('2023-02-01'), pd.Timestamp('2025-04-01'))
ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
plt.legend()
plt.show()




# Metrics
total_nov = df_smooth.loc['2023-11-30', 'Top of cone']-df_smooth.loc['2023-11-01', 'Top of cone']


term_rho = ((df_corrected.loc['2023-11-13', 'Top of cone'] / density) * sigma_rho )**2
term_dh_s = (density * np.sqrt(sigma_dh**2 + (sigma_s*(df_corrected.index[16] - ref_date).days / 365.25)**2))**2
current_sigma_smb = np.sqrt(term_rho + term_dh_s)

print(f"Total accumulation in Nov 2023: {total_nov} +/- {current_sigma_smb}")

cum_mb_feb24 =  df_smooth.loc['2024-02-28', 'Center of cone']

term_rho = ((df_corrected.loc['2024-03-04', 'Center of cone'] / density) * sigma_rho )**2
term_dh_s = (density * np.sqrt(sigma_dh**2 + (sigma_s*(df_corrected.index[23] - ref_date).days / 365.25)**2))**2
current_sigma_smb = np.sqrt(term_rho + term_dh_s)

print(f"Cumulated MB year 1: {cum_mb_feb24} +/- {current_sigma_smb}")

cum_mb_feb25 =  df_smooth.loc['2025-02-28', 'Center of cone']-df_smooth.loc['2024-02-28', 'Center of cone']

term_rho = (((df_corrected.loc['2025-02-28', 'Center of cone']-df_corrected.loc['2024-03-04', 'Center of cone']) / density) * sigma_rho )**2
term_dh_s = (density * np.sqrt(sigma_dh**2 + (sigma_s*1)**2))**2
current_sigma_smb = np.sqrt(term_rho + term_dh_s)

print(f"Cumulated MB year 1: {cum_mb_feb25} +/- {current_sigma_smb}")

cum_mb_feb24 =  df_smooth_aoi.loc['2024-02-28']

term_rho = ((df_aoi_corrected.loc['2024-03-04'] / density) * sigma_rho )**2
term_dh_s = (density * np.sqrt(sigma_dh**2 + (sigma_s)**2))**2
current_sigma_smb = np.sqrt(term_rho + term_dh_s)

print(f"Cumulated MB year 1: {cum_mb_feb24} +/- {current_sigma_smb}")

cum_mb_feb25 =  df_smooth_aoi.loc['2025-02-28']-df_smooth_aoi.loc['2024-02-28']

term_rho = (((df_aoi_corrected.loc['2025-02-28']-df_aoi_corrected.loc['2024-03-04']) / density) * sigma_rho )**2
term_dh_s = (density * np.sqrt(sigma_dh**2 + (sigma_s)**2))**2
current_sigma_smb = np.sqrt(term_rho + term_dh_s)

print(f"Cumulated MB year 2: {cum_mb_feb25} +/- {current_sigma_smb}")


# EF
mb_c = 2.7
sig_mb_c = 2.4
mb_g = 0.8
sig_mb_g = 0.4

ef = mb_c/mb_g

sig_ef = np.sqrt((sig_mb_c/mb_g)**2+(mb_c/mb_g**2)**2*sig_mb_g**2)

print(f"{ef} +/- {sig_ef}")







# extract snowslide values within cone


# === CONFIGURATION ===
cones_path = AOI_SHAPEFILE
mean_tif = "Z:/glazio/projects/8045-VAW_CAIRN-GLOBAL/SMB_inversions/2024_Argentiere/Snowslide/SND_final/SND_anomaly_mweq_mean.tif"
std_tif = "Z:/glazio/projects/8045-VAW_CAIRN-GLOBAL/SMB_inversions/2024_Argentiere/Snowslide/SND_final/SND_anomaly_mweq_std.tif"

# === LOAD GEOMETRIES ===
cones = gpd.read_file(cones_path)

src = rasterio.open(std_tif) 

# Check if CRS matches, if not, reproject GDF
if cones.crs != src.crs:
    cones = cones.to_crs(src.crs)

out_image, out_transform = rio_mask(src, cones.geometry, crop=True, all_touched=False)
data = out_image[0].astype('float32')
data[(data<=0)] = np.nan

plt.figure(figsize=(10, 8))
plt.imshow(data, cmap='terrain')
plt.colorbar(label='Snow (m w.e.)')
plt.show()
        
# Flatten to 1D array and remove NaNs/NoData
data = data.flatten()
valid_data = data[~np.isnan(data)]
        
print(f"{np.mean(valid_data)}+/-{np.mean(valid_data)}")



