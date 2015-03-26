'''
Find the halo with with the most number of particles that most closely
matches the given halo property, and then find its 
Most Massive Progenitor Branch (MMPB) properties.

The last snapshot's Rockstar catalogs are used to find the host halo and
the Consistent Merger Trees for the MMPB.  
'''
import os, sys, argparse
import subprocess
from glob import glob


def parse():
    '''
    Parse command line arguments
    ''' 
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter,
                                     description='''\
                                 Find the halo with with the most number of particles that most 
                                 closely matches the given halo property, and then find its 
                                 Most Massive Progenitor Branch (MMPB) properties.
                                 ''')
 
    parser.add_argument('sim_dirs', nargs='+', help='Simulation directories to be analyzed.')

    parser.add_argument('-p','--props', nargs='+', default=['Mvir'],
                        help='Halo properties to use for matching in each of the sim_dirs. '\
                            "You can use 'Mvir'(default), 'Vmax', 'Rvir', 'Vel' or 'Spin'.")

    parser.add_argument('-v','--prop_values', nargs='+', default=[1e11], type=float,
                        help='Halo property values to use for matching in each of the sim_dirs.')

    parser.add_argument('--rockstar_out_dir',default='sim_dir/analysis/rockstar_output/',
                        help='Directory where rockstar output can be found.') 

    parser.add_argument('--out_dir',default='sim_dir/analysis/catalogs/',
                        help='Directory where the output will be placed.') 

    args = vars(parser.parse_args())
    return args


def cat_and_generateIrate(snap_number, sim_dir, rockstar_out_dir, out_dir):
    '''
    Cat together the catalogs for the last snapshot in the snapshots set
    found in sim_dir and generate an irate.hdf5 catalog.

    Parameters
    ----------
    snap_number : str or int
         The snapshot number (as in the Rockstar catalogs) of the catalog 
         to write into an IRATE file
    
    sim_dir : str
         Simulation directory to be analyzed

    rockstar_out_dir: str
         Directory where Rockstar output can be found

    out_dir: str
         Directory where the IRATE catalog will be placed

    Returns
    -------
    irate_file : str
    
    '''
    
    snap_number = int(snap_number)

    # Cat all catalogs with the same snap number into one
    cmd = "cat %s/halos_%d.*.ascii > %s/halos_%d.ascii"%(rockstar_out_dir, snap_number, 
                                                         rockstar_out_dir, snap_number)
    print cmd
    #cmd_output = subprocess.check_output(cmd.split(' ')) # cat not working with subprocess
    cmd_output = os.system(cmd)
    if cmd_output != 0: 
        print cmd_output
        sys.exit(1)

    # Generate IRATE catalog
    irate_file = "%s/%s_rockstar_halos_%d_irate.hdf5" % (out_dir, sim_dir.split('/')[-1].replace('/',''),
                                                         snap_number)
    cmd = "rockstar2irate %s/halos_%d.ascii %s %d --param=%s/rockstar.cfg" \
        % (rockstar_out_dir, snap_number, irate_file, snap_number, rockstar_out_dir )
    print cmd
    cmd_output = subprocess.call(cmd.split(' '))
    if cmd_output != 0: 
        print cmd_output
        sys.exit(1)
        
    print '\nSuccesfully generated IRATE catalog\n'
    return irate_file

if __name__ == "__main__":

    args = parse()

    from visnap.general import find_halos
    import numpy as np

    print '\nStarting '+ sys.argv[0]
    print 'Parsed arguments: '
    print args
    print

    sim_dirs = args['sim_dirs']
    print 'Analyzing ', sim_dirs

    out_dir, rockstar_out_dir = args['out_dir'], args['rockstar_out_dir']
    modify_outdir = modify_rockstar_outdir = 0
    if  'sim_dir' in out_dir: 
        out_dir = out_dir.replace('sim_dir','')
        modify_outdir = 1   
    if  'sim_dir' in rockstar_out_dir: 
        rockstar_out_dir = rockstar_out_dir.replace('sim_dir','')
        modify_rockstar_outdir = 1   

    props, prop_values = args['props'], args['prop_values'] 
    if len(sim_dirs) != len(prop_values):
        print 'You have to provide the same number of prop_values as that of sim_dirs'
        sys.exit()

    if len(props) < len(sim_dirs):
        props_ext = np.empty(len(sim_dirs)-len(props))
        props_ext[:] = props[-1]
        props = np.concatenate((props,props_ext))

    for i, sim_dir in enumerate(sim_dirs):
        
        sim_dir = os.path.expandvars(sim_dir)
        sim_dir = os.path.abspath(sim_dir)

        if modify_outdir:  out_dir = sim_dir+'/'+out_dir
        if modify_rockstar_outdir: rockstar_out_dir = sim_dir+'/'+rockstar_out_dir

        if not os.path.exists(out_dir): os.makedirs(out_dir)
        
        # Extract the last catalog snap number
        catalogs = glob(rockstar_out_dir+'/*.ascii')
        catalogs = [catalog.split('/')[-1] for catalog in catalogs]
        catalogs = [catalog.split('.')[0] for catalog in catalogs]
        catalogs_numbers = [int(catalog.replace('halos_','')) for catalog in catalogs ]
        catalogs_numbers.sort()
        last_catalog_number = catalogs_numbers[-1]    

        # Cat and generate IRATE
        irate_file = cat_and_generateIrate(last_catalog_number, sim_dir, rockstar_out_dir, out_dir)

        # Find host halo
        print 'Finding galaxy host halo and MMPB for ',sim_dir
        halo, dist = find_halos.find_zoom_halo(None, None, irate_file, last_catalog_number,
                                               'Rockstar', prop=props[i], prop_value=prop_values[i],
                                               N_mostparticles=5)
        halo.print_properties()                                       
                                               
        # Find and save MMPB
        halo_past_props = halo.track(trees_path=rockstar_out_dir+'/trees/')
        cmd = 'ln -s %s/trees/*.hdf5 %s/%s'%(rockstar_out_dir, out_dir, 'rockstar_trees.hdf5')
        cmd_output = os.system(cmd)
        if cmd_output != 0: print cmd_output
        mmpb_file  = '%s/%s_halo%d_mmpb_props'%(out_dir, sim_dir.split('/')[-1], halo.id)

        print '\nSuccefully found host halo and its MMPB properties'
        print 'Saving MMPB properties to ',mmpb_file
        np.save(mmpb_file, halo_past_props)
        
