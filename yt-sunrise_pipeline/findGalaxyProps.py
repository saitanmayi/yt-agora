'''
Find the properties of the galaxy found within a halo over time.
The Most Massive Progenitor Branch (MMPB) properties of the halo 
are needed as input.

by Miguel Rocha  - miguel@scitechanalytics.com
'''
import os, sys, argparse
from glob import glob
import numpy as np
from visnap.general.halo_particles import axis_ratios


def parse():
    '''
    Parse command line arguments
    ''' 
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter,
                                     description='''\
                                 Find the properties of the galaxy found within a halo over time.
                                 The Most Massive Progenitor Branch (MMPB) properties of the halo
                                 are needed as input.                            
                                 ''')
 
    parser.add_argument('sim_dirs', nargs='+', help='Simulation directories to be analyzed.')

    
    parser.add_argument('-s', '--snap_base', default='10MpcBox_csf512_',
                        help='Base of the snapshots file names.') 

    parser.add_argument('-c', '--center', default='hist',
                        help='The location to use as the center of the stellar component. Can be '\
                             "'max_dens' (for the location of the maximum stellar density), 'com' "\
                            "(for the center of mass), or 'hist' (for a iteratively refined mass "\
                            "weighted histogram).")

    parser.add_argument('-r', '--sc_sphere_r', default=0.25, type=float,
                        help='The radius to use for the sphere enclosing the stellar center in units of Rvir.')

    parser.add_argument( '--shapes_nrad', default=10, type=int,
                        help='Number of radii to calculate shapes for.')

    parser.add_argument( '--shapes_rmax', default=20.0, type=float,
                         help='Maximum radius to calculate shapes at.')


    parser.add_argument( '--mmpb_file', default='sim_dir/analysis/catalogs/*_mmpb_props.npy',
                        help='File containing the Most Massive Progenitor branch properties. '\
                             'A python dictionary is expected as generated by findHostandMMPB.py.')

    parser.add_argument('--out_dir',default='sim_dir/analysis/catalogs/',
                        help='Directory where the output will be placed.') 

    args = vars(parser.parse_args())
    return args


def find_hist_center(positions, masses):
    '''
    Find the center of a particle distribution by interactively refining 
    a mass weighted histogram
    '''
    pos = np.array(positions)
    masses = np.array(masses)
    if len(pos) == 0: 
        return None
    mass_current = masses
    old_center = np.array([0,0,0])
    refined_pos = pos.copy()
    refined_mas = mass_current.copy()
    refined_dist = 1e20
    nbins=3
    center = None

    dist = lambda x,y:np.sqrt(np.sum((x-y)**2.0))
    dist2 = lambda x,y:np.sqrt(np.sum((x-y)**2.0,axis=1))

    j=0
    while len(refined_pos)>1e1 or j==0: 
        table,bins=np.histogramdd(refined_pos, bins=nbins, weights=refined_mas)
        bin_size = min((np.max(bins,axis=1)-np.min(bins,axis=1))/nbins)
        centeridx = np.where(table==table.max())
        le = np.array([bins[0][centeridx[0][0]],
                       bins[1][centeridx[1][0]],
                       bins[2][centeridx[2][0]]])
        re = np.array([bins[0][centeridx[0][0]+1],
                       bins[1][centeridx[1][0]+1],
                       bins[2][centeridx[2][0]+1]])
        center = 0.5*(le+re)
        refined_dist = dist(old_center,center)
        old_center = center.copy()
        idx = dist2(refined_pos,center)<bin_size
        refined_pos = refined_pos[idx]
        refined_mas = refined_mas[idx]
        j+=1    

    return center


def find_shapes(center, pos, ds, nrad=10, rmax=None):
    '''
    Find the shape of the given particle distribution at nrad different 
    radii, spanning from 0.1*rmax to rmax. 
    rmax = max(r(pos)) if not given.
    '''

    print 'Starting shape calculation'

    units = center.units
    center = center.value

    try:
        pos = np.array([pos[:,0] - center[0],
                        pos[:,1] - center[1],
                        pos[:,2] - center[2]]).transpose()
        pos = ds.arr(pos, units)
        pos = pos.in_units(units).value
        r = np.sqrt(pos[:,0]**2 + pos[:,1]**2 + pos[:,2]**2)
    except IndexError: # no stars found
        pos = np.array([])   

    if len(pos) > 1: 
        if not rmax: rmax = r.max()
        radii = np.linspace(0.1*rmax, rmax, nrad)
    else:
        radii = np.array([])
    
    c_to_a = np.empty(radii.size)     
    b_to_a = np.empty(radii.size)
    axes = []
        
    for i,r in enumerate(radii):
        # get shapes
        try:
            axis_out = axis_ratios(pos, r, axes_out=True, fix_volume = False)
            c_to_a[i] = axis_out[0][0]
            b_to_a[i] = axis_out[0][1]
            axes.append(axis_out[1])
        except UnboundLocalError:
            print 'Not enough particles to find shapes at r = %g in snapshot %s'%(r, ds.parameter_filename )
            b_to_a[i] = c_to_a[i] = None
            axes.append([])
    
    return radii, c_to_a, b_to_a, axes        
       

def L_crossing(x, y, z, vx, vy, vz, weight, center):
    x, y, z = x-center[0], y-center[1],z-center[2]
    cx, cy, cz = y*vz - z*vy, z*vx - x*vz, x*vy - y*vx
    lx, ly, lz = [np.sum(l * weight) for l in [cx, cy, cz]]
    L = np.array([lx, ly, lz])
    L /= np.sqrt(np.sum(L*L))
    return L


if __name__ == "__main__":

    args = parse()

    import yt

    print '\nStarting analysis for '+ sys.argv[0]
    print 'Parsed arguments: '
    print args
    print

    # Get parsed values
    sim_dirs, snap_base = args['sim_dirs'], args['snap_base']
    print 'Analyzing ', sim_dirs

    out_dir = args['out_dir']
    modify_outdir = 0
    if  'sim_dir' in out_dir: 
        out_dir = out_dir.replace('sim_dir','')
        modify_outdir = 1 

    mmpb_file = args['mmpb_file']
    modify_mmpb_file = 0
    if  'sim_dir' in mmpb_file: 
        mmpb_file = mmpb_file.replace('sim_dir','')
        modify_mmpb_file = 1

    center = args['center']
    sc_sphere_r = args['sc_sphere_r']
    shapes_nrad, shapes_rmax = args['shapes_nrad'], args['shapes_rmax']
    
        
    # Loop over simulation directories    
    for sim_dir in sim_dirs:
        
        # Set paths and file names
        sim_dir = os.path.expandvars(sim_dir)
        sim_dir = os.path.abspath(sim_dir)

        if modify_outdir:  out_dir = sim_dir+'/'+out_dir
        if modify_mmpb_file: mmpb_file = sim_dir+'/'+mmpb_file

        if not os.path.exists(out_dir): os.makedirs(out_dir)

        # Get the MMPB properties
        mmpb_files = glob(mmpb_file)
        if len(mmpb_files) > 1:
            print 'More than one file matches %s, '\
                'the supplied file name for the MMPB properties. '\
                'Set which file you want to use with --mmpb_file'\
                % (mmpb_file)
            sys.exit()
        else:
            mmpb_file = mmpb_files[0]
            mmpb_props = np.load(mmpb_file)[()] 
    
        # Generate data series
        snaps = glob(sim_dir+'/'+snap_base+'*')
        ts = yt.DatasetSeries(snaps)

        # Initialize galaxy properties dictionary 
        galaxy_props = {}
        fields = ['scale', 'stars_total_mass', 'stars_com', 'stars_maxdens', 'stars_hist_center',
                  'stars_rhalf', 'stars_mass_profile', 'stars_c_to_a', 'stars_b_to_a',
                  'stars_shape_axes', 'dm_c_to_a', 'dm_b_to_a', 'dm_shape_axes', 'stars_L',
                  'gas_total_mass', 'gas_maxdens', 'gas_L']
        for field in fields: 
            if field in ['scale', 'stars_total_mass', 'stars_rhalf', 'gas_total_mass' ]:
                galaxy_props[field] = np.array([])                
            else :
                galaxy_props[field] = []
        
        # Loop over snapshots
        for ds in reversed(ts):

            scale = round(1.0/(ds.current_redshift+1.0),4)
            if scale not in mmpb_props['scale']:
                continue

            print '\nFinding galaxy properties for snapshot ', ds.parameter_filename.split('/')[-1]
            print ''

            galaxy_props['scale'] = np.append(galaxy_props['scale'], scale)
            idx = np.argwhere(mmpb_props['scale'] == scale)[0][0]

            # Generate sphere selection
            halo_center = ds.arr([mmpb_props['x'][idx], mmpb_props['y'][idx],
                                  mmpb_props['z'][idx]], 'Mpccm/h') # halo props are in Rockstar units
            halo_rvir = ds.arr(mmpb_props['rvir'][idx], 'kpccm/h')  
            hc_sphere = ds.sphere(halo_center, halo_rvir)

            # Get total stellar mass 
            stars_mass = hc_sphere[('stars', 'particle_mass')].in_units('Msun')
            stars_total_mass = stars_mass.sum().value[()]
            galaxy_props['stars_total_mass'] = np.append(galaxy_props['stars_total_mass'],
                                                         stars_total_mass)

            # Get center of mass of stars
            stars_pos_x = hc_sphere[('stars', 'particle_position_x')].in_units('kpc')
            stars_pos_y = hc_sphere[('stars', 'particle_position_y')].in_units('kpc')
            stars_pos_z = hc_sphere[('stars', 'particle_position_z')].in_units('kpc')
            stars_com = np.array([np.dot(stars_pos_x, stars_mass)/stars_total_mass, 
                                  np.dot(stars_pos_y, stars_mass)/stars_total_mass, 
                                  np.dot(stars_pos_z, stars_mass)/stars_total_mass])
            galaxy_props['stars_com'].append(stars_com)
            
            # Get max density of stars (value, location)
            stars_maxdens = hc_sphere.quantities.max_location(('deposit', 'stars_cic'))
            stars_maxdens_val = stars_maxdens[0].in_units('Msun/kpc**3').value[()]
            stars_maxdens_loc = np.array([stars_maxdens[2].in_units('kpc').value[()], 
                                          stars_maxdens[3].in_units('kpc').value[()], 
                                          stars_maxdens[4].in_units('kpc').value[()]])
            galaxy_props['stars_maxdens'].append((stars_maxdens_val, stars_maxdens_loc))

            # Get refined histogram center of stars
            stars_pos = np.array([stars_pos_x, stars_pos_y, stars_pos_z]).transpose()
            stars_hist_center = find_hist_center(stars_pos, stars_mass)
            galaxy_props['stars_hist_center'].append(stars_hist_center)

            # Define center of stars
            if center == 'max_dens': stars_center = stars_maxdens_loc
            elif center == 'com': stars_center = stars_com
            else: stars_center = stars_hist_center
            stars_center = ds.arr(stars_center, 'kpc')
   
            # Get shape of stars
            radii, c_to_a, b_to_a, axes = \
                find_shapes(stars_center, stars_pos, ds, shapes_nrad, shapes_rmax)
            galaxy_props['stars_c_to_a'].append((radii, c_to_a))
            galaxy_props['stars_b_to_a'].append((radii, b_to_a))    
            galaxy_props['stars_shape_axes'].append((radii, axes))

            # Get shape of dm
            dm_pos_x = hc_sphere[('darkmatter', 'particle_position_x')].in_units('kpc')
            dm_pos_y = hc_sphere[('darkmatter', 'particle_position_y')].in_units('kpc')
            dm_pos_z = hc_sphere[('darkmatter', 'particle_position_z')].in_units('kpc')
            dm_pos = np.array([dm_pos_x, dm_pos_y, dm_pos_z]).transpose()
            radii, c_to_a, b_to_a, axes = \
                find_shapes(stars_center, dm_pos, ds, shapes_nrad, shapes_rmax)
            galaxy_props['dm_c_to_a'].append((radii, c_to_a))
            galaxy_props['dm_b_to_a'].append((radii, b_to_a))    
            galaxy_props['dm_shape_axes'].append((radii, axes))

            # Get stellar density profile
            ssphere_r = sc_sphere_r*halo_rvir.in_units('code_length')
            while ssphere_r < ds.index.get_smallest_dx():
                ssphere_r = 2.0*ssphere_r
            sc_sphere =  ds.sphere(stars_center, ssphere_r)
            try:
                p_plot = yt.ProfilePlot(sc_sphere, 'radius', 'stars_mass', n_bins=100,
                                        weight_field=None, accumulation=True)
                p_plot.set_unit('radius', 'kpc')
                p_plot.set_unit('stars_mass', 'Msun')
                p = p_plot.profiles[0]
                radii, smass = p.x.value, p['stars_mass'].value 
                rhalf = radii[smass >= 0.5*smass.max()][0]
            except (IndexError, ValueError): # not enough stars found
                radii, smass = None, None 
                rhalf = None
            galaxy_props['stars_rhalf'] = np.append(galaxy_props['stars_rhalf'], rhalf)
            galaxy_props['stars_mass_profile'].append((radii, smass))             

            # Get angular momentum of stars
            try:
                x, y, z = [sc_sphere[('stars', 'particle_position_%s'%s)] for s in 'xyz'] 
                vx, vy, vz = [sc_sphere[('stars', 'particle_velocity_%s'%s)] for s in 'xyz'] 
                mass = sc_sphere[('stars', 'particle_mass')]
                metals = sc_sphere[('stars', 'particle_metallicity')]
                stars_L = L_crossing(x, y, z, vx, vy, vz, mass*metals, sc_sphere.center)
            except IndexError: # no stars found
                stars_L = [None, None, None]
            galaxy_props['stars_L'].append(stars_L)
            del(sc_sphere)

            # Get total mass of gas
            gas_mass = hc_sphere[('gas', 'cell_mass')].in_units('Msun')
            gas_total_mass = gas_mass.sum().value[()]
            galaxy_props['gas_total_mass'] = np.append(galaxy_props['gas_total_mass'], 
                                                       gas_total_mass)
            
            # Get max density of gas
            gas_maxdens = hc_sphere.quantities.max_location(('gas', 'density'))
            gas_maxdens_val = gas_maxdens[0].in_units('Msun/kpc**3').value[()]
            gas_maxdens_loc = np.array([gas_maxdens[2].in_units('kpc').value[()], 
                                        gas_maxdens[3].in_units('kpc').value[()], 
                                        gas_maxdens[4].in_units('kpc').value[()]])
            galaxy_props['gas_maxdens'].append((gas_maxdens_val, gas_maxdens_loc)) 
            
            # Get angular momentum of gas
            gas_center = ds.arr(gas_maxdens_loc, 'kpc')
            gc_sphere =  ds.sphere(gas_center, ssphere_r)
            x, y, z = [gc_sphere[('index', '%s'%s)] for s in 'xyz'] 
            vx, vy, vz = [gc_sphere[('gas', 'momentum_%s'%s)] for s in 'xyz'] # momentum density
            cell_volume = gc_sphere[('index', 'cell_volume')]
            metals = gc_sphere[('gas', 'metal_ia_density')] + gc_sphere[('gas', 'metal_ii_density')]
            gas_L = L_crossing(x, y, z, vx, vy, vz, metals*cell_volume**2, gc_sphere.center)
            galaxy_props['gas_L'].append(gas_L)
            del(gc_sphere)
                               
            del(hc_sphere)                    

        # Save galaxy props
        galaxy_props_file = mmpb_file.replace('mmpb', 'galaxy')    
        print '\nSuccessfully computed galaxy properties'
        print 'Saving galaxy properties to ', galaxy_props_file
        print
        np.save(galaxy_props_file, galaxy_props)     
