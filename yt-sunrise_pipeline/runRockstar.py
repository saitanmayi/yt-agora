'''
Run Rockstar for a set of snapshots in the given simulation directories

You must run this script using MPI, on Edison the following works:

    source /project/projectdirs/agora/scripts/activate_yt-agora.sh
    module load mpi4py 
    aprun -np Ncpus python-mpi run_rockstar.py 

Ncpus must be at least 3, 1 server, 1 reader and 1 worker/writer

by Miguel Rocha  - miguel@scitechanalytics.com
'''
import os, sys, argparse
import subprocess
from glob import glob

if __name__ != '__main__':
    import yt
    from yt.analysis_modules.halo_finding.rockstar.api import RockstarHaloFinder
    from yt.data_objects.particle_unions import  ParticleUnion
    from yt.data_objects.static_output import _cached_datasets
    try:
        from mpi4py import MPI
    except ImportError:
        print "ERROR: Unable to import mpi4py, did you do 'module load mpi4py'?" 
        sys.exit(1)
    yt.enable_parallelism()

           
def parse():
    '''
    Parse command line arguments
    ''' 
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter,
                                     description='''\
                                 Run Rockstar for a set of snapshots from a list of directories.
                                 You must run this script using MPI, on Edison the following works:
                                      source /project/projectdirs/agora/scripts/activate_yt-agora.sh &&
                                      module load mpi4py &&
                                      aprun -np Ncpus python-mpi run_rockstar.py.
                                 Ncpus must be at least 3, 1 server, 1 reader and 1 worker/writer
                                 ''')

    parser.add_argument('sim_dirs', nargs='+', help='Simulation directories to be analyzed')
    
    parser.add_argument('-s', '--snap_base', nargs='+', default=['10MpcBox_csf512_'],
                        help='Base name of the snapshot files for which you want to run rockstar. '\
                            'You can use wild cards, and provide more than one if a different SNAP_BASE '\
                            'is to be used for each of the provided SIM_DIRS')
    
    parser.add_argument('--particle_types', nargs='+', default=["darkmatter"],
                        help='The particle types to use for halo finding, as named in yt fields or '\
                            'derived fields. These can be filtered or inherent types. '\
                            'If particles with different masses are found for the given particle_types '\
                            'only the particles with the lowest mass will be used, unless the '\
                            '--multi_mass option is given.')

    parser.add_argument('--recognized_star_types', nargs='+', default=["stars", "specie5"],
                        help='Particle types to be recognized as stars. All types in particle_types '\
                            'that are not included in this list will be treated as dark matter particles.')

    parser.add_argument('--multi_mass', action='store_true', default=False,
                        help='If this option is given all the particle species in particle_types'\
                            'will be passed to Rockstar even if they have different masses.')

    parser.add_argument('--force_res', nargs=1, default=None, type=float,
                        help='Force resolution in units of Mpc/h. Halos whose centers are closer than '\
                            'FORCE_RES are usually noise, and are subject to stricter removal tests '\
                            'than other halos. If no value is provided, this parameter is automatically '\
                            'set to the width of the smallest grid element in the simulation from the '\
                            'last data snapshot (i.e. the one where time has evolved the longest).')

    parser.add_argument('--initial_metric_scaling', nargs=1, default=1, type=float,
                        help='The position element of the fof distance metric is divided by this '\
                            'parameter, set to 1 by default. If the initial_metric_scaling=0.1 the '\
                            'position element will have 10 times more weight than the velocity element, '\
                            'biasing the metric towards position information more so than velocity '\
                            'information. That was found to be needed for hydro-ART simulations with '\
                            "with 10's of parsecs resolution.")

    parser.add_argument('--out_dir',default='sim_dir/analysis/rockstar_output',
                        help='Directory where the Rockstar output will be placed')
    
    parser.add_argument('--num_readers', nargs=1, default=1, type=int,
                        help='If the number of files per snapshot is more than one, setting '\
                            'num_readers > 1 can help I/O performance.')

    parser.add_argument('--no_merger_trees', action='store_true', default=False ,
                        help='By default merger trees will be generated with the snapshots found '\
                            'in OUT_DIR. If this option is given merger trees will not be generated.') 

    args = vars(parser.parse_args())
    return args


def run_rockstar(sim_dir, snap_base='*', particle_types=["darkmatter"],
                 recognized_star_types=["stars", "specie5"], multi_mass=False,
                 force_res=None, initial_metric_scaling=1, out_dir="rockstar_output",
                 num_readers=1):
    '''
    Run Rockstar for a set of snapshots in the given simulation directory

    Parameters
    ----------
    sim_dir : str
         Simulation directory to be analyzed

    snap_base : str
         Snapshot files to be analyzed. You can use wild cards in SNAP_BASE
         to select a set of snapshots that match a given pattern

    particle_types: str list/array
         The particle types to use for halo finding, as named in yt fields or  
         derived fields. This can be filtered or inherent types.
         If particles with different masses are found for the given particle_types
         only the particles with the lowest mass will be used, unless the 
         multi_mass option is set to True

    recognized_star_types: str list/array
         Particle types to be recognized as stars. All types in particle_types 
         that are not included in this list will be treated as dark matter particles

    multi_mass : bool
         If True all the particle species in particle_types will be passed to 
         Rockstar even if they have different masses

    force_res : float
         Force resolution in units of Mpc/h. Halos whose centers are closer than 
         FORCE_RES are usually noise, and are subject to stricter removal tests
         than other halos. If no value is provided, this parameter is automatically 
         set to the width of the smallest grid element in the simulation from the
         last data snapshot (i.e. the one where time has evolved the longest)

    initial_metric_scaling : float
         The position element of the fof distance metric is divided by this 
         parameter, set to 1 by default. If the initial_metric_scaling=0.1 the
         position element will have 10 times more weight than the velocity element,
         biasing the metric towards position information more so than velocity
         information. That was found to be needed for hydro-ART simulations with
         with 10's of parsecs resolution

    out_dir : str
         Directory where the Rockstar output will be placed

    num_readers : int
         If the number of files per snapshot is more than one, setting
         num_readers > 1 can help I/O performance
    
    Returns
    -------
    None

    '''
    if MPI.COMM_WORLD.Get_rank()==0:
        print
        print 'Beginning Rockstar analysis in ', sim_dir
        print 'Placing output in ', out_dir
   
    # Generate data series
    snap_base = sim_dir+ '/' + snap_base + '*'
    ts = yt.DatasetSeries(snap_base)
    if len(ts) > 1:
        first_snap = ts[0]
        last_snap = ts[-1]
        if MPI.COMM_WORLD.Get_rank()==0:    
            print 'first snapshot: ', first_snap.basename
            print 'last snapshot: ', last_snap.basename    
    else:
        last_snap = ts[0]
        if MPI.COMM_WORLD.Get_rank()==0:    
            print 'snapshot: ', last_snap.basename    

    # Create particle union if needed    
    punion=None
    if len(particle_types) > 1:
        punion = ParticleUnion("rockstar_analysis_particles", particle_types)
        last_snap.add_particle_union(punion)
        particle_type = "rockstar_analysis_particles"
    else:
        particle_type = particle_types[0]
    ad = last_snap.all_data()
    particle_masses = yt.np.unique(ad[(particle_type, 'particle_mass')].in_units('Msun/h'))
    total_particles = ad.quantities.total_quantity((particle_type, "particle_ones"))
  
    if MPI.COMM_WORLD.Get_rank()==0:
        print 'Using particle(s) ', particle_types, ' with mass(es) ', particle_masses 
        print

    # Get the particle_type field of the star particles, and the min mass of the DM particles    
    dm_masses = []
    star_types = []
    for type in particle_types:
        if  type in recognized_star_types:
            star_types = yt.np.concatenate((star_types, yt.np.unique(ad[(type, 'particle_type')])))
        else:
            dm_masses = \
                yt.np.concatenate((dm_masses,yt.np.unique(ad[(type, 'particle_mass')].in_units('Msun/h'))))
    dm_masses = last_snap.arr(dm_masses.value, 'Msun/h')
    dm_min_mass = dm_masses.min()

    # In not multi mass select only the DM particles with the min mass
    if not multi_mass and len(particle_masses) > 1:
        @yt.particle_filter('hires_particles', filtered_type=particle_type, requires=['particle_mass'])
        def _hires_filter(pfilter, data):
            return data['particle_mass'] == dm_min_mass

        def setup_ds(ds):
            if punion: ds.add_particle_union(punion)
            ds.add_particle_filter('hires_particles')

        particle_type = 'hires_particles'    
    else:
        def setup_ds(ds):
            if punion: ds.add_particle_union(punion)

    # Remove last/first_snap from memory and cache
    if len(ts) > 1 : del first_snap
    del last_snap
    _cached_datasets.clear()

    # Pass the setup_function to the time series  
    ts._setup_function=setup_ds
    
    # Run rockstar         
    rh = RockstarHaloFinder(ts, 
                            num_readers=num_readers,
                            num_writers=None,
                            outbase=out_dir,
                            particle_type=particle_type,
                            star_types=star_types,
                            multi_mass=multi_mass,
                            force_res=force_res, 
                            initial_metric_scaling=initial_metric_scaling,
                            particle_mass=dm_min_mass,
                            total_particles=total_particles)
    MPI.COMM_WORLD.barrier()    
    rh.run()
    MPI.COMM_WORLD.barrier()

    if MPI.COMM_WORLD.Get_rank()==0:
        print 'Successfully finished Rockstar analysis in ', sim_dir
        print


def run_merger_trees(rockstar_out_dir, rockstar_src_dir="$ROCKSTAR_DIR",
                     consistent_trees_dir="$AGORA_PIPE_INSTALL/packages/consistent-trees"):
    '''
    Run consistent-trees using the rockstar catalogs found in rockstar_out_dir
    '''
    
    print
    print 'Generating merger trees in ', rockstar_out_dir

    dirs = [rockstar_out_dir, rockstar_src_dir, consistent_trees_dir]
    for i,dir in enumerate(dirs):
          dir = os.path.expandvars(dir)
          dir = os.path.abspath(dir)
          dirs[i] = dir
    rockstar_out_dir, rockstar_src_dir, consistent_trees_dir = dirs      
          
    cmd = "perl %s/scripts/gen_merger_cfg.pl %s/rockstar.cfg "%(rockstar_src_dir, rockstar_out_dir)
    print cmd
    cmd_output = subprocess.check_output(cmd.split(' '))
    print cmd_output
    
    owd = os.getcwd()
    os.chdir(consistent_trees_dir)
    merger_cfg = "%s/outputs/merger_tree.cfg"%rockstar_out_dir
    cmd = "perl do_merger_tree.pl %s"%merger_cfg
    print cmd
    cmd_output =  subprocess.check_output(cmd.split(' '))
    print cmd_output
    os.chdir(owd)
    
    print 'Successfully generated merger trees in %s/trees' % (rockstar_out_dir)
    print 



if __name__ == "__main__":

    args = parse()
    
    import yt
    from yt.analysis_modules.halo_finding.rockstar.api import RockstarHaloFinder
    from yt.data_objects.particle_unions import ParticleUnion
    from yt.data_objects.static_output import _cached_datasets
    try:
        from mpi4py import MPI
    except ImportError:
        if MPI.COMM_WORLD.Get_rank()==0:
            print "ERROR: Unable to import mpi4py, did you do 'module load mpi4py'?" 
        sys.exit(1)
    yt.enable_parallelism()
  
    if MPI.COMM_WORLD.Get_rank()==0:
        print 'Starting '+ sys.argv[0]
        print 'Parsed arguments: '
        print args
        print

    # Get parsed arguments    
    sim_dirs = args['sim_dirs']
    if MPI.COMM_WORLD.Get_rank()==0:
        print 'Halo finding in ',sim_dirs
    
    out_dir = args['out_dir']
    modify_outdir = 0    
    if  'sim_dir' in out_dir: 
        out_dir = out_dir.replace('sim_dir','')
        modify_outdir = 1   
    
    snap_base = args['snap_base']
    
    # Loop over simulation directories
    for i, sim_dir in enumerate(sim_dirs):
        sim_dir = os.path.expandvars(sim_dir)
        sim_dir = os.path.abspath(sim_dir)
        if modify_outdir:
            out_dir = sim_dir+'/'+out_dir
        if not os.path.exists(out_dir):
            if MPI.COMM_WORLD.Get_rank()==0:
                os.makedirs(out_dir)
        if len(snap_base) == 1: 
            snap_base = snap_base[0]
        else:
            snap_base = snap_base[i]

        run_rockstar(sim_dir,
                     snap_base=snap_base,
                     particle_types=args["particle_types"],
                     recognized_star_types=args["recognized_star_types"],
                     multi_mass=args["multi_mass"],
                     force_res=args['force_res'],
                     initial_metric_scaling=args['initial_metric_scaling'],
                     out_dir=out_dir,
                     num_readers=args['num_readers'])
            
        if MPI.COMM_WORLD.Get_rank()==0:
            if not args['no_merger_trees']: run_merger_trees(out_dir)
        MPI.COMM_WORLD.barrier()

    
