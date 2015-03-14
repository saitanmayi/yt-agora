'''
Generate the configuration files required to run Sunrise and
setup the Sunrise simulation directory with everything
necessary to submit.
'''
import os, sys, argparse
from glob import glob
import numpy as np
import shutil
import pyfits  


def parse():
    '''
    Parse command line arguments
    ''' 

    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter,
                                     description='''\
                                Generate the configuration files required to run Sunrise and
                                setup the Sunrise simulation directory with everything
                                necessary to submit.
                                ''')
    
    parser.add_argument('sim_dirs', nargs='+', 
                        help='Simulation directories to setup Sunrise runs for.')
    
    parser.add_argument('--mcrx', nargs='+', default=[],
                        help='Add mcrx.config options in the style --mcrx=nrays:1e7')
    
    parser.add_argument('--sfrhist',nargs='+', default=[],
                        help='Add sfrhist.config options in the style --sfrhist=multiphase:false')
    
    parser.add_argument('--broadband',nargs='+', default=[],
                        help='Add broadband.config options in the style --broadband=redshift:2.0')
    
    parser.add_argument('--pbs', nargs='+', default=[],
                        help='Add PBS options in the style --pbs=ncpus:24')
    
    parser.add_argument('--parameter_set', nargs='+', default=[],
                        help='Shortcut for choosing a set of config parameters')
    
    parser.add_argument('--ffov', default=None,
                        help='Change the camera/s FOV by a fractional amount')
    
    parser.add_argument('--fovcam', default=None, type=int,
                        help='If fovcam is given (as int), only change this camera FOV by a '\
                            'fractional amount given by --ffov')
    
    parser.add_argument('--random_cameras', default=None,
                        help='Add some number of randomly oriented cameras. Seed=Halo#')
    
    parser.add_argument('--limit_cameras', default=10,
                        help='Limit the number of cameras, generally to cut '\
                            'down on the random cameras')
 
    parser.add_argument('--moviecam', default=False, help='Limit to two cameras')
  
    parser.add_argument('--overwrite',action='store_true', default=False,
                        help='If the run directory already exist overwrite it')
    
    parser.add_argument('--short_broadband', action='store_true',
                        help='Use short filter files and skip redshifting broadbands and calzetti')
    
    parser.add_argument('--cut_radius', default=None, type=float,
                        help='Remove particles outside this radius (in [kpc])')
    
    parser.add_argument('--min_age',  default=None,
                        help='Remove particles with ages below this age (in [years])')
    
    parser.add_argument('--max_age', default=None,
                        help='Remove particles with ages above this age (in [years])')
    
    parser.add_argument('--fmass', default=None,
                        help='Multiple the mass of stars as a function of age. Format:'\
                            '10e7,0.9,100e7,1.1,500e7,1.5,1e9,1.0,1e15')
    
    parser.add_argument('--fmetallicity', default=None,
                        help='Multiple the metallicity of stars as a function of age. Format:'\
                            '10e7,0.9,100e7,1.1,500e7,1.5,1e9,1.0,1e15')
    
    parser.add_argument('--fism_temp', default=None,
                        help='Modify the ISM temperature as a function of the original temperature. '\
                            'Format:1e0,0.9,1e3,1.0,1e4,1.5,1e5,2.0,1e6')
    
    parser.add_argument('--dryrun', action='store_true', default=False,
                        help='Do not create any files just evaluate all possible.')
    
    parser.add_argument('--tolerant', action='store_true', default=False,
                        help='Wrap each generate run in a try except loop')
    
    parser.add_argument('--skip_calzetti', action='store_true', default=False,
                        help='Skip the Calzetti attenuation step')
    
    parser.add_argument('--skip_idl', action='store_true', default=True,
                        help='Skip IDL dependent blackbox step')
    
    parser.add_argument('--submit', action='store_true', default=False,
                        help='Submit job automatically using qsub')
    
    parser.add_argument('--impression_dir', default='$IMPRESSION',
                        help="Path to Chris Moody's impression package" )
    
    parser.add_argument('--sunrise_dir', default='$SUNRISE_DIR',
                        help='Path to Sunrise executables.')
    
#    parser.add_argument('--sunrise_ics_dir', default="$SUNRISE_ICS_DIR",
#                        help='Directory containing filters and models to use with Sunrise.')
    
    parser.add_argument('--input_dir', default='sim_dir/analysis/sunrise_analysis/',
                        help='Directory where to find the input FITS and camera files, '\
                            'and where the Sunrise runs will be setup. A subdirectory '\
                            'is expected for each snapshot, as created by genSunriseInput.py')
    
    args = vars(parser.parse_args())
    
    #check parameters in parameters_set
    for pset in args['parameter_set']:
        if pset not in parameter_sets.keys():
            parser.error("parameter_set must be: ".join(
                    parameter_sets.keys()))
            sys.exit()
            
    return args


parameter_sets = {
    'dustgrain':{'mcrx':{'dust_grain_file':'kext_albedo_WD_LMCavg_20',
                         'grain_model':None,
                         'wd01_parameter_set':None,
                         'use_dl07_opacities':None,
                         'template_pah_fraction':None,
                         'grain_data_directory':None
                         }
                 },
    'brent':{'mcrx':{'grain_model':'wd01_Brent_PAH',
                     'template_pah_fraction':0.5,
                     'dust_grain_file':None
                     }
             },
    'aux':{'mcrx':{ 'nrays_ir':'0',
                    'nrays_aux':'1e6',
                    'nrays_nonscatter':'1e3',
                    'nrays_scatter':'0',
                    'nrays_intensity':'0',
                    'ir_equilibrium_tolerance':'5.0', #very high for IR calc
                    'ir_luminosity_percentile':'0.99',
                    'integrate_ir':'false'
                    }
           },
    'mem0':{'sfrhist':{'mappings_sed_file':
                           os.path.expandvars('$SUNRISE_ICS_DIR/mappings/Smodel-lores256.fits')}},
    'mem1':{'sfrhist':{'mappings_sed_file':
                           os.path.expandvars('$SUNRISE_ICS_DIR/mappings/Smodel-lores128.fits')}},
    'mem2':{'sfrhist':{'mappings_sed_file':
                           os.path.expandvars('$SUNRISE_ICS_DIR/mappings/Smodel-lores64.fits')}},
    'mem3':{'sfrhist':{'mappings_sed_file':
                           os.path.expandvars('$SUNRISE_ICS_DIR/mappings/Smodel-lores32.fits')}},
    
    'ir0':{'mcrx':{ 'ir_luminosity_percentile':'0.90',
                    'ir_equilibrium_tolerance':'10.0'
                    }
           },
    'ir1':{'mcrx':{ 'ir_luminosity_percentile':'0.50',
                    'ir_equilibrium_tolerance':'1.0'
                    }
           },
    'ir2':{'mcrx':{'ir_luminosity_percentile':'0.10',
                   'ir_equilibrium_tolerance':'0.5'
                   }
           },
    'ir3':{'mcrx':{'ir_luminosity_percentile':'0.01',
                   'ir_equilibrium_tolerance':'0.1'
                   }
           },
    'ir4':{'mcrx':{'ir_luminosity_percentile':'0.005',
                   'ir_equilibrium_tolerance':'0.05'
                   }
           },
    'shortbroadband':{'pbs':{'FILTERSET':'filters_restframe_short',
                             'FILTERSETZ':'filters_redshifted_short',
                             'SHORTBROADBAND':'true'
                             }
                      },
    'skipir':{'mcrx':{'nrays_ir':'0',
                      'nrays_intensity':'0',
                      'integrate_ir':'false',
                      },
              'sfrhist':{'mappings_sed_file':
                             os.path.expandvars('$SUNRISE_ICS_DIR/mappings/Smodel-lores256.fits')},
              'pbs':{'PBS_NHOURS':'8',
                     'NHOURS':'8',
                     'WCL':'28800'
                     }
              },
    'noscatter':{ 'mcrx':{'n_scatter_min':'0',
                          'n_scatter_max':'0'
                          }
                  },
    'onlyscatter':{'mcrx':{ 'n_scatter_min':'1',
                            'n_scatter_max':None
                            }
                   },
    'allrays1':{'mcrx':{ 'nrays_aux':'1e1',
                         'nrays_nonscatter':'1e1',
                         'nrays_scatter':'1e1',
                         'nrays_ir':'1e1',
                         'nrays_intensity':'1e1'
                         }
                },
    'allrays6':{'mcrx':{ 'nrays_aux':'1e6',
                         'nrays_nonscatter':'1e6',
                         'nrays_scatter':'1e6',
                         'nrays_ir':'1e6',
                         'nrays_intensity':'1e6'}
                },
    'allrays7':{'mcrx':{ 'nrays_aux':'1e7',
                         'nrays_nonscatter':'1e7',
                         'nrays_scatter':'1e7',
                         'nrays_ir':'1e7',
                         'nrays_intensity':'1e7'
                         }
                },
    'allrays8':{'mcrx':{ 'nrays_aux':'1e8',
                         'nrays_nonscatter':'1e8',
                         'nrays_scatter':'1e8',
                         'nrays_ir':'1e8',
                         'nrays_intensity':'1e8'
                         }
                },
    'allrays9':{'mcrx':{ 'nrays_aux':'1e9',
                         'nrays_nonscatter':'1e9',
                         'nrays_scatter':'1e9',
                         'nrays_ir':'1e9',
                         'nrays_intensity':'1e9'}
                },
    'allrays10':{'mcrx':{ 'nrays_aux':'1e10',
                          'nrays_nonscatter':'1e10',
                          'nrays_scatter':'1e10',
                          'nrays_ir':'1e10',
                          'nrays_intensity':'1e10'}
                 },
    'null':{'mcrx':{}}}


abbreviations = {'allrays':'A', 'skipir':'I', 'aux':'X', 
                 'DL07_':'D', 'MW3.1_':'m'}


def setup_run(fits_file, info_file, args,  mcrx=None, sfrhist=None, 
              broadband=None, pbs=None, parameter_set_names=None, 
              indir=os.getcwd(), sunrise_dir=None, imp_dir=None, 
              overwrite=False, submit=False, ffov=None, dryrun=False, 
              min_age=None, max_age=None, fmass=None, fism_temp=None, 
              fmetallicity=None, random_cameras=None, skip_calzetti=False, 
              limit_cameras=None, cut_radius=None, skip_idl=False, fovcam=None, 
              short_broadband=False, moviecam=False):
    """
    Steps:
    - Read in sim_info (especially center)
    - Make the run name
    - Check to see if it already exists
    - Mkdir/Copy all files into (sunrise/ICs/inputs/outputs/plots)
    - Generate config/stub text (include generation date in comments)
    - Replace text accordingly
    - Create the PBS script
    - Create the PBS submit command
    """

    # Load info dic
    info = np.load(info_file)[()]

    # Set run_name and make run directory
    run_name = os.path.basename(fits_file.replace('.fits',''))
    for pset in parameter_set_names[::-1]:
        if pset is not None:
            run_name += '_'+pset

    other= {'ffov':ffov,'min_age':min_age,'max_age':max_age,'fmass':fmass,
            'fism_temp':fism_temp,'fmetallicity':fmetallicity,
            'cut_radius':cut_radius}
    otherl = [key+'='+str(value) for key, value in other.iteritems() if value is not None]
    args['other']=otherl

    for d in [sfrhist, mcrx, broadband, other, pbs]:
        if d is None: continue
        for k,v in d.iteritems():
            if v is None: continue
            if '/' in v:
                v=v.split('/')[-1]
            v=v.replace(',','-')
            run_name += '_%s_%s'%(str(k),str(v))

    cfgs = ['mcrx', 'broadband', 'sfrhist', 'pbs']
    for config,paramlines in [(cfg, args[cfg]) for cfg in cfgs]:
        if config == "pbs":continue #dont add pbs constants to the run name
        for line in paramlines:
            line = line.strip().replace('\n','')
            key,value = line.split(':')
            if '/' in value:
                value=value.split('/')[-1]
            value=value.replace(',','-')
            run_name += '_%s_%s'%(str(key),str(value))
    run_dir = indir+'/sunrise_runs/'+run_name

    if os.path.exists(run_dir):
        if overwrite:
            shutil.rmtree(run_dir)
            os.makedirs(run_dir)
        else:
            print 'run_dir %s already exists -- skipping'%run_dir
            return

    # Make short name
    short = make_short(info, ['mcrx','broadband','sfrhist',
        'pbs','parameter_set','other'],args)
    print '#run_name   =  %s'%run_name
    print '#short name =  %s'%short

    # Load parameterset options in sfrhist, mcrx, broadband 
    # *not* overriding if they already exist
    for pset in parameter_set_names:
        if pset in parameter_sets.keys():
            for configname, params in parameter_sets[pset].iteritems():
                #retrieve the local mcrx or sfrhist dictionary
                config = vars()[configname]
                #skip if defined already
                for k,v in params.iteritems():
                    #if k in config.keys(): continue
                    config[k]=v
        elif pset is None:
            pass
        else:
            print 'bad parameter_set chosen'
            sys.exit()

    # Load individual options
    cfgs = ['mcrx','broadband','sfrhist','pbs']
    for config,paramlines in [(cfg,args[cfg]) for cfg in cfgs]:
        for line in paramlines:
            line = line.strip().replace('\n','')
            key,value = line.split(':')
            vars()[config][key]=value

    # Make input/output/sunrise dirs
    scale = float(info['scale'])
    center = info['export_center']
    if dryrun: return
    copy_fits = min_age is not None or max_age is not None \
        or fism_temp is not None or cut_radius is not None
    make_paths(run_dir, fits_file, sunrise_dir, imp_dir,
               copy_fits=copy_fits)

    # Modify data if required
    if cut_radius is not None:
        modify_cut_radius(run_dir, cut_radius, center)
    if min_age is not None or max_age is not None:
        modify_ages(run_dir, min_age, max_age)
    if fmass is not None:
        modify_mass(run_dir, fmass)
    if fmetallicity:
        modify_metallicity(run_dir,fmetallicity)
    if fism_temp:
        modify_ism_temp(run_dir,fism_temp)
 
    # Copy cameras and export info file     
    shutil.copy(fits_file.replace('.fits', '.cameras'), run_dir+'/input/cameras' )
    shutil.copy(fits_file.replace('.fits', '.camnames'), run_dir+'/input/camnames')
    shutil.copy(fits_file.replace('.fits', '_export_info.npy'), 
                run_dir+'/input/export_info.npy')

    # Modify cameras if required
    if ffov or (random_cameras is not None) or limit_cameras:
        modify_cameras(run_dir,ffov=ffov,
                       fovcam=fovcam, moviecam=moviecam,
                       random_cameras=random_cameras,
                       limit_cameras=limit_cameras,
                       halo_id=info['halo_id'] )

    make_configs(run_dir, imp_dir, run_name, short, sfrhist, mcrx,
                 broadband, pbs, scale, center, skip_calzetti,
                 skip_idl=skip_idl, short_broadband=short_broadband)

    # Copy misc files to the sync directory
#    for misc_file in glob(fits_file.replace('.fits','*')):
#        if misc_file.endswith('fits'): continue
#        shutil.copy(misc_file,run_dir+'/sync')
#    source = fits_file.replace('.fits','plots.tar.gz')
#    fn = '%s/sync/%s'%(run_dir,os.path.basename(source))
#    if not  os.path.exists(fn):
#        try:
#            os.symlink(source,fn)
#        except:
#            print 'failed making plots symlink'
#    if int(pbs['NHOURS'])<=8:
#        qsub = 'qsub -q gpu %s/input/pre_one_step.sh'%run_dir
#    else:
#        qsub = 'qsub -q gpu_long_free %s/input/pre_one_step.sh'%run_dir
    if submit:
        print 'WARNING: Job not submitted. Automatic submittion not yet '\
            'implemented for this system'
#        os.system(qsub)
#    else:
#        print qsub


def make_short(info, cfgs, configs, level=0, break_level=1):
    assert level != break_level
    short = ''
    sim = info['sim_name']
    scale = '%1.2f'%info['scale']
    scale = 'a.'+scale[-2:]
    short += sim+'_'+scale
    for cfg in cfgs:
        for line in configs[cfg]:
            line = line.strip().replace('\n','')
            if ':' in line:
                key,value = line.split(':')
                c,k,v = abbr_function(cfg,key,value)
                if level==0:
                    if '/' in v:
                        v=v.split('/')[-1]
                    short += k.lower()+v.upper()
            else:
                for a,b in abbreviations.iteritems():
                    if a in line:
                        line = line.replace(a,b)
                line = line[0].upper()+line[1:]
                short += line
    if len(short) >15:
        try:
            short = make_short(fits_file, cfgs, configs, level=level+1)
        except:
            short = short[:15]
    #replace all spaces with underscores
    short = short.replace(' ','_')
    return short


def abbr_function(config,key,value):
    for a,b in abbreviations.iteritems():
        if a in key:
            key = key.replace(a,b)
        if a in value:
            value = value.replace(a,b)
    k = ''
    k = k.join([y[0] for y in key.split('_')])
    if value == 'false': v ='F'
    if value == 'true':  v ='T'
    try: 
        float(value)
        if 'e' in value:
            v=value.split('e')[-1]
        else:
            v = value
    except: 
        pass
        v = value
    c = config[0]
    return c,k,v


def make_paths(run_dir, fits_file, sunrise_dir, imp_dir, copy_fits=False):

    empty_dirs = [run_dir, run_dir+'/input', run_dir+'/output']#, run_dir+'/sync']
    for path in empty_dirs:
        if not os.path.exists(path):
            os.makedirs(path)
    
    target_links = [sunrise_dir]
    source_links = [run_dir+'/sunrise']

    for target, source in zip(target_links, source_links):
        if os.path.exists(source):
            os.remove(source)
        os.symlink(target, source)

    #symlink to FITS file
    if not copy_fits:
        os.symlink(fits_file, run_dir+'/input/initial.fits')
    else:
        shutil.copy(fits_file, run_dir+'/input/initial.fits')


def modify_cut_radius(run_dir, cut_radius, center):
    cut_radius = float(cut_radius)
    print 'Removing particles outside %1.1f kpc'%cut_radius
    initial = run_dir+'/input/initial.fits'
    pd,h = pyfits.getdata(initial,extname='PARTICLEDATA',header=True)
    pos = pd['position']
    rad = np.sqrt(np.sum((pos - center)**2.0,axis=1))
    idx = rad < cut_radius
    pd = pd[idx]
    pyfits.update(initial,pd,header=h,extname='PARTICLEDATA')


def modify_ages(run_dir, min_age=None, max_age=None):
    if min_age is None: min_age = -1.0
    if max_age is None: max_age = np.inf
    min_age= float(min_age)
    max_age= float(max_age)
    print 'Updating particle min ages %1.1e years'%min_age
    print 'Updating particle max ages %1.1e years'%max_age
    initial = run_dir+'/input/initial.fits'
    pd,h = pyfits.getdata(initial,extname='PARTICLEDATA',header=True)
    pd=pd[pd['age']>min_age]
    pd=pd[pd['age']<max_age]
    pyfits.update(initial,pd,header=h,extname='PARTICLEDATA')


def modify_mass(run_dir, fmassraw):
    fmassraw = np.array([float(x) for x in fmassraw.split(',')])
    age_intervals = fmassraw[::2]
    fmass = fmassraw[1::2]
    assert fmass.shape[0] == age_intervals.shape[0]-1
    initial = run_dir+'/input/initial.fits'
    pd,h = pyfits.getdata(initial,extname='PARTICLEDATA',header=True)
    pd = np.array(pd)
    for agea,ageb,fm in zip(age_intervals[:-1],age_intervals[1:],fmass):
        agea,ageb = float(agea),float(ageb)
        idx  = pd['age']>=agea
        idx &= pd['age']<=ageb
        marr = pd['mass']
        marr[idx] *= float(fm)
        pd['mass'] = marr
        out = (np.sum(idx),agea/1e6,ageb/1e6,fm)
        print 'modified %i particles %1.1eMyr-%1.1eMyr by %1.1f '%out
    pyfits.update(initial,pd,header=h,extname='PARTICLEDATA')


def modify_metallicity(run_dir, fmassraw):
    fmassraw = np.array([float(x) for x in fmassraw.split(',')])
    age_intervals = fmassraw[::2]
    fmass = fmassraw[1::2]
    assert fmass.shape[0] == age_intervals.shape[0]-1
    initial = run_dir+'/input/initial.fits'
    pd,h = pyfits.getdata(initial,extname='PARTICLEDATA',header=True)
    pd = np.array(pd)
    for agea,ageb,fm in zip(age_intervals[:-1],age_intervals[1:],fmass):
        agea,ageb = float(agea),float(ageb)
        idx  = pd['age']>=agea
        idx &= pd['age']<=ageb
        z = pd['metallicity']
        z[idx] *= float(fm)
        pd['metallicity'] = z
        out = (np.sum(idx),agea/1e6,ageb/1e6,fm)
        print 'modified %i particles %1.1eMyr-%1.1eMyr by %1.1f '%out
    pyfits.update(initial,pd,header=h,extname='PARTICLEDATA')


def modify_ism_temp(run_dir, fism_temp):
    fism_temp= np.array([float(x) for x in fism_temp.split(',')])
    temp_intervals = fism_temp[::2]
    fts = fism_temp[1::2]
    assert fts.shape[0] == temp_intervals.shape[0]-1
    initial = run_dir+'/input/initial.fits'
    gd,h = pyfits.getdata(initial,extname='GRIDDATA',header=True)
    gd = np.array(gd)
    for ta,tb,ft in zip(temp_intervals[:-1],temp_intervals[1:],fts):
        ta,tb = float(ta),float(tb)
        ism_temp = gd['gas_temp_m']/gd['mass_gas']
        idx  = ism_temp > ta
        idx &= ism_temp < tb
        ism_temp_m= gd['gas_temp_m']
        ism_temp_m[idx] *= ft
        gd['gas_temp_m'] = ism_temp_m 
        out = (np.sum(idx),ta,tb,ft)
        print 'modified %i cells %1.1fK-%1.1fK by %1.1f '%out
    pyfits.update(initial,gd,header=h,extname='GRIDDATA')


def modify_cameras(run_dir,ffov=None,fovcam=None,limit_cameras=None,
                   random_cameras=None,halo_id=None,moviecam=False):
    camera_file = run_dir+'/input/cameras'
    camdata = np.loadtxt(camera_file)
    shutil.move(camera_file, camera_file+'.old')    
    if limit_cameras:
        camdata = camdata[:int(limit_cameras)]
    fidx = Ellipsis
    if moviecam:
        #limit to two cameras
        moviecam = 3
        camdata = camdata[moviecam:moviecam+2]
        camdata[:,6:9] = 0.0
        camdata[:,6]   = 1.0 
        fidx = -1
        if ffov is None:
            ffov = 0.10
    if fovcam:
        fidx = int(fovcam)
    if ffov:
        ffov = float(ffov)
        camdata[fidx,-1]*=ffov
    if random_cameras:
        #to calculate the new cameras
        np.random.seed(int(halo_id))
        afov = camdata[0,-1]
        rad  = np.sqrt((camdata[0,0:3]**2.0).sum())
        shape = list(camdata.shape) 
        shape[0] += int(random_cameras)
        rcamdata = np.zeros(shape,'float')
        rcamdata[:camdata.shape[0],:]=camdata
        for j in range(camdata.shape[0],shape[0]):
            theta = np.random.random()*1.0*np.pi
            phi   = np.random.random()*2.0*np.pi
            x = rad*np.sin(theta)*np.cos(phi) 
            y = rad*np.sin(theta)*np.sin(phi) 
            z = rad*np.cos(theta)
            rcamdata[j,0]=x
            rcamdata[j,1]=y
            rcamdata[j,2]=z
            rcamdata[j,3]=-1.0*x
            rcamdata[j,4]=-1.0*y
            rcamdata[j,5]=-1.0*z
            rcamdata[j,6]=np.random.random()
            rcamdata[j,7]=np.random.random()
            rcamdata[j,8]=np.random.random()
            rcamdata[j,9]=afov
        camdata = rcamdata     
    np.savetxt(camera_file,camdata)    


def make_configs(run_dir, imp_dir, run_name, short, 
                 sfrhist, mcrx, broadband, pbs, scale, center,
                 skip_calzetti=False, skip_idl=False,
                 short_broadband=False):
    '''
    Generate the following configuration files:
      sfrhist.config
      broadbandz.config, broadband.config, 
      mcrx.config, mcrx_no_ir.config

    And modify runSunrise.sh if necesary

    '''
    files = glob(imp_dir+'/export/input/*config')
    files += (os.path.expandvars('$AGORA_PIPE_INSTALL/scripts/runSunrise.sh')),
#    files += ( os.path.expandvars('$AGORA_PIPE_INSTALL/scripts/runSunrise.pbs')),
    files += (imp_dir+'/export/input/filters_redshifted'),
    files += (imp_dir+'/export/input/filters_redshifted_short'),
    files += (imp_dir+'/export/input/filters_restframe'),
    files += (imp_dir+'/export/input/filters_restframe_short'),

    var_dicts = {'sfrhist':sfrhist, 'mcrx':mcrx, 
                 'broadband':broadband} #,'runSunrise':pbs}

    sfrhist['translate_origin'] = str(center).strip('[]')

    for config in files:
        config_base = os.path.basename(config)
        config_type = config_base.replace('.config','')
        if config_type.endswith('.sh'):
            config_type = config_type.replace('.sh','')
        if config_type.endswith('.pbs'):
            config_type = config_type.replace('.pbs','')
        config_dict = var_dicts.get(config_type,{})
        lines = open(config).readlines()
        text = ''
        used_keys = [] #make sure all are used!
        pad = 25
        for line in lines:
            if len(config_dict.keys())>0:
                for k,v in config_dict.iteritems():
                    if line.startswith(k) and k is not '':
                        if v is None: break
                        pad=line_padding(line)
                        newline = k.ljust(pad)+' '
                        newline+=str(v)
                        text += newline+'\n'
                        used_keys += k,
                        break
                    else:
                        text += line
            else:
                text += line

        for k,v in config_dict.iteritems():
            if k in used_keys: continue
            if k is '': continue
            if v is None: continue
            text += k.ljust(pad)+' '+str(v)+'\n'
        
        if config_type == 'runSunrise':
            fh = open(run_dir+'/'+config_base,'w')
        else:    
            fh = open(run_dir+'/input/'+config_base,'w')

        text = rep_text(text, run_dir, imp_dir, run_name, 
                        short, config_dict, (1.0/scale)-1.0,
                        skip_calzetti, short_broadband,
                        skip_idl)
        fh.write(text)
        fh.close()


def rep_text(text, run_dir, imp_dir, run_name, 
             short, rep_dict, redshift,
             skip_calzetti, short_broadband,
             skip_idl):
    '''
    Replace environment vars in .sh and .pbs files
    '''
    rep_dict.setdefault('SHORTNAME',short)
    rep_dict.setdefault('RUN_DIR',run_dir)
    rep_dict.setdefault('RUNDIR',run_dir)
    rep_dict.setdefault('IMPRESSION',imp_dir)
    rep_dict.setdefault('FULLNAME',run_name)
    rep_dict.setdefault('WCL','86300') #just short of 24 hours
    rep_dict.setdefault('PBS_NCPUS','12') 
    rep_dict.setdefault('NCPUS','12') 
    rep_dict.setdefault('PBS_NHOURS','23') 
    rep_dict.setdefault('NHOURS','24') 
    rep_dict.setdefault('UHOST','pbspl1') 
    rep_dict.setdefault('SKIPCALZETTI',skip_calzetti) 
    rep_dict.setdefault('SKIPIDL',skip_idl) 
    rep_dict.setdefault('SHORTBROADBAND',short_broadband) 
    rep_dict.setdefault('REDSHIFT',redshift) 
    if short_broadband:
        rep_dict.setdefault('FILTERSET','filters_restframe_short') 
        rep_dict.setdefault('FILTERSETZ','filters_redshifted_short') 
    else:
        rep_dict.setdefault('FILTERSET','filters_restframe') 
        rep_dict.setdefault('FILTERSETZ','filters_redshifted') 

    for k,v in rep_dict.iteritems():
        if k == '': continue
        k = k.upper()
        text=text.replace('$'+k, str(v))

    return text

        
def line_padding(line):
    #figure out what the in-place line padding is
    step =0
    for j,c in enumerate(line):
        if c is ' ' and step==0:
            step=1
        if c is not ' ' and step==1:
            break
    return j-1


if __name__ == "__main__":

    args = parse()

    print '/nStarting '+ sys.argv[0]
    print 'Parsed arguments: '
    print args
    print
    
    # Get needed parsed values to begin
    sim_dirs = args['sim_dirs']
    input_dir = args['input_dir']
    impression_dir = os.path.expandvars(args['impression_dir'])
    impression_dir = os.path.abspath(impression_dir)
    sunrise_dir = os.path.expandvars(args['sunrise_dir'])
    sunrise_dir = os.path.abspath(sunrise_dir)

    print 'Setting up Sunrise runs for ', sim_dirs

    modify_indir = 0
    if  'sim_dir' in input_dir: 
        input_dir = input_dir.replace('sim_dir','')
        modify_indir = 1
    else:
        input_dir = os.path.expandvars(input_dir)
        input_dir = os.path.abspath(input_dir)

    tolerant = args['tolerant']    

    # Loop over simulation directories    
    for sim_dir in sim_dirs:
        
        # Set paths and filenames
        sim_dir = os.path.expandvars(sim_dir)
        sim_dir = os.path.abspath(sim_dir)
        
        if modify_indir:  input_dir = sim_dir+'/'+input_dir
        if not os.path.exists(input_dir):
            print 'The provided input_dir %s does not exits'%input_dir
            print 'have you run genSunriseInput.py for this simulation?'
            print 'if yes, use the out_dir in genSunriseInput.py as input_dir here (default)'
            sys.exit()
        in_dirs = os.listdir(input_dir)

        # Loop over snapshot input directories and setup runs for each of them
        for dir in in_dirs:
            
            print '\nSetting up run for snapthot dir', dir

            # Change to this input dir and get the FITS file
            this_in_dir = input_dir+'/'+dir+'/'
            fits_file = glob(this_in_dir+'*.fits')
            if len(fits_file) > 1: 
                print 'WARNING: Multiple FITS files found in %s, using %s'%(this_in_dir, fits_file[0])
            elif len(fits_file) == 0:
                print 'WARNING: No input FITS file found in %s, skipping'%this_in_dir
                continue
            fits_file = fits_file[0]    
            info_file = fits_file.replace('.fits','_export_info.npy')
            if not os.path.exists(info_file):
                print 'WARNING: No export_info file found in %s, skipping'%this_in_dir
                continue
            mcrx, sfrhist, broadband, pbs = {},{},{},{}
         
            if tolerant:
                try:
                    setup_run(fits_file, info_file, args, mcrx, sfrhist, broadband, 
                              pbs, args['parameter_set'], this_in_dir, 
                              sunrise_dir, impression_dir, 
                              args['overwrite'], args['submit'], args['ffov'], 
                              args['dryrun'], args['min_age'], args['max_age'], 
                              args['fmass'], args['fism_temp'], args['fmetallicity'], 
                              args['random_cameras'], args['skip_calzetti'], 
                              args['limit_cameras'], args['cut_radius'], 
                              args['skip_idl'], args['fovcam'], 
                              args['short_broadband'], args['moviecam'])
                except:
                    pass
            else:
                setup_run(fits_file, info_file, args, mcrx, sfrhist, broadband, 
                          pbs, args['parameter_set'], this_in_dir, 
                          sunrise_dir, impression_dir, 
                          args['overwrite'], args['submit'], args['ffov'], 
                          args['dryrun'], args['min_age'], args['max_age'], 
                          args['fmass'], args['fism_temp'], args['fmetallicity'], 
                          args['random_cameras'], args['skip_calzetti'], 
                          args['limit_cameras'], args['cut_radius'], 
                          args['skip_idl'], args['fovcam'], 
                          args['short_broadband'], args['moviecam'])
                        
                        
