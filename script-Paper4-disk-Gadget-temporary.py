#######################################################################
#
#  UNIFIED ANALYSIS SCRIPT FOR DISK SIMULATION FOR THE AGORA PROJECT
#
#  FOR SCRIPT HISTORY SEE VERSION CONTROL CHANGELOG
#
#  Note: This script is designed to run in yt 3.0, 
#        the "bleeding edge" installation option on the yt website.  
#        Older versions of yt may yield incorrect results 
#        (especially with RAMSES data)
# 
#  Note: This is a temporary script for Gadget datasets.
#        We may not need a separate script for SPH codes 
#        as yt improves in its support for SPH.
#
#######################################################################
import sys
from yt.mods import *
import matplotlib.colorbar as cb
import yt.utilities.physical_constants as constants
import matplotlib.pyplot as plt
from mpl_toolkits.axes_grid1 import AxesGrid
from yt.fields.particle_fields import add_volume_weighted_smoothed_field
mylog.setLevel(1)

# If RAMSES data, use pf=load('/path/to/data', fields=["list of fields"]).  
# For other codes, the syntax to load may be different - see the yt docs.  

# For GADGET, the bounding_box must be set manually 
# in such a way that the boundary encloses all the particles in the snap. 
# In this example, the boundary is set to extend from -1000.0 to 1000.0 kpc.
for time in range(5):
        if time == 0:
            pf = GadgetStaticOutput('./Gadget3/snap_000',unit_base = {'length':("kpc", 1.0)}, 
                                    bounding_box=[[-1000.0, 1000.0], [-1000.0, 1000.0], [-1000.0,1000.0]],
				    n_ref=64, field_spec= "agora_unlv")
        if time == 1:
            pf = GadgetStaticOutput('./Gadget3/snap_001',unit_base = {'length':("kpc", 1.0)}, 
                                    bounding_box=[[-1000.0, 1000.0], [-1000.0, 1000.0], [-1000.0,1000.0]],
				    n_ref=64, field_spec= "agora_unlv")
        if time == 2:
            pf = GadgetStaticOutput('./Gadget3/snap_002',unit_base = {'length':("kpc", 1.0)}, 
                                    bounding_box=[[-1000.0, 1000.0], [-1000.0, 1000.0], [-1000.0,1000.0]],
				    n_ref=64, field_spec= "agora_unlv")
        if time == 3:
            pf = GadgetStaticOutput('./Gadget3/snap_003',unit_base = {'length':("kpc", 1.0)}, 
                                    bounding_box=[[-1000.0, 1000.0], [-1000.0, 1000.0], [-1000.0,1000.0]],
				    n_ref=64, field_spec= "agora_unlv")
        if time == 4:
            pf = GadgetStaticOutput('./Gadget3/snap_004',unit_base = {'length':("kpc", 1.0)}, 
                                    bounding_box=[[-1000.0, 1000.0], [-1000.0, 1000.0], [-1000.0,1000.0]],
				    n_ref=64, field_spec= "agora_unlv")

	pf.h
	fig = plt.figure()
	grid = AxesGrid(fig, (0.01,0.07,0.45,0.91),
			nrows_ncols = (3, 1),
			axes_pad = 0.02,
			add_all = True, 
			share_all = True,
			label_mode = "1",
			cbar_mode = "single",
			cbar_location = "right",
			cbar_size = "1.5%",
			cbar_pad = "0%")

	fn = add_volume_weighted_smoothed_field("Gas", "Coordinates",
						"particle_mass", "SmoothingLength", "density", "density",
						pf.field_info)
	pf.field_info.alias(("gas", "density"), fn[0])

        # Let's find the center to keep the galaxy at the center of all the images.
	v, center = pf.h.find_max(("gas", "density"))

        # The following makes a 1x3 column of a field along all 3 axes with a horizontal colorbar at the bottom
        #fig, axes, colorbars = get_multi_plot( 1, 3, colorbar='horizontal', bw = 4)
        for ax in range(3):
	    p = ProjectionPlot(pf, ax, ("gas", "density"), center = center, weight_field = None)
            p.set_zlim(("gas", "density"), 1e-6, 1e-1)

	    plot = p.plots[("gas", "density")]
	    plot.figure = fig
	    plot.axes = grid[ax].axes
	    plot.cax = grid.cbar_axes[ax]
	    p._setup_plots()

            p.set_width(30,'kpc')
	    
            if time == 0:
                if ax == 0:
                    fig.text(0.1, 0.95, "GADGET 0 Myr", {'color':'w'}) #change to your code name here
            if time == 1:
                if ax == 0:
                    fig.text(0.1, 0.95, "GADGET 250 Myr", {'color':'w'}) #change to your code name here
            if time == 2:
                if ax == 0:
                    fig.text(0.1, 0.95, "GADGET 500 Myr", {'color':'w'}) #change to your code name here
            if time == 3:
                if ax == 0:
                    fig.text(0.1, 0.95, "GADGET 750 Myr", {'color':'w'}) #change to your code name here
            if time == 4:
                if ax == 0:
                    fig.text(0.1, 0.95, "GADGET 1000 Myr", {'color':'w'}) #change to your code name here

        if time == 0:
            fig.savefig("Gadget_Todoroki_0Myr_Sigma", bbox_inches='tight', pad_inches=0.03)
        if time == 1:
            fig.savefig("Gadget_Todoroki_250Myr_Sigma", bbox_inches='tight', pad_inches=0.03)
        if time == 2:
            fig.savefig("Gadget_Todoroki_500Myr_Sigma", bbox_inches='tight', pad_inches=0.03)
        if time == 3:
            fig.savefig("Gadget_Todoroki_750Myr_Sigma", bbox_inches='tight', pad_inches=0.03)
        if time == 4:
            fig.savefig("Gadget_Todoroki_1000Myr_Sigma", bbox_inches='tight', pad_inches=0.03)



