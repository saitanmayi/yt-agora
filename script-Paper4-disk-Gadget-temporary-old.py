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

# If RAMSES data, use pf=load('/path/to/data', fields=["list of fields"]).  
# For other codes, the syntax to load may be different - see the yt docs.  

# For GADGET, the bounding_box must be set manually 
# in such a way that the boundary encloses all the particles in the snap. 
# In this example, the boundary is set to extend from -1000.0 to 1000.0 kpc.
for time in range(5):
        if time == 0:
            pf = GadgetStaticOutput('/path/to/ics',unit_base = {"kpc": 1.0}, 
                                    bounding_box=[[-1000.0, 1000.0], [-1000.0, 1000.0], [-1000.0,1000.0]])
        if time == 1:
            pf = GadgetStaticOutput('/path/to/snap',unit_base = {"kpc": 1.0}, 
                                    bounding_box=[[-1000.0, 1000.0], [-1000.0, 1000.0], [-1000.0,1000.0]])       
        if time == 2:
            pf = GadgetStaticOutput('/path/to/snap',unit_base = {"kpc": 1.0}, 
                                    bounding_box=[[-1000.0, 1000.0], [-1000.0, 1000.0], [-1000.0,1000.0]])        
        if time == 3:
            pf= GadgetStaticOutput('/path/to/snap',unit_base = {"kpc": 1.0}, 
                                  bounding_box=[[-1000.0, 1000.0], [-1000.0, 1000.0], [-1000.0,1000.0]])
        if time == 4:
            pf = GadgetStaticOutput('/path/to/snap',unit_base = {"kpc": 1.0}, 
                                    bounding_box=[[-1000.0, 1000.0], [-1000.0, 1000.0], [-1000.0,1000.0]])

        pc=PlotCollection(pf,'c')

        # Template - add all your fields like this if they aren't already defined by your code.  The following example just changes the "Density" field to "Sigma" for projections
        def _Sigm(field,data): return(data["deposit", "Gas_density"]*1.0)
        GadgetFieldInfo.add_field("Sigma",function=_Sigm, units=r"\rm {g cm}^{-3}", projected_units=r"\rm{g\ cm}^{-2}", display_name=r"\Sigma_{gas}")

        # Let's calculate the center of mass to keep the galaxy at the center of all the images.
        my_sphere = pf.h.sphere([0.5, 0.5, 0.5], 20.0/pf["kpc"])
        my_sphere["deposit", "Gas_density"]
        center = my_sphere.quantities["CenterOfMass"](use_cells=False, use_particles=True)

        # The following makes a 1x3 column of a field along all 3 axes with a horizontal colorbar at the bottom
        fig, axes, colorbars = get_multi_plot( 1, 3, colorbar='horizontal', bw = 4)
        for ax in range(3):
            p=pc.add_projection("Sigma",ax,center=center,figure=fig,axes=axes[ax][0],use_colorbar=False)
            p.set_zlim(1e-6,1e-1)  #set your limits here
            
            if time == 0:
                if ax == 0:
                    p.modify["text"]((0.1,0.9),"GADGET 0 Myr",text_args={'color':'k'}) #change to your code name here
            if time == 1:
                if ax == 0:
                    p.modify["text"]((0.1,0.9),"GADGET 250 Myr",text_args={'color':'k'})
            if time == 2:
                if ax == 0:
                    p.modify["text"]((0.1,0.9),"GADGET 500 Myr",text_args={'color':'k'})
            if time == 3:
                if ax == 0:
                    p.modify["text"]((0.1,0.9),"GADGET 750 Myr",text_args={'color':'k'})
            if time == 4:
                if ax == 0:
                    p.modify["text"]((0.1,0.9),"GADGET 1000 Myr",text_args={'color':'k'})

            p.set_width(30,'kpc')
    
        # Add colorbar
        for p, cax in zip(pc.plots, colorbars):
            cbar=cb.Colorbar(cax,p.image,orientation='horizontal')
            p.colorbar=cbar
            p._autoset_label()

        if time == 0:
                fig.savefig("Gadget_Todoroki_0Myr_Sigma")
        if time == 1:
                fig.savefig("Gadget_Todoroki_250Myr_Sigma")
        if time == 2:
                fig.savefig("Gadget_Todoroki_500Myr_Sigma")
        if time == 3:
                fig.savefig("Gadget_Todoroki_750Myr_Sigma")
        if time == 4:
                fig.savefig("Gadget_Todoroki_1000Myr_Sigma")



