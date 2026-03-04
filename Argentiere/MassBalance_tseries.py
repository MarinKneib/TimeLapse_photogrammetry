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
from datetime import datetime
import matplotlib.cm as cm
import matplotlib.colors as colors
from scipy.ndimage import binary_erosion
import scipy.ndimage as ndi
from scipy.interpolate import griddata
from shapely.geometry import LineString
from typing import Dict, List, Tuple

# --- 1. CONFIGURATION & SWITCHES ---
POINTS_OF_INTEREST = {
    "Top of cone": (1010713,  6544661), 
    "Center of cone": (1010839,  6544760),
    "Bottom of cone": (1011012,  6544896)
}
BOX_SIZE = 20  # meters 
reproj_res = 1
reproj_bounds = {"left": 1010500, "bottom": 6544500, "right": 1011226, "top": 6545200}
MAX_PIXEL_SIZE = 100   # Max gap size to interpolate in Ref DEM
SUBMERGENCE_TIF = "Z:/gl_kneibm/Projects/PI/2024_CAIRN-GLOBAL/TL_photogrammetry_Argentiere/results/UAV/submergence/Submergence_2023.tif" # m/yr
PRECIP_FILE = "Z:/gl_kneibm/Projects/PI/2024_CAIRN-GLOBAL/TL_photogrammetry_Argentiere/data/Meteo/Donnees_MeteoFrance/Donnees_journalieres_2023-2024/Donnees_precip_journalieres_Chamonix_aout23-mai24.txt"
TEMP_FILE = "Z:/gl_kneibm/Projects/PI/2024_CAIRN-GLOBAL/TL_photogrammetry_Argentiere/data/Meteo/Donnees_MeteoFrance/Donnees_journalieres_2023-2024/Chamonix_journalieres.xlsx"
dir_dems = pathlib.Path("Z:/gl_kneibm/Projects/PI/2024_CAIRN-GLOBAL/TL_photogrammetry_Argentiere/results/DEM_LB/PhotoTL/Coreg_avec_PhotoTL_27-09")

ALL_CONFIGS = [
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

# --- 2. FUNCTIONS ---
def get_mean_elevation(raster: gu.Raster, x: float, y: float, box_size: float):
    """Extracts mean elevation in a square box around a point."""
    # Define the bounding box for the crop
    half = box_size / 2
    extent = [x - half, x + half, y - half, y + half]
    try:
        # Crop raster to the 10x10 area
        subset = raster.crop(extent)
        # Calculate mean ignoring NaNs
        return np.nanmean(subset.data)
    except Exception:
        return np.nan

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
    labeled_array, num_labels = ndi.label(gap_mask) # <-- Use ndi.label
    
    # If no gaps are found, return an array of False
    if num_labels == 0:
        return np.zeros_like(gap_mask, dtype=bool)

    # 2. Calculate the size (sum of pixels) for each component
    component_sizes = ndi.sum(gap_mask, labeled_array, range(1, num_labels + 1)) # <-- Use ndi.sum (replaces the problematic 'sum')

    # 3. Identify labels that are too large
    large_labels_mask = component_sizes > max_size
    label_is_large = np.insert(large_labels_mask, 0, False)
    
    # 4. Map the large labels back to the original array structure
    large_gap_mask_output = label_is_large[labeled_array]

    return large_gap_mask_output

# --- 3. PROCESSING ---

# Load Submergence Velocity
v_sub_raster = gu.Raster(SUBMERGENCE_TIF)
v_sub_values = {name: get_mean_elevation(v_sub_raster, px, py, BOX_SIZE) 
                for name, (px, py) in POINTS_OF_INTEREST.items()}

# Extract Elevation Time Series
data_rows = []
for filename, date_str in ALL_CONFIGS:
    print(f'processing {filename}')
    dt = datetime.strptime(date_str, '%d/%m/%y')
    path = dir_dems / filename # Adjust path
    
    if path.exists():
        dem = gu.Raster(path).reproject(res=reproj_res, bounds=reproj_bounds, resampling="cubic")

        # Fill gaps 
        gap_mask = np.isnan(dem.data)
        gap_mask_eroded = binary_erosion(gap_mask, iterations=1)
        large_gaps = identify_large_gaps(gap_mask_eroded, MAX_PIXEL_SIZE)

        # Fill gaps but re-mask the truly large ones
        dem.data = interpolate_dem(dem.data)
        dem.data[large_gaps] = np.nan

        obs = {"date": dt}
        for name, (px, py) in POINTS_OF_INTEREST.items():
            obs[name] = get_mean_elevation(dem, px, py, BOX_SIZE)
        data_rows.append(obs)

df_elev = pd.DataFrame(data_rows).sort_values('date').set_index('date')

# --- 4. LOAD METEO DATA ---

# Precipitation (Tab separated/Fixed width)
df_precip = pd.read_csv(PRECIP_FILE, sep='\t', names=['date_str', 'precip'], dtype={'date_str': str})
df_precip['date'] = pd.to_datetime(df_precip['date_str'], format='%Y%m%d')
df_precip = df_precip.set_index('date')[['precip']]

# Temperature (Excel)
df_temp = pd.read_excel(TEMP_FILE)
df_temp['date'] = pd.to_datetime(df_temp['AAAAMMJJ'].astype(str), format='%Y%m%d')
df_temp = df_temp.set_index('date')[['TAMPLI']]

# Adjusting from Chamonix (1042m) to Bergschrund
df_temp['TAMPLI'] = df_temp['TAMPLI'] + (-0.0065 * (3150 - 1042))

# Aggregate to month-end ('ME')
df_precip_monthly = df_precip.resample('ME').sum()
df_temp_monthly = df_temp.resample('ME').mean()

# --- 5. CALCULATE SUBMERGENCE CORRECTION ---
# dh_corrected = z_obs - (v_sub * time_delta_years)
ref_date = df_elev.index[0]
df_corrected = df_elev.copy()

for name in POINTS_OF_INTEREST.keys():
    years_passed = (df_elev.index - ref_date).days / 365.25
    # Subtract the cumulative emergence/submergence 
    # (Note: if v_sub is negative for submergence, subtracting it adds elevation back)
    df_corrected[name] = df_elev[name] - (v_sub_values[name] * years_passed)

# Subtract the first valid elevation value from each column to show change (dh)
df_corrected = df_corrected - df_corrected.iloc[0]

# Reindex to daily to ensure the 60-day window is time-accurate
df_daily_interp = df_corrected.reindex(pd.date_range(df_corrected.index.min(), df_corrected.index.max(), freq='D')).interpolate(method='linear')
df_smooth = df_daily_interp.rolling(window=60, center=True, min_periods=1).mean()

# --- 6. PLOTTING ---
fig, axs = plt.subplots(len(POINTS_OF_INTEREST), 1, figsize=(14, 12), sharex=True)
if len(POINTS_OF_INTEREST) == 1: axs = [axs]

for ax, name in zip(axs, POINTS_OF_INTEREST.keys()):
    # Axis 1: Raw Elevation Points and 60-day Smooth Line
    ax.scatter(df_corrected.index, df_corrected[name], color='black', s=20, alpha=0.5, label='Raw dh')
    ax.plot(df_smooth.index, df_smooth[name], color='black', linewidth=2.5, label='60d Running Mean')
    ax.set_ylabel("Cumulative MB (m)", fontweight='bold')
    ax.set_ylim(-35, 35)
    
    # Axis 2: Monthly Precipitation (Width=20 to look like bars)
    ax_precip = ax.twinx()
    ax_precip.bar(df_precip_monthly.index, df_precip_monthly['precip'], width=20, color='royalblue', alpha=0.3, label='Monthly Precip')
    ax_precip.set_ylabel("Monthly Precip (mm)", color='royalblue')
    
    # Axis 3: Monthly Temperature
    ax_temp = ax.twinx()
    ax_temp.spines['right'].set_position(('outward', 60))
    ax_temp.plot(df_temp_monthly.index, df_temp_monthly['TAMPLI'], color='crimson', marker='s', linewidth=1.5, label='Monthly Temp')
    ax_temp.set_ylabel("Mean Monthly Temp (°C)", color='crimson')
    ax_temp.axhline(0, color='grey', linestyle='--', linewidth=0.8)
    
    ax.set_title(f"{name}", fontsize=14)

plt.tight_layout()
plt.show()