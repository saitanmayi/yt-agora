#####################################################################
#
#  UNIFIED ANALYSIS SCRIPT EXAMPLE FOR THE AGORA PROJECT
#
#  FOR SCRIPT HISTORY SEE VERSION CONTROL CHANGELOG
#
#####################################################################

import sys, os
for spec in ["~/yt/yt-3.0", "~/yt-3.0"]:
    if os.path.isdir(os.path.expanduser(spec)):
        sys.path.insert(0, os.path.expanduser(spec))
        break

if not os.path.isdir("images"): os.makedirs("images")
import h5py
from yt.config import ytcfg; ytcfg["yt","loglevel"] = "20"
from yt.mods import *
import yt.utilities.physical_constants as phys_const
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm, Normalize
from yt.data_objects.particle_filters import \
        particle_filter, filter_registry
from yt.data_objects.particle_fields import \
        particle_deposition_functions
from yt.frontends.stream.data_structures import \
        load_particles
from yt.data_objects.particle_fields import \
    particle_deposition_functions, \
    particle_vector_functions
from yt.startup_tasks import YTParser, unparsed_args

@particle_filter("finest", ["ParticleMassMsun"])
def finest(pfilter, data):
    return data["ParticleMassMsun"] < 340000

output_functions = {}
def register_output_function(func):
    output_functions[func.func_name[3:]] = func

@register_output_function
def do_art2():
    ds_art2 = load("./A11QR1/s11Qzm1h2_a1.0000.art")
    center = 128 * np.array([0.492470,  0.533444,  0.476942]) 
    ds_art2.add_particle_filter("finest")
    process_dataset(ds_art2, center)
    return ds_art2

@register_output_function
def do_enzo():
    ds_enzo = load("./DD0040/data0040")
    center = np.array([ 0.49297869, 0.50791068, 0.50727271])
    ds_enzo.add_particle_filter("finest")
    process_dataset(ds_enzo, center)

@register_output_function
def do_ramses():
    ds_ramses = load("./output_00101/info_00101.txt")
    center = np.array([ 0.48598457, 0.52665735, 0.48984628])
    #center = np.array([ 0.4861241, 0.52643877, 0.49013741])
    ds_ramses.add_particle_filter("finest")
    process_dataset(ds_ramses, center)

@register_output_function
def do_gadget():
    ds_gadget = GadgetStaticOutput("./snapshot_010", unit_base = {"mpchcm": 1.0})
    center = np.array([ 29.75540543, 32.12417221, 28.28912735])
    ds_gadget.add_particle_filter("finest")
    process_dataset(ds_gadget, center)

@register_output_function
def do_gasoline():
    cosmology_parameters = dict(current_redshift = 0.0, omega_lambda = 0.728,
                                omega_matter = 0.272, hubble_constant = 0.702)
    ds_gasoline = TipsyStaticOutput("./agora_1e11.00400",
                                    cosmology_parameters = cosmology_parameters,
                                    unit_base = {'mpchcm': 1.0/60.0})
    center = np.array([-0.014738, 0.026979, -0.010535])
    #center = np.array([-0.01477163, 0.02694199, -0.0105199])
    ds_gasoline.add_particle_filter("finest")
    process_dataset(ds_gasoline, center)

@register_output_function
def do_pkdgrav():
    cosmology_parameters = dict(current_redshift = 0.0, omega_lambda = 0.728,
                                omega_matter = 0.272, hubble_constant = 0.702)
    ds_pkdgrav = TipsyStaticOutput("./halo1e11_run1.00400", endian="<",
                                   field_dtypes = {"Coordinates": "d"},
                                   cosmology_parameters = cosmology_parameters,
                                   unit_base = {'mpchcm': 1.0/60.0})
    center = np.array([-0.01434195, 0.027505, -0.01086525])
    ds_pkdgrav.add_particle_filter("finest")
    process_dataset(ds_pkdgrav, center)

@register_output_function
def do_particles():
    f = h5py.File("./s11Qzm1h2_a1.0000.art.h5")
    data = dict((k, f[k][:].astype("float64")) for k in f)
    bbox = np.array([[0.0, 128.0], [0.0, 128.0], [0.0, 128.0]])
    data["particle_mass"] *= 2.2023338912587828e+43 # Convert to grams
    ds_particles = load_particles(data, 2.0604661199638546e+24, bbox=bbox)
    center = np.array([0.492470,  0.533444,  0.476942]) 
    center *= 128
    ds_particles.add_particle_filter("finest")
    particle_vector_functions("all",
                              ["particle_position_%s" % ax for ax in 'xyz'],
                              ["particle_velocity_%s" % ax for ax in 'xyz'],
                              StreamFieldInfo)
    particle_vector_functions("finest",
                              ["particle_position_%s" % ax for ax in 'xyz'],
                              ["particle_velocity_%s" % ax for ax in 'xyz'],
                              StreamFieldInfo)
    particle_deposition_functions("all", "Coordinates", "particle_mass", StreamFieldInfo)
    particle_deposition_functions("finest", "Coordinates", "particle_mass", StreamFieldInfo)
    process_dataset(ds_particles, center)

def process_dataset(ds, center):

    #=======================
    #  [1] TOTAL MASS
    #=======================
    sp = ds.h.sphere(center, (1.0, 'mpc'))
    total_particle_mass = sp.quantities["TotalQuantity"]( ("all","ParticleMassMsun") )[0]
    print "Total particle mass within a radius of 1 Mpc of the center: %0.3e Msun" \
          % total_particle_mass
    
    #=======================
    #  [2] PLOTS
    #=======================
    for ptype in ["finest", "all"]:
        p = ProjectionPlot(ds, "z", ("deposit", "%s_density" % ptype), center = center)
        p.save("./images/%s_z1_%s.png" % (ds, ptype))
        p.zoom(60)
        p.save("./images/%s_z2_%s.png" % (ds, ptype))

    #=======================
    #  [3] PLOTS-2
    #=======================
    w = (1.0/0.702, "mpc")
    #w = (1.0, "mpch")
    axis = 2
    colorbounds = (1e-32, 1e-25)
    res = [1024] * 3
    res[axis] = 16

    LE = center - 0.5*(w[0]/ds[w[1]])
    RE = center + 0.5*(w[0]/ds[w[1]])
    source = ds.h.arbitrary_grid(LE, RE, res)

    field = ("deposit", "all_cic")
    num = (source[field] * source[field]).sum(axis=axis)
    num *= (RE[axis] - LE[axis])*ds['cm'] # dl
    den = (source[field]).sum(axis=axis)
    den *= (RE[axis] - LE[axis])*ds['cm'] # dl
    proj = (num/den)
    proj[proj!=proj] = 1e-100 # remove NaN's
    plt.clf()
    norm = LogNorm(colorbounds[0], colorbounds[1], clip=True)
    plt.imshow(proj.swapaxes(0,1), interpolation='nearest', origin='lower',
               norm = norm, extent = [-0.5*(w[0]/ds[w[1]]), 0.5*(w[0]/ds[w[1]]), 
                                       -0.5*(w[0]/ds[w[1]]), 0.5*(w[0]/ds[w[1]])])
    cb = plt.colorbar()
    cb.set_label(r"$\mathrm{Density}\/\/[\mathrm{g}/\mathrm{cm}^3]$")
    plt.savefig("./images/%s_%s.png" % (ds, field[1]), dpi=150, bbox_inches='tight', \
                pad_inches=0.1)
    
    #=======================
    #  [4] PROFILES
    #=======================
    sphere_radius        = 300  # kpc
    inner_radius         = 0.8  # kpc
    total_bins           = 30

    sp = ds.h.sphere(center, (sphere_radius, 'kpc'))
    prof = BinnedProfile1D(sp, total_bins, "ParticleRadiuskpc", \
                           inner_radius, sphere_radius, end_collect = True)
    prof.add_fields([("all","ParticleMassMsun")],
                    weight = None, accumulation=False)
    prof["AverageDMDensity"] = prof[("all","ParticleMassMsun")] * \
                               phys_const.mass_sun_cgs / (phys_const.cm_per_kpc)**3 # g/cm^3
    shell_volume = prof["ParticleRadiuskpc"]**3.0 * (4.0/3.0)*np.pi
    shell_volume[1:] -= shell_volume[0:-1]
    prof["AverageDMDensity"] /= shell_volume

    plt.clf()
    plt.loglog(prof["ParticleRadiuskpc"], prof["AverageDMDensity"], '-k')
    plt.xlabel(r"$\mathrm{Radius}\/\/[\mathrm{kpc}]$")
    plt.ylabel(r"$\mathrm{Dark}\/\mathrm{Matter}\/\mathrm{Density}\/\/[\mathrm{g}/\mathrm{cm}^3]$")
    plt.ylim(1e-29, 1e-23)
    plt.savefig("./images/%s_radprof.png" % ds)

    fout = open("./images/%s_profile.dat" % ds, "w")
    fout.write("# sphere_radius:"+str(sphere_radius)+"\n")
    fout.write("# inner_radius:"+str(inner_radius)+"\n")
    fout.write("# \n")
    fout.write("# radius(kpc)   gas_DM_enclosed(Msun)   prof_DM_shell(g/cm^3)\n")
    fout.write("# \n")
    for k in range(0, total_bins):
        fout.write(str(prof["ParticleRadiuskpc"][k])+"   "+ 
                   str(prof[("all","ParticleMassMsun")][k])+"   "+ 
                   str(prof["AverageDMDensity"][k])+"\n")
    fout.close()

    #=======================
    #  [5] HOP HALOFINDER
    #=======================
    if os.path.exists("./images/%s_MergerHalos.out" % ds) == False:
        omega_matter = 0.272
        halos = HaloFinder(ds, threshold = omega_matter*360)
        field = ("deposit", "finest_density")
        halos.write_out("./images/%s_MergerHalos.out" % ds)
        
        source = ds.h.region(center, center - (w[0]/ds[w[1]])/2.0, center + (w[0]/ds[w[1]])/2.0)
        proj = ds.h.proj(field, "z", weight_field = field, data_source = source)
        pw = proj.to_pw(fields = [field], center = center, width = w)
        pw.set_zlim(field, 1e-31, 1e-24)
        pw.annotate_hop_circles(halos, annotate=True, print_halo_mass=False, min_size=1000)
        pw.save("./images/%s_Projection_z_%s_subset.png" % (ds, field[1]))

if __name__ == '__main__':
    parser = YTParser(description = 'AGORA analysis')
    parser.add_argument("--run-all", action="store_true", dest = "run_all")
    for output_type in sorted(output_functions):
        parser.add_argument("--run-%s" % output_type,
                dest = "outputs",
                action = "append_const",
                const = output_type,
                )
    opts = parser.parse_args(unparsed_args)
    if opts.run_all:
        outputs = output_functions.keys()
    else:
        outputs = opts.outputs
    if outputs is None:
        parser.error("No outputs supplied.")
        sys.exit()
    for output in sorted(outputs):  
        mylog.info("Examining %s", output)
        output_functions[output]()
