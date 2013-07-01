#####################################################################
#
#  AGORA SCRIPT
#  
#  PLEASE SEE:  https://hub.yt-project.org/nb/abu5nb
#
#  FOR SCRIPT HISTORY SEE VERSION CONTROL CHANGELOG
#
#####################################################################

import sys, os
for spec in ["~/yt/yt-3.0", "~/yt-3.0"]:
    if os.path.isdir(os.path.expanduser(spec)):
        sys.path.insert(0, os.path.expanduser(spec))
        break
if not os.path.isdir("figures"):
    os.makedirs("figures")
from yt.config import ytcfg; ytcfg["yt","loglevel"] = "20"
from yt.mods import *
from yt.utilities.physical_constants import kpc_per_cm
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm, Normalize

for name, method in [("CIC", "cic"), ("Density", "sum")]:
    def _func(_method):
        def finest_DM_func(field, data): # user-defined field
            filter = data["ParticleMassMsun"] <= 340000
            pos = data["all", "Coordinates"][filter, :]
            d = data.deposit(pos, [data["all", "Mass"][filter]],
                             method = _method)
            d /= data["CellVolume"]
            return d
        return finest_DM_func
    GadgetFieldInfo.add_field(("deposit", "finest_DM_%s" % name.lower()),
                              function = _func(method),
                              validators = [ValidateSpatial()],
                              display_name = "\\mathrm{Finest DM %s}" % name,
                              units = r"\mathrm{g}/\mathrm{cm}^{3}",
                              projected_units = r"\mathrm{g}/\mathrm{cm}^{2}",
                              projection_conversion = 'cm')

def particle_count(field, data):
    return np.ones(data["all","ParticleMass"].shape, dtype="float64")
GadgetFieldInfo.add_field(("all", "particle_count"), function=particle_count,
                          particle_type = True)

center = np.array([29.7555, 32.1242, 28.2893])  # Gadget unit system: [0, 60]
ds = GadgetStaticOutput("snapshot_010", unit_base = {"mpchcm": 1.0})

#=======================
#  [1] TOTAL MASS
#=======================

sp = ds.h.sphere(center, (1.0, 'mpc'))
total_particle_mass = sp.quantities["TotalQuantity"]( ("all","ParticleMassMsun") )[0]
print "Total particle mass within a radius of 1 Mpc of the center: %0.3e Msun" % total_particle_mass

#=======================
#  [2] BASIC PLOTS
#=======================

w = (1.0, "mpch")
axis = 2
colorbounds = (1e-32, 1e-25)

res = [1024] * 3
res[axis] = 16

LE = center - 0.5*(w[0]/ds[w[1]])
RE = center + 0.5*(w[0]/ds[w[1]])

source = ds.h.arbitrary_grid(LE, RE, res)

fields = [("deposit", "all_cic"), ("deposit", "finest_DM_cic")]

for field in fields:
    # Weighted Projection: Manually do this until we have a solution in place 
    # to do it from arbitrary_grid objects.
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
    plt.xlabel(r"$%d\/ \mathrm{Mpc} / h \/(\mathrm{comoving})$" % round(ds.units["mpch"]))
    plt.ylabel(r"$%d\/ \mathrm{Mpc} / h \/(\mathrm{comoving})$" % round(ds.units["mpch"]))
    cb = plt.colorbar()
    cb.set_label(r"$\mathrm{Density}\/\/[\mathrm{g}/\mathrm{cm}^3]$")
    plt.savefig("figures/%s_%s.png" % (ds, field[1]), dpi=150, bbox_inches='tight', pad_inches=0.1)

#=======================
#  [3] BASIC PROFILE
#=======================

sphere_radius        = 200  # kpc
inner_radius         = 0.3  # kpc
total_bins           = 30

sp = ds.h.sphere(center, (sphere_radius, 'kpc'))
prof = BinnedProfile1D(sp, total_bins, "ParticleRadiuskpc",
                       inner_radius, sphere_radius,
                       end_collect = True)
prof.add_fields([("all","ParticleMassMsun")],
                weight = None, accumulation=False)
prof.add_fields([("all", "particle_count")],
                weight = None, accumulation=True)
prof["AverageDMDensity"] = prof[("all","ParticleMassMsun")] * 6.77e-32
for k in range(0, len(prof["AverageDMDensity"])):
    if k == 0:
        prof["AverageDMDensity"][k] /= ((4.0/3.0) * np.pi * prof["ParticleRadiuskpc"][k]**3)  # g/cm^3
    else:
        prof["AverageDMDensity"][k] /= ((4.0/3.0) * np.pi * 
                                        (prof["ParticleRadiuskpc"][k]**3-prof["ParticleRadiuskpc"][k-1]**3))

plt.clf()
plt.loglog(prof["ParticleRadiuskpc"], prof["AverageDMDensity"], '-k')
plt.xlabel(r"$\mathrm{Radius}\/\/[\mathrm{kpc}]$")
plt.ylabel(r"$\mathrm{Dark}\/\mathrm{Matter}\/\mathrm{Density}\/\/[\mathrm{g}/\mathrm{cm}^3]$")
plt.ylim(1e-29, 1e-23)
plt.savefig("figures/%s_radprof.png" % ds)

plt.clf()
plt.loglog(prof["ParticleRadiuskpc"], prof["all", "particle_count"], '-k')
plt.xlabel(r"$\mathrm{Radius}\/\/[\mathrm{kpc}]$")
plt.ylabel(r"$\mathrm{N}$")
plt.ylim(1, 1e6)
plt.savefig("figures/%s_pcount.png" % ds)

#=======================
#  [4] HOP HALOFINDER
#=======================

# halos = HaloFinder(ds, subvolume = source, threshold=80.)
# print halos[0].center_of_mass() 
# print halos[0].total_mass()
# halos.dump("./%s_MergerHalos" % ds)
# pw = ProjectionPlot(ds, "z", ("deposit", "all_density"), weight_field=None, center=center, width=(1.0,'mpch'))
# pw.annotate_hop_circles(halos)
# pw.save()
