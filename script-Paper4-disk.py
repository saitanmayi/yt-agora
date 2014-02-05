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
#######################################################################
import sys
from yt.mods import *
import matplotlib.colorbar as cb
import yt.utilities.physical_constants as constants

# If RAMSES data, use pf=load('/path/to/data', fields=["list of fields"]).  
# For other codes, the syntax to load may be different - see the yt docs.  
for time in range(5):
        if time == 0:
            pf=load('') #  0 Myr                
        if time == 1:
            pf=load('') #250 Myr
        if time == 2:
            pf=load('') #500 Myr
        if time == 3:
            pf=load('') #750 Myr
        if time == 4:
            pf=load('') #1000 Myr
        
        pc=PlotCollection(pf,'c')

        # Template - add all your fields like this if they aren't already defined by your code.  The following example just changes the "Density" field to "Sigma" for projections
        def _Sigm(field,data): return(data["Density"]*1.0)
        add_field("Sigma",function=_Sigm, units=r"\rm {g cm}^{-3}", projected_units=r"\rm{g\ cm}^{-2}", display_name=r"\Sigma_{gas}")

        # The following makes a 1x3 column of a field along all 3 axes with a horizontal colorbar at the bottom
        fig, axes, colorbars = get_multi_plot( 1, 3, colorbar='horizontal', bw = 4)
        for ax in range(3):
            p=pc.add_projection("Sigma",ax, figure=fig,axes=axes[ax][0],use_colorbar=False)
            p.set_zlim(1e-6,1e-1)  #set your limits here
            
            if time == 0:
                if ax == 0:
                    p.modify["text"]((0.1,0.9),"Enzo 0 Myr",text_args={'color':'w'}) #change to your code name here
            if time == 1:
                if ax == 0:
                    p.modify["text"]((0.1,0.9),"Enzo 250 Myr",text_args={'color':'w'})
            if time == 2:
                if ax == 0:
                    p.modify["text"]((0.1,0.9),"Enzo 500 Myr",text_args={'color':'w'})
            if time == 3:
                if ax == 0:
                    p.modify["text"]((0.1,0.9),"Enzo 750 Myr",text_args={'color':'w'})
            if time == 4:
                if ax == 0:
                    p.modify["text"]((0.1,0.9),"Enzo 1000 Myr",text_args={'color':'w'})

            pc.set_width(30,'kpc')

        # Add colorbar
        for p, cax in zip(pc.plots, colorbars):
            cbar=cb.Colorbar(cax,p.image,orientation='horizontal')
            p.colorbar=cbar
            p._autoset_label()

        if time == 0:
            fig.savefig("Enzo_0Myr_Sigma")
        if time == 1:
            fig.savefig("Enzo_250Myr_Sigma")
        if time == 2:
            fig.savefig("Enzo_500Myr_Sigma")
        if time == 3:
            fig.savefig("Enzo_750Myr_Sigma")
        if time == 4:
            fig.savefig("Enzo_1000Myr_Sigma")

        # Plot projected cell size weighted by inverse square of cell V (c/o Sam Leitner)    
        def _CellSizepc(field,data): return (data['CellVolume'])**(1/3.)/constants.cm_per_pc
        add_field("cell_size",function=_CellSizepc, units=r"pc", display_name=r"\Delta x", take_log=True )
        #def _Level(field,data): return -np.log2(data['CellVolumeCode'])/3.
        #add_field("cell_level",function=_Level, units=r"", display_name="level", take_log=False)
        def _Inv2CellVolumeCode(field,data): return data['CellVolumeCode']**-2
        add_field("volume_inv2",function=_Inv2CellVolumeCode)
        pc=PlotCollection(pf,'c')

        # The following makes a 1x3 column of a field along all 3 axes with a horizontal colorbar at the bottom
        figa, axesa, colorbarsa = get_multi_plot( 1, 3, colorbar='horizontal', bw = 4)
        for ax in range(3):
            p=pc.add_projection("cell_size",ax, figure=figa,axes=axesa[ax][0],use_colorbar=False,weight_field="volume_inv2")
            p.set_cmap("RdBu_r") # gist_stern
            p.set_zlim(50,500)  #set your limits here
            if time == 0:
                if ax == 0:
                    p.modify["text"]((0.1,0.9),"Enzo 0 Myr",text_args={'color':'w'}) #change to your code name here
            if time == 1:
                if ax == 0:
                    p.modify["text"]((0.1,0.9),"Enzo 250 Myr",text_args={'color':'w'})
            if time == 2:
                if ax == 0:
                    p.modify["text"]((0.1,0.9),"Enzo 500 Myr",text_args={'color':'w'})
            if time == 3:
                if ax == 0:
                    p.modify["text"]((0.1,0.9),"Enzo 750 Myr",text_args={'color':'w'})
            if time == 4:
                if ax == 0:
                    p.modify["text"]((0.1,0.9),"Enzo 1000 Myr",text_args={'color':'w'})

                pc.set_width(30,'kpc')

        for p, cax in zip(pc.plots, colorbarsa):
            cbar=cb.Colorbar(cax,p.image,ticks=[50,100,200,400],orientation='horizontal')
            cbar.ax.set_xticklabels(['50','100','200','400'])
            p.colorbar=cbar
            p._autoset_label()

            if time == 0:
                figa.savefig("Enzo_cellsize_0Myr")
            if time == 1:
                figa.savefig("Enzo_cellsize_250Myr")
            if time == 2:
                figa.savefig("Enzo_cellsize_500Myr")
            if time == 3:
                figa.savefig("Enzo_cellsize_750Myr")
            if time == 4:
                figa.savefig("Enzo_cellsize_1000Myr")

        # Create cumulative and mass fraction histograms of Cell Mass for final timestep
        if time ==4:
            dd=pf.h.sphere([0.5,0.5,0.5],(40.0,'kpc'))
            def _MassFraction(field,data): return(data["CellMassMsun"]/dd.quantities["TotalQuantity"]("CellMassMsun"))
            add_field("Mfrac",function=_MassFraction, display_name=r"MassFraction")
            pf.h
            pf.h._derived_fields_add(["Mfrac"])  #can probably comment this line out if not using RAMSES
            pc=PlotCollection(pf,'c')
            p=pc.add_profile_sphere(40.0,'kpc',["CellMassMsun","Mfrac"],weight=None,x_bins=100,x_log=True,x_bounds=[1.0e4,1.0e8])
            p.set_log_field(False)
            p2=pc.add_profile_sphere(40.0,'kpc',["CellMassMsun","Mfrac"],weight=None,x_bins=100,x_log=True,x_bounds=[1.0e4,1.0e8],accumulation=True)
            p2.set_log_field(False)
            pc.save("Enzo_histogram")
