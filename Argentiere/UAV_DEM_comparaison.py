import numpy as np
import matplotlib.pyplot as plt
import py4dgeo
from matplotlib.colors import LinearSegmentedColormap
import xdem
from shapely.geometry import LineString, Point
import geoutils as gu
import pyproj
import rasterio
from scipy.interpolate import griddata
from scipy.spatial import cKDTree
from rasterio.transform import rowcol
import geopandas as gpd
import matplotlib.lines as mlines

######## Local functions
def add_scalebar(ax, length=100, location=(0.1, 0.05), linewidth=3, text_offset=0.015):
    # Get axis limits in map units
    x_min, x_max = ax.get_xlim()
    y_min, y_max = ax.get_ylim()

    # Convert fractional location to map coordinates
    x0 = x_min + location[0] * (x_max - x_min)
    y0 = y_min + location[1] * (y_max - y_min)

    # Draw scale bar
    ax.plot([x0, x0 + length], [y0, y0],
            color='black', linewidth=linewidth)

    # Label
    ax.text(x0 + length / 2, y0 + text_offset * (y_max - y_min),
            f"{length:.0f} m",
            ha='center', va='bottom', fontsize=14, color='black')

# Define extent from DEM affine (for georeferenced axes)
def get_extent(dem):
    xmin = dem.transform[2]
    xmax = dem.transform[2] + dem.transform[0] * dem.data.shape[1]
    ymax = dem.transform[5]
    ymin = dem.transform[5] + dem.transform[4] * dem.data.shape[0]
    return [xmin, xmax, ymin, ymax]

def sample_profile(dem, line: LineString, spacing=1.0):
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

    ## convert geographic coordinates to raster indices
    #x_i = ((x_s - dem.bounds.left) / dem.res[0]).astype(int)
    #y_i = ((dem.bounds.top - y_s) / dem.res[1]).astype(int)

    ## Initialize output array with NaNs
    #z_s = np.full_like(x_s, np.nan, dtype=float)

    ## Mask valid indices
    #valid_mask = (
    #    (x_i >= 0) & (x_i < dem.data.shape[0]) &
    #    (y_i >= 0) & (y_i < dem.data.shape[1])
    #)

    ## Fill valid points
    #z_s[valid_mask] = dem.data[x_i[valid_mask], y_i[valid_mask]]
    points = [x_s, y_s]
    z_s = dem.interp_points(points)

    return sample_dist, z_s

# ---- North arrow ----
def add_north_arrow(ax, x=0.95, y=0.1, size=0.05):
    ax.annotate('N',
                xy=(x, y), xytext=(x, y-size),
                xycoords='axes fraction',
                textcoords='axes fraction',
                arrowprops=dict(facecolor='black', width=3, headwidth=10),
                ha='center', va='center', fontsize=fontsize+2, fontweight='bold')

######## Define paths
results_dir = "Z:/gl_kneibm/Projects/PI/2024_CAIRN-GLOBAL/TL_photogrammetry_Argentiere/results/UAV/co-registered/"
gis_dir = "Z:/gl_kneibm/Projects/PI/2024_CAIRN-GLOBAL/TL_photogrammetry_Argentiere/data/GIS/"

######## load shapefiles
stable_terrain = gu.Vector(gis_dir+"Stable_terrain_fromUAV_2023_09_27.shp")
tran1 = gpd.read_file(gis_dir+"Profile1.shp")
tran2 = gpd.read_file(gis_dir+"Profile2.shp")
tran3 = gpd.read_file(gis_dir+"Profile3.shp")

######## Compute elevation change & plot
# Load DEMs from GeoTIFF
dem_ref = xdem.DEM(results_dir+"DEM_2023_09_27_ref_1m.tif")
dem_slave1 = xdem.DEM(results_dir+"DEM_2023_05_04_coreg_1m.tif")
dem_slave2 = xdem.DEM(results_dir+"DEM_2024_05_28_coreg_1m.tif")
dem_slave3 = xdem.DEM(results_dir+"DEM_2024_10_23_coreg_1m.tif")
dem_slave4 = xdem.DEM(results_dir+"DEM_2023_01_26_coreg_1m.tif")

# Compute elevation difference
dh_slave1_ref = dem_ref - dem_slave1
dh_ref_slave2 = dem_slave2 - dem_ref
dh_slave2_slave3 = dem_slave3 - dem_slave2
dh_slave4_slave1 = dem_slave1 - dem_slave4
dh_slave4_ref = dem_ref - dem_slave4

# ---- PLOT ----
fig, axes = plt.subplots(1, 3, figsize=(16, 6), constrained_layout=True)
vmin, vmax = -35, 35  # limits in meters
cmap = 'bwr_r'           # blue-white-red diverging colormap
fontsize = 16          # font size for titles, labels

# Define extent from DEM affine (for georeferenced axes)
extent = get_extent(dh_slave1_ref)

# Plot Slave1-ref difference
im1 = axes[0].imshow(dh_slave1_ref.data, cmap=cmap, vmin=vmin, vmax=vmax, extent=extent)
axes[0].set_title("04/05/2023 - 27/09/2023", fontsize=fontsize)
axes[0].grid(True, color='white', linestyle='--', linewidth=0.5)  # lat/lon-like grid
axes[0].tick_params(left=False, bottom=False, labelleft=False, labelbottom=False)
add_scalebar(axes[0], length=100)

# Plot ref-Slave2 difference
im2 = axes[1].imshow(dh_ref_slave2.data, cmap=cmap, vmin=vmin, vmax=vmax, extent=extent)
axes[1].set_title("27/09/2023 - 28/05/2024", fontsize=fontsize)
axes[1].grid(True, color='white', linestyle='--', linewidth=0.5)  # lat/lon-like grid
axes[1].tick_params(left=False, bottom=False, labelleft=False, labelbottom=False)

# Plot Slave2-Slave3 difference
im3 = axes[2].imshow(dh_slave2_slave3.data, cmap=cmap, vmin=vmin, vmax=vmax, extent=extent)
axes[2].set_title("28/05/2024 - 23/10/2024", fontsize=fontsize)
axes[2].grid(True, color='white', linestyle='--', linewidth=0.5)  # lat/lon-like grid
axes[2].tick_params(left=False, bottom=False, labelleft=False, labelbottom=False)

# Shared colorbar
cbar = fig.colorbar(im3, ax=axes, orientation='vertical', fraction=0.04, pad=0.02)
cbar.set_label("Elevation change (m)", fontsize=fontsize)
cbar.ax.tick_params(labelsize=fontsize)

add_north_arrow(axes[0])

# Add transects (black line, thicker)
tran1.plot(ax=axes[0], color="black", linewidth=2)
tran2.plot(ax=axes[0], color="black", linewidth=2)
tran3.plot(ax=axes[0], color="black", linewidth=2)

plt.show()



# plot terrestrial survey dh

fig, ax = plt.subplots(1, 1, figsize=(8, 6), constrained_layout=True)
vmin, vmax = -35, 35  # limits in meters
cmap = 'bwr_r'           # blue-white-red diverging colormap
fontsize = 16          # font size for titles, labels

# Plot Slave4-Slave1 difference
im1 = ax.imshow(dh_slave4_slave1.data, cmap=cmap, vmin=vmin, vmax=vmax, extent=extent)
ax.set_title("26/01/2023 - 04/05/2023", fontsize=fontsize)
ax.grid(True, color='white', linestyle='--', linewidth=0.5)  # lat/lon-like grid
ax.tick_params(left=False, bottom=False, labelleft=False, labelbottom=False)
add_scalebar(ax, length=100)

# colorbar
cbar = fig.colorbar(im1, ax=ax, orientation='vertical', fraction=0.04, pad=0.02)
cbar.set_label("Elevation change (m)", fontsize=fontsize)
cbar.ax.tick_params(labelsize=fontsize)

add_north_arrow(ax)

# Add transects (black line, thicker)
# tran1.plot(ax=axes[0], color="black", linewidth=2)
# tran2.plot(ax=axes[0], color="black", linewidth=2)
# tran3.plot(ax=axes[0], color="black", linewidth=2)

plt.show()

fig, ax = plt.subplots(1, 1, figsize=(8, 6), constrained_layout=True)
vmin, vmax = -35, 35  # limits in meters
cmap = 'bwr_r'           # blue-white-red diverging colormap
fontsize = 16          # font size for titles, labels

# Plot Slave4-Slave1 difference
im1 = ax.imshow(dh_slave4_ref.data, cmap=cmap, vmin=vmin, vmax=vmax, extent=extent)
ax.set_title("26/01/2023 - 27/09/2023", fontsize=fontsize)
ax.grid(True, color='white', linestyle='--', linewidth=0.5)  # lat/lon-like grid
ax.tick_params(left=False, bottom=False, labelleft=False, labelbottom=False)
add_scalebar(ax, length=100)
cbar = fig.colorbar(im1, ax=ax, orientation='vertical', fraction=0.04, pad=0.02)
cbar.set_label("Elevation change (m)", fontsize=fontsize)
cbar.ax.tick_params(labelsize=fontsize)
add_north_arrow(ax)

plt.show()

# # Save difference as GeoTIFF
# dh_slave1_ref.save(results_dir+"dh_2023_05_04-2023_09_27.tif")
# dh_ref_slave2.save(results_dir+"dh_2023_09_27-2024_05_28.tif")
# dh_slave2_slave3.save(results_dir+"dh_2024_05_28-2024_10_23.tif")



####### Plot DEMs along transects

line1 = tran1.geometry.iloc[0]
line2 = tran2.geometry.iloc[0]
line3 = tran3.geometry.iloc[0]

profiles = {
    "Profile 1": [sample_profile(dem_slave1, line1),
                  sample_profile(dem_ref, line1),
                  sample_profile(dem_slave2, line1),
                  sample_profile(dem_slave3, line1)],
    "Profile 2": [sample_profile(dem_slave1, line2),
                  sample_profile(dem_ref, line2),
                  sample_profile(dem_slave2, line2),
                  sample_profile(dem_slave3, line2)],
    "Profile 3": [sample_profile(dem_slave1, line3),
                  sample_profile(dem_ref, line3),
                  sample_profile(dem_slave2, line3),
                  sample_profile(dem_slave3, line3)]
}

fig, axs = plt.subplots(1, 3, figsize=(12, 15), constrained_layout=True)

dem_labels = ["04/05/2023",
              "27/09/2023",
              "28/05/2024",
              "23/10/2024"]

colors = ["blue", "red", "cyan", "orange"]

for ax, (title, profiles_list) in zip(axs, profiles.items()):
    for (dist, z), label, col in zip(profiles_list, dem_labels, colors):
        ax.plot(dist, z, label=label, color=col, linewidth=2)

    # Titles and styling
    ax.set_title(title, fontsize=16)
    ax.set_xlabel("Distance along transect (m)", fontsize=14)
    ax.set_ylabel("Elevation (m)", fontsize=14)
    ax.set_ylim(2800, 3300)
    ax.set_xlim(-10, 640)
    ax.set_aspect('equal')
    ax.grid(True, linestyle="--", linewidth=0.5)

axs[0].legend(loc='lower center', bbox_to_anchor=(0.5, 1.2), borderaxespad=0.)

plt.show()

####### Plot DH along transects

profiles = {
    "Profile 1": [sample_profile(dh_slave1_ref, line1),
                  sample_profile(dh_ref_slave2, line1),
                  sample_profile(dh_slave2_slave3, line1)],
    "Profile 2": [sample_profile(dh_slave1_ref, line2),
                  sample_profile(dh_ref_slave2, line2),
                  sample_profile(dh_slave2_slave3, line2)],
    "Profile 3": [sample_profile(dh_slave1_ref, line3),
                  sample_profile(dh_ref_slave2, line3),
                  sample_profile(dh_slave2_slave3, line3)]
}

fig, axs = plt.subplots(1, 3, figsize=(12, 3), constrained_layout=True)

dem_labels = ["04/05/2023 - 27/09/2023 (SUMMER 1)",
              "27/09/2023 - 28/05/2024 (WINTER 1)",
              "28/05/2024 - 23/10/2024 (SUMMER 2)"]

colors = ["red", "cyan", "orange"]

for ax, (title, profiles_list) in zip(axs, profiles.items()):
    for (dist, z), label, col in zip(profiles_list, dem_labels, colors):
        ax.plot(dist, z, label=label, color=col, linewidth=2)

    # Titles and styling
    ax.set_title(title, fontsize=16)
    ax.set_xlabel("Distance along transect (m)", fontsize=14)
    ax.set_ylabel("Elevation change (m)", fontsize=14)
    ax.set_ylim(-40, 40)
    ax.set_xlim(-10, 640)
    #ax.set_aspect('equal')
    ax.grid(True, linestyle="--", linewidth=0.5)

axs[0].legend(loc='lower center', bbox_to_anchor=(0.5, 1.2), borderaxespad=0.)

plt.show()

######### UNCERTAINTIES in DH

##### histograms 
# Extract valid (non-NaN) pixels
dh1 = dh_slave1_ref.data[~np.isnan(dh_slave1_ref.data)]
dh2 = dh_ref_slave2.data[~np.isnan(dh_ref_slave2.data)]
dh3 = dh_slave2_slave3.data[~np.isnan(dh_slave2_slave3.data)]
dh4 = dh_slave4_ref.data[~np.isnan(dh_slave4_ref.data)]

# Common histogram range
vmin, vmax = -35, 35
bins = np.linspace(vmin, vmax, 141)   # 0.5 m bins

plt.figure(figsize=(10,6))

plt.hist(dh1, bins=bins, alpha=0.5, label="04/05/2023 - 27/09/2023 (SUMMER 1)")
plt.hist(dh2, bins=bins, alpha=0.5, label="27/09/2023 - 28/05/2024 (WINTER 1)")
plt.hist(dh3, bins=bins, alpha=0.5, label="28/05/2024 - 23/10/2024 (SUMMER 2)")
plt.hist(dh4, bins=bins, alpha=0.5, label="28/05/2024 - 23/10/2024 (Spring 1)")

plt.xlabel("Elevation change (m)", fontsize=14)
plt.ylabel("Pixel count", fontsize=14)
plt.legend(fontsize=12)
plt.grid(alpha=0.3)
plt.tight_layout()

plt.show()


##### based on stable terrain
slope = xdem.terrain.slope(dem_ref)   
slope_slave1 = xdem.terrain.slope(dem_slave1)
slope_slave2 = xdem.terrain.slope(dem_slave2)
slope_slave3 = xdem.terrain.slope(dem_slave3)

ortho_ref = gu.Raster(results_dir+"ORTHO_2023_09_27_ref_1m.tif")
ortho_slave1 = gu.Raster(results_dir+"ORTHO_2023_05_04_coreg_1m.tif")
ortho_slave2 = gu.Raster(results_dir+"ORTHO_2024_05_28_coreg_1m.tif")
ortho_slave3 = gu.Raster(results_dir+"ORTHO_2024_10_23_coreg_1m.tif")
ortho_slave4 = gu.Raster(results_dir+"ORTHO_2023_01_26_coreg_1m.tif")

img_ref = ortho_ref.data
img_slave1 = ortho_slave1.data
img_slave2 = ortho_slave2.data
img_slave3 = ortho_slave3.data
img_slave4 = ortho_slave4.data

grayscale_ref = img_ref[:3].mean(axis=0) 
grayscale_slave1 = img_slave1[:3].mean(axis=0) 
grayscale_slave2 = img_slave2[:3].mean(axis=0) 
grayscale_slave3 = img_slave3[:3].mean(axis=0) 
grayscale_slave4 = img_slave4[:3].mean(axis=0) 

ndwi_ref = (img_ref[2] - img_ref[0]) / (img_ref[2] + img_ref[0] + 1e-8)
ndwi_slave1 = (img_slave1[2] - img_slave1[0]) / (img_slave1[2] + img_slave1[0] + 1e-8)
ndwi_slave2 = (img_slave2[2] - img_slave2[0]) / (img_slave3[2] + img_slave2[0] + 1e-8)
ndwi_slave3 = (img_slave3[2] - img_slave3[0]) / (img_slave3[2] + img_slave3[0] + 1e-8)
ndwi_slave4 = (img_slave4[2] - img_slave4[0]) / (img_slave4[2] + img_slave4[0] + 1e-8)

a1 = -150 / 0.25
b1 = 150
a2 = -150/0.75
b2 = 120

mask_ref = grayscale_ref - (ndwi_ref * a1 + b1) < 0 
mask_slave1 = grayscale_slave1 - (ndwi_slave1 * a1 + b1) < 0
mask_slave2 = grayscale_slave2 - (ndwi_slave2 * a1 + b1) < 0
mask_slave3 = grayscale_slave3 - (ndwi_slave3 * a1 + b1) < 0
mask_slave4 = grayscale_slave4 - (ndwi_slave4 * a2 + b2) < 0

stable_mask = stable_terrain.create_mask(dh_slave1_ref)

dh1 = dh_slave1_ref.copy()
dh2 = dh_ref_slave2.copy()
dh3 = dh_slave2_slave3.copy()
dh4 = dh_slave4_ref.copy()

dh1[(stable_mask == 0) | (slope.data > 60) | (mask_slave1 == 0) | (mask_ref == 0)] = np.nan
dh2[(stable_mask == 0) | (slope.data > 60) | (mask_slave2 == 0) | (mask_ref == 0)] = np.nan
dh3[(stable_mask == 0) | (slope.data > 60) | (mask_slave2 == 0) | (mask_slave3 == 0)] = np.nan
dh4[(stable_mask == 0) | (slope.data > 60) | (mask_slave4 == 0) | (mask_ref == 0)] = np.nan

dh1 = dh1.data[~np.isnan(dh1.data)]
dh2 = dh2.data[~np.isnan(dh2.data)]
dh3 = dh3.data[~np.isnan(dh3.data)]
dh4 = dh4.data[~np.isnan(dh4.data)]

# Common histogram range
vmin, vmax = -3, 3
bins = np.linspace(vmin, vmax, 141)   # 0.5 m bins

plt.figure(figsize=(10,6))

plt.hist(dh1, bins=bins, alpha=0.5, label="04/05/2023 - 27/09/2023 (SUMMER 1)")
plt.hist(dh2, bins=bins, alpha=0.5, label="27/09/2023 - 28/05/2024 (WINTER 1)")
plt.hist(dh3, bins=bins, alpha=0.5, label="28/05/2024 - 23/10/2024 (SUMMER 2)")
#plt.hist(dh4, bins=bins, alpha=0.5, label="26/01/2023 - 27/09/2023 (SPRING)")

plt.xlabel("Elevation change (m)", fontsize=14)
plt.ylabel("Pixel count", fontsize=14)
plt.legend(fontsize=12)
plt.grid(alpha=0.3)
plt.tight_layout()

plt.show()

def get_outlier_percentage(data, vmin, vmax):
    # Find points below vmin OR above vmax
    outliers = np.sum((data < vmin) | (data > vmax))
    total = len(data)
    return (outliers / total) * 100

# Calculate for your datasets
p1 = get_outlier_percentage(dh1, vmin, vmax)
p2 = get_outlier_percentage(dh2, vmin, vmax)
p3 = get_outlier_percentage(dh3, vmin, vmax)

print(f"Summer 1 Outliers: {p1:.2f}%")
print(f"Winter 1 Outliers: {p2:.2f}%")
print(f"Summer 2 Outliers: {p3:.2f}%")

median_all = np.nanmedian(np.concatenate([dh1, dh2, dh3]))
std_all = np.nanstd(np.concatenate([dh1, dh2, dh3]))
print(f"Median STABLE TERRAIN dh SUMMER 1: {np.nanmedian(dh1):.3f} m")
print(f"Std. dev. STABLE TERRAIN dh SUMMER 1: {np.nanstd(dh1):.3f} m")
print(f"Median STABLE TERRAIN dh WINTER 1: {np.nanmedian(dh2):.3f} m")
print(f"Std. dev. STABLE TERRAIN dh WINTER 1: {np.nanstd(dh2):.3f} m")
print(f"Median STABLE TERRAIN dh SUMMER 2: {np.nanmedian(dh3):.3f} m")
print(f"Std. dev. STABLE TERRAIN dh SUMMER 2: {np.nanstd(dh3):.3f} m")
print(f"Median STABLE TERRAIN all: {np.nanmedian(np.concatenate([dh1, dh2, dh3])):.3f} m")
print(f"Std. dev. STABLE TERRAIN all: {np.nanstd(np.concatenate([dh1, dh2, dh3])):.3f} m")

############# SLOPE
# extract slope
slope_ref = xdem.terrain.slope(dem_ref)   
slope_slave1 = xdem.terrain.slope(dem_slave1)
slope_slave2 = xdem.terrain.slope(dem_slave2)
slope_slave3 = xdem.terrain.slope(dem_slave3)

slope_ref.save(results_dir+"slope_2023_09_27.tif")
slope_slave1.save(results_dir+"slope_2023_05_04.tif")
slope_slave2.save(results_dir+"slope_2024_05_28.tif")
slope_slave3.save(results_dir+"slope_2024_10_23.tif")

slope_filt = slope_ref.data[~np.isnan(slope_ref.data)]

vmin, vmax = 0, 90
bins = np.linspace(vmin, vmax, 91)   # 1° bins

plt.figure(figsize=(10,6))

plt.hist(slope_filt, bins=bins, alpha=0.5, label="Slope")

plt.xlabel("Slope (°)", fontsize=14)
plt.ylabel("Pixel count", fontsize=14)
plt.legend(fontsize=12)
plt.grid(alpha=0.3)
plt.tight_layout()

plt.show()


vmin, vmax = 0, 90  # limits in °
cmap = 'inferno'           # blue-white-red diverging colormap
fontsize = 16          # font size for titles, labels

# Define extent from DEM affine (for georeferenced axes)
extent = get_extent(slope_ref)

fig, axs = plt.subplots(1,2, figsize=(10, 8), constrained_layout=True)

im1 = axs[0].imshow(slope_slave1.data,cmap=cmap,vmin=vmin,vmax=vmax,extent=extent)
axs[0].grid(True, color='white', linestyle='--', linewidth=0.5)  # lat/lon-like grid
axs[0].tick_params(left=False, bottom=False, labelleft=False, labelbottom=False)
axs[0].set_title("Slope Map 04/05/2023", fontsize=fontsize+2)
add_scalebar(ax=axs[0], length=100)

im2 = axs[1].imshow(slope_ref.data,cmap=cmap,vmin=vmin,vmax=vmax,extent=extent)
axs[1].grid(True, color='white', linestyle='--', linewidth=0.5)  # lat/lon-like grid
axs[1].tick_params(left=False, bottom=False, labelleft=False, labelbottom=False)
axs[1].set_title("Slope Map 27/09/2023", fontsize=fontsize+2)

# Shared colorbar
cbar = fig.colorbar(im2, ax=axs, orientation="vertical", fraction=0.04, pad=0.02)
cbar.set_label("Slope (°)", fontsize=fontsize)
cbar.ax.tick_params(labelsize=fontsize)

add_north_arrow(axs[0])

# Add transects (black line, thicker)
tran1.plot(ax=axs[0], color="black", linewidth=2)
tran2.plot(ax=axs[0], color="black", linewidth=2)
tran3.plot(ax=axs[0], color="black", linewidth=2)

plt.show()









# --- 1. Load the cone shapefile ---
gis_dir = "Z:/gl_kneibm/Projects/PI/2024_CAIRN-GLOBAL/TL_photogrammetry_Argentiere/data/GIS/"
cone_small = gpd.read_file(gis_dir + 'from_Louise/Entire_cone.shp')

# --- 2. Prep Slope Profiles ---
# (Assuming slope rasters are already computed as slope_slave1, slope_ref, etc.)
slope_profiles = {
    "Profile 1": [sample_profile(slope_slave1, line1),
                  sample_profile(slope_ref, line1),
                  sample_profile(slope_slave2, line1),
                  sample_profile(slope_slave3, line1)],
    "Profile 2": [sample_profile(slope_slave1, line2),
                  sample_profile(slope_ref, line2),
                  sample_profile(slope_slave2, line2),
                  sample_profile(slope_slave3, line2)],
    "Profile 3": [sample_profile(slope_slave1, line3),
                  sample_profile(slope_ref, line3),
                  sample_profile(slope_slave2, line3),
                  sample_profile(slope_slave3, line3)]
}

# --- 3. Find Intersection Distances ---
# We calculate where the transect enters/leaves the cone to plot vertical lines
cone_geom = cone_small.geometry.unary_union
intersection_dist = []
for line in [line1, line2, line3]:
    # Intersection returns a multiline or line within the cone
    intersect = line.intersection(cone_geom)
    if not intersect.is_empty:
        # Get start and end distance along the original line for the intersection
        # This is a simplification; works best if the line crosses once
        d1 = line.project(Point(intersect.coords[0])) if hasattr(intersect, 'coords') else 0
        d2 = line.project(Point(intersect.coords[-1])) if hasattr(intersect, 'coords') else 0
        intersection_dist.append([d1, d2])
    else:
        intersection_dist.append([])

# --- 1. Smoothing Function ---
def smooth_slope_filtered(z, window_m, spacing=1.0, max_slope=60):
    # Create a copy and mask values steeper than 60 degrees
    z_filtered = np.array(z, copy=True)
    z_filtered[z_filtered > max_slope] = np.nan
    
    # Calculate window size in pixels
    window_size = int(window_m / spacing)
    if window_size < 3:
        return z_filtered

    # Apply a moving average that ignores NaNs
    smoothed = np.full_like(z_filtered, np.nan)
    half_win = window_size // 2
    
    for i in range(len(z_filtered)):
        # Define window boundaries
        start = max(0, i - half_win)
        end = min(len(z_filtered), i + half_win + 1)
        # Calculate mean of valid pixels in window
        window_vals = z_filtered[start:end]
        if np.any(~np.isnan(window_vals)):
            smoothed[i] = np.nanmean(window_vals)
            
    return smoothed

# --- 2. Setup Figure & Layout ---
# Use a smaller width to height ratio or adjust wspace to remove the gap
fig, axs = plt.subplots(3, 3, figsize=(18, 16), 
                       gridspec_kw={'height_ratios': [2, 1, 1]})
fig.set_dpi(600)
plt.subplots_adjust(wspace=0.18, hspace=0.3) # Manually tightening horizontal space

fontsize_label = 14
fontsize_tick = 12
fontsize_title = 16

# --- ROW 1: Map Views (dh) ---
d_maps = [dh_slave1_ref, dh_ref_slave2, dh_slave2_slave3]
titles_row1 = ["04/05/2023 - 27/09/2023", "27/09/2023 - 28/05/2024", "28/05/2024 - 23/10/2024"]

for i in range(3):
    ax = axs[0, i]
    im = ax.imshow(d_maps[i].data, cmap='bwr_r', vmin=-35, vmax=35, extent=extent)
    ax.set_title(titles_row1[i], fontsize=fontsize_title, fontweight='bold')
    ax.tick_params(left=False, bottom=False, labelleft=False, labelbottom=False)
    if i == 0:
        cone_small.boundary.plot(ax=ax, color='black', linestyle='--', linewidth=1.5)
        add_north_arrow(ax, x=0.08, y=0.92, size=0.05)
        add_scalebar(ax, length=100, location=(0.15, 0.05))
        for t in [tran1, tran2, tran3]:
            t.plot(ax=ax, color="black", linewidth=1.5)

# Colorbar for Top Row
cbar_ax = fig.add_axes([0.92, 0.7, 0.015, 0.2]) # [left, bottom, width, height]
cbar = fig.colorbar(im, cax=cbar_ax)
cbar.set_label("Elevation change (m)", fontsize=fontsize_label)
cbar.ax.tick_params(labelsize=fontsize_tick)

# --- ROW 2: DH Transects ---
colors_dh = ["red", "cyan", "orange"]
labels_dh = ["Summer 1 (04/05/2023 - 27/09/2023)", "Winter 1 (27/09/2023 - 28/05/2024)", "Summer 2 (28/05/2024 - 23/10/2024)"]

for i, (title, prof_list) in enumerate(profiles.items()):
    ax = axs[1, i]
    if i > 0: ax.sharey(axs[1, 0])

    for (dist, z), label, col in zip(prof_list, labels_dh, colors_dh):
        ax.plot(dist, z, label=label, color=col, linewidth=2)
    
    for d in intersection_dist[i]:
        ax.axvline(d, color='black', linestyle='--', alpha=0.7)
    
    ax.set_title(title, fontsize=fontsize_title, fontweight='bold') # Matching top row style
    ax.set_ylabel("Elevation change (m)", fontsize=fontsize_label)
    ax.set_ylim(-40, 40)
    ax.set_xlim(-10, 640)
    ax.tick_params(axis='both', labelsize=fontsize_tick)
    ax.grid(True, alpha=0.3)

# Legend Row 2
axs[1, 0].legend(loc='lower center', bbox_to_anchor=(1.5, -0.3), ncol=3, fontsize=fontsize_label)

# --- ROW 3: Slope Transects (Smoothed) ---
# Warm for Autumn (Sept, Oct), Cold for Spring (Jan, May)
colors_slope = ["#1f77b4", "#aec7e8", "#ff7f0e", "#d62728"] # Cold (Blue/LightBlue), Warm (Orange/Red)
slope_labels = ["04/05/2023 (Spring)", "28/05/2024 (Spring)", "27/09/2023 (Autumn)", "23/10/2024 (Autumn)"]
# Reordering to match color logic: Slave1, Slave2 (Spring) then Ref, Slave3 (Autumn)
slope_order = [0, 2, 1, 3] 

for i, (title, prof_list) in enumerate(slope_profiles.items()):
    ax = axs[2, i]
    if i > 0: ax.sharey(axs[2, 0])
    # Re-map profiles to match the cold/warm order
    for idx, color_idx in enumerate(slope_order):
        dist, z = prof_list[color_idx]
        z_smooth = smooth_slope_filtered(z, window_m=20, spacing=1.0, max_slope=60)
        ax.plot(dist, z_smooth, label=slope_labels[idx], color=colors_slope[idx], linewidth=1.5)
        
    for d in intersection_dist[i]:
        ax.axvline(d, color='black', linestyle='--', alpha=0.7)
        
    ax.set_title("") # No title as requested
    ax.set_ylabel("Slope (°)", fontsize=fontsize_label)
    ax.set_xlabel("Distance along transect (m)", fontsize=fontsize_label)
    ax.set_ylim(0, 70)
    ax.set_xlim(-10, 640)
    ax.tick_params(axis='both', labelsize=fontsize_tick)
    ax.grid(True, alpha=0.3)

# Legend Row 3
axs[2, 0].legend(loc='upper center', bbox_to_anchor=(1.5, -0.2), ncol=4, fontsize=fontsize_label)

plt.show()
