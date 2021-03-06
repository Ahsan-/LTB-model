from __future__ import division
import numpy as np
from LTB_Sclass_v2 import LTB_ScaleFactor, sample_radial_coord
from LTB_MyWay import LTB_geodesics
from LTB_housekeeping import *

from scipy.interpolate import UnivariateSpline as spline_1d
from scipy.interpolate import RectBivariateSpline as spline_2d
from matplotlib import pylab as plt
from mpl_toolkits.mplot3d import Axes3D

from joblib import Parallel, delayed
from joblib.pool import has_shareable_memory
import multiprocessing as mp
import healpy as hp

c = 299792458. #ms^-1
Mpc = 1.
Gpc = 1e3*Mpc
H_in = 0.73 #0.5-0.85 units km s^-1 Mpc^-1
Hoverc_in = H_in*1e5/c #units of Mpc^-1
H_out = 0.673 #0.7 #0.3-0.7 units km s^-1 Mpc^-1
Hoverc_out = H_out*1e5/c #units of Mpc^-1
H_not = 0.673 #0.7 #0.5-0.95 units km s^-1 Mpc^-1
Hoverc_not = H_not*1e5/c #units of Mpc^-1
#if Lambda is nonzero check equations for correct units. [Lambda]=[R]^-2

Omega_R0 = 4.1834e-5/H_out**2
OmegaM_out = 0.315
Omega_Lambda = (1. - OmegaM_out - Omega_R0)*0.999 
Lambda = Omega_Lambda * 3. * Hoverc_not**2

r0 = 53./H_out #3.*Gpc  #2.5*Gpc #3.5 #0.33 #0.3-4.5 units Gpc
delta_r = 15./H_out #2.5 #0.2*r0 #5. #0.2*r0 # 0.1r0-0.9r0

###################
#wiltshire notation
# r0 = R = 20 to 60  (h^{-1] Mpc)
delta_w = -0.96 #-0.95 #-0.95 to -1
#delta_r =  w = 2.5  , 5.,  10.,  15.
# add subscript w to all quantities wiltshire
###################
print "Omega_Lambda", Omega_Lambda, "Lambda ", Lambda
print "OmegaM_out ", OmegaM_out, "H0 ", H_out


def dLTBw_M_dr(r):
	"""
	[LTB_M] = Mpc
	"""
	return_me = 0.75*OmegaM_out*Hoverc_out**2*r**2 * (2.+delta_w - delta_w* 
	                                                 np.tanh((r-r0)/delta_r))
	return return_me

#fist make a spline and use it to calcuate the integral than make a second spline
# so that it is computationally less expensive

#generously sample M(r) as it is not expensive
#rw = np.concatenate((np.logspace(np.log10(1e-10),np.log10(1.),num=500,endpoint=False),
#                       np.linspace(1.,r0+4.*delta_r,num=500,endpoint=False)))

#rw = np.concatenate((rw,np.linspace(r0+4.*delta_r,20.*Gpc,num=300,endpoint=True)))

rw = sample_radial_coord(r0=r0,delta_r=delta_r,r_init=1e-10,r_max=20*1e3,num_pt1=1000,num_pt2=1000)

r_vector = sample_radial_coord(r0=r0,delta_r=delta_r,r_init=1e-4,r_max=20*1e3,num_pt1=100,num_pt2=100)
size_r_vector = 200

spdLTBw_M_dr = spline_1d(rw, dLTBw_M_dr(rw), s=0) #dLTBw_M_dr(rw), s=0)
spdLTBw_M_dr_int = spdLTBw_M_dr.antiderivative()
Mw = spdLTBw_M_dr_int(rw) #- spdLTBw_M_dr_int(rw[0])
model_age = 13.819*ageMpc
spMw = spline_1d(rw,Mw,s=0)

def LTBw_M(r):
	"""
	[LTB_M] = Mpc
	"""
	return spMw(r)




@Integrate
def LTB_t(RoverR0,twoE,twoM,Lambda_over3):
	#return 1./np.sqrt(twoE + twoM/RoverR0 + Lambda_over3 * RoverR0**2)
	return np.sqrt(RoverR0)/np.sqrt(twoE*RoverR0 + twoM + Lambda_over3 * RoverR0**3)

LTB_t.set_options(epsabs=1.49e-16,epsrel=1.49e-12)
LTB_t.set_limits(0.,1.)
@Findroot
def LTB_2E_Eq(twoE_over_r3,twoM_over_r3,Lambda_over3):
	return model_age - LTB_t.integral(twoE_over_r3,twoM_over_r3,Lambda_over3) #*1.e-3

 

LTB_2E_Eq.set_options(xtol=4.4408920985006262e-16,rtol=4.4408920985006262e-15)
LTB_2E_Eq.set_bounds(0.,1e-6)#(0.,1e-6) #(0,2.)

E = np.zeros(len(r_vector))
#serial loop
#i = 0
#for r in r_vector:
#	E[i] = LTB_2E_Eq.root(2.*LTB_M(r)/r**3,0.)
#	i = i + 1

def E_loop(r,Lambda_over3):
	return LTB_2E_Eq.root(2.*LTBw_M(r)/r**3,Lambda_over3)


num_cores = mp.cpu_count()-1

E_vec = Parallel(n_jobs=num_cores,verbose=0)(delayed(E_loop)(r,Lambda/3.) for r in r_vector)
E_vec = np.asarray(E_vec)/2.

i = 0
for r in r_vector:
	print E_vec[i],  r
	i = i + 1


E_vec = E_vec

spLTBw_E = spline_1d(r_vector, E_vec, s=0) 
dE_vec_dr = spLTBw_E(r_vector,nu=1) #compute the first derivative
spdLTBw_E_dr = spline_1d(r_vector,dE_vec_dr,s=0)

def LTBw_E(r):
	"""
	returns the spline for r^2 * E(r) as E was E/r^2
	"""
	return r**2*spLTBw_E(r)

def dLTBw_E_dr(r):
	"""
	Returns the spline for diff(E(r),r)
	"""
	return 2*r*spLTBw_E(r) + r**2*spdLTBw_E_dr(r)



model =  LTB_ScaleFactor(Lambda=Lambda,LTB_E=LTBw_E, LTB_Edash=dLTBw_E_dr,\
                              LTB_M=LTBw_M, LTB_Mdash=dLTBw_M_dr)

num_pt = 1000 #6000
r_vec, t_vec, R_vec, Rdot_vec, Rdash_vec, Rdotdot_vec, Rdashdot_vec, = \
              [np.zeros((size_r_vector,num_pt)) for i in xrange(7)]

#serial 
#for i, r_loc in zip(range(len(r_vector)),r_vector):
#	print r_loc
#	t_vec[i,:], R_vec[i,:], Rdot_vec[i,:], Rdash_vec[i,:], Rdotdot_vec[i,:], \
#	Rdashdot_vec[i,:] = LTB_model0(r_loc=r_loc,num_pt=num_pt)
#	r_vec[i,:] = r_vec[i,:] + r_loc

def r_loop(r_loc):
	return model(r_loc=r_loc,t_max=model_age,num_pt=num_pt)


num_cores = mp.cpu_count()-1	
r = Parallel(n_jobs=num_cores,verbose=0)(delayed(r_loop)(r_loc) for r_loc in r_vector)
#r = Parallel(n_jobs=num_cores,verbose=0)(delayed(LTB_model0)(r_loc=r_loc,num_pt=num_pt) for r_loc in r_vector)

i = 0
for tup in r:
	t_vec[i,:], R_vec[i,:], Rdot_vec[i,:], Rdash_vec[i,:], Rdotdot_vec[i,:], \
	Rdashdot_vec[i,:] = tup
	i = i + 1

t_vector = t_vec[0,:]
sp = spline_2d(r_vector,t_vector,R_vec,s=0)
spdr = spline_2d(r_vector,t_vector,Rdash_vec,s=0)
spR = spline_2d(r_vector,t_vector,R_vec,s=0)
spRdot = spline_2d(r_vector,t_vector,Rdot_vec,s=0)
spRdash = spline_2d(r_vector,t_vector,Rdash_vec,s=0)
spRdashdot = spline_2d(r_vector,t_vector,Rdashdot_vec,s=0)

print "checking that age is the same "
for r_val in r_vector:
	print "model age = ", model_age/ageMpc, "sp(r,age) ", sp.ev(r_val,model_age), "r ", r_val
	print "H(r,t0) in km /s/Mpc ", spRdot.ev(r_val,model_age)/spR.ev(r_val,model_age)*c/1e5, spRdash.ev(r_val,model_age)
	print "R/R_r-3M/M_r ", r_val-3.*LTBw_M(r_val)/dLTBw_M_dr(r_val) 

###############################################################################
#******************************************************************************
model_geodesics = LTB_geodesics(E=LTBw_E, E_r=dLTBw_E_dr, R=spR,R_r=spRdash,
                                R_rt=spRdashdot,R_t=spRdot,num_pt=1700)

#num_angles = 100 #20. #200 #200
#angles = np.linspace(0.,0.995*np.pi,num=num_angles,endpoint=True)
#angles = np.concatenate( (np.linspace(0.,0.995*np.pi,num=int(num_angles/2),endpoint=True), 
#                        np.linspace(1.01*np.pi,2.*np.pi,num=int(num_angles/2),endpoint=False)))
num_angles = hp.nside2npix(nside=2)
#theta,phi = hp.pix2ang(nside=2,ipix=np.arange(num_angles))
#theta = np.unique(theta)
#theta = np.concatenate(([0.],theta))
#theta = np.concatenate((theta,[np.pi]))
#phi = np.unique(phi)
#theta = np.array([0.,0.41113786, 29.3*np.pi/180., 0.84106867,  1.23095942,
#                 1.57079633,  1.91063324,2.30052398,  2.73045479,np.pi])
#phi = np.array([ 0.        ,  0.39269908,  0.78539816,  1.17809725,  1.57079633,
#        1.96349541,  2.35619449,  2.74889357,  3.14159265,  3.53429174,\
#        3.92699082,  4.3196899 ,  4.71238898,276.4*np.pi/180.,  5.10508806,\
#        5.49778714, 5.89048623])
theta = np.linspace(0.,2*np.pi,12)
phi = np.linspace(0.,2*np.pi,13)
angles = [(a,b) for a in theta for b in phi]
num_angles = np.size(angles)/2
num_z_points = model_geodesics.num_pt
geo_z_vec = model_geodesics.z_vec 
#geo_s_vec = model_geodesics.s_vec

#geo_affine_vec, geo_t_vec, geo_r_vec, geo_p_vec, geo_theta_vec = \
#                        [np.zeros((num_angles,num_z_points)) for i in xrange(5)] 

ans = [np.zeros((num_angles,num_z_points)) for i in xrange(8)]
loc = 27.9/H_out#27./H_out#30/H_out#40/H_out #20

#First for an on center observer calculate the time when redshift is 1100.
ans_central = model_geodesics(
              [model_age,r_vector[0]+loc*0., np.pi/2.+0.*(90.+29.3)*np.pi/180.,276.4*np.pi/180.],
              (np.pi/2.,276.4*np.pi/180.))#(29.3*np.pi/180.,276.4*np.pi/180.)) (np.pi/2.+29.3*np.pi/180.,276.4*np.pi/180.)
              
sp_center_t = spline_1d(geo_z_vec,ans_central[0][:],s=0)
print "age at t(z=1100) for central observer is ", sp_center_t(1100.), sp_center_t(1100.)/ageMpc*1e4
print "t ", ans_central[0][:]
print "r ", ans_central[1][:]
print "theta ", ans_central[2][:]
print "phi ", ans_central[3][:]
print "ang dist ", ans_central[7][:]
#t = ans_central[0][:]
#r = np.abs(ans_central[1][:])
#theta = ans_central[2][:]
#phi = ans_central[3][:]
#dr = ans_central[4][:]
#dtheta = ans_central[5][:]
#dphi = ans_central[6][:]
#print "normalization ", (\
#                        spRdash.ev(r,t)**2/(1.+2.*dLTBw_E_dr(r))*dr**2 + \
#                        spR.ev(r,t)**2*(dtheta**2 + np.sin(theta)**2*dphi**2))/\
#                        (-(1+geo_z_vec)**2)
#print "r[0], r[-1]", r_vector[0], r_vector[-1]
#dphi_dz_sp = spline_1d(geo_z_vec,dphi,s=0)
#t_sp = spline_1d(geo_z_vec,t,s=0)
#print "estimate dphi_ds", dphi_dz_sp(0.)/(1.+0.)*t_sp(0.,nu=1), dphi_dz_sp(0.),t_sp(0.,nu=1)
#print "dphi_dz ", (phi[1]-phi[0])/(geo_z_vec[1]-geo_z_vec[0])
#print "phi(0+delta_z) ",  dphi_dz_sp(0.)/(1.+0.)*t_sp(0.,nu=1)*(geo_z_vec[1]-geo_z_vec[0])+phi[0], phi[1]
#from matplotlib import pylab as plt
#plt.figure()
#plt.plot(geo_z_vec,ans_central[1][:])
#plt.figure()
#plt.plot(geo_z_vec,ans_central[1][:])
#plt.xscale('log')
#plt.show()

#import sys
#sys.exit()
#serial version
#for i, angle in zip(xrange(num_angles),angles):
#	geo_affine_vec[i,:], geo_t_vec[i,:], geo_r_vec[i,:], geo_p_vec[i,:], \
#	geo_theta_vec[i,:] = LTB_geodesics_model0(rp=loc,tp=model_age,alpha=angle)

#parallel version 2
def geo_loop(angle):
	return model_geodesics(
	       [model_age,loc, np.pi/2.+0.*(90.+29.3)*np.pi/180.,276.4*np.pi/180.],
           angle)

num_cores=7
geos = Parallel(n_jobs=num_cores,verbose=5)(
delayed(geo_loop)(angle=angle) for angle in angles)
print "type and shape", type(geos)
print "as tuple", np.shape(geos)
geos = np.asarray(geos)
print "asarray", np.shape(geos)
geo_t, geo_r, geo_theta, geo_phi, geo_drds, geo_dthetads, geo_dphids, geo_DA = \
[geos[:,i,:] for i in np.arange(8)]

z_dec, t_z1100, DA_dec = [np.empty(num_angles) for i in np.arange(3)]
for i in np.arange(num_angles):
	sp_z = spline_1d(-geo_t[i,:],geo_z_vec,s=0)
	z_dec[i] = sp_z(-sp_center_t(1100.))
	print "z_dec[i] ", z_dec[i]
	sp_t = spline_1d(geo_z_vec,geo_t[i,:],s=0)
	t_z1100[i] = sp_t(1100.)
	print "t_z1100[i] ", t_z1100[i]
	sp_DA = spline_1d(geo_z_vec,geo_DA[i,:],s=0)
	DA_dec[i] = sp_DA(z_dec[i])
	print "DA_dec[i]", DA_dec[i]

sp_z_dec = spline_2d(theta,phi,np.reshape(z_dec,(theta.size,phi.size)),s=0)
print "max min z_dec", z_dec.max(), z_dec.min()
print "reshaped z_dec", np.reshape(z_dec,(theta.size,phi.size))
#plt.figure()
#hp.mollview(np.array(
#                     [sp_z_dec(a,b) for a,b in \
#                     hp.pix2ang(np.arange(z_dec.size))]
#                     ))
#plt.figure()
a, b = hp.pix2ang(32,np.arange(hp.nside2npix(32)))
zdec_map = np.array([sp_z_dec.ev(i,j) for i,j in zip(a,b)])
zdec_map = (zdec_map.mean()-zdec_map)/(1.+zdec_map)*2.7255
proj_map = hp.mollview(zdec_map,coord='G')
hp.mollview(map = zdec_map, title = "Simulated dipole" ,
remove_mono=True,format='%.4e',coord='G')
hp.mollview(map = zdec_map, title = "Simulated quadrupole" ,
remove_dip=True,format='%.4e',coord='G')
plt.show()
#for i,j in zip(a,b):
#	print sp_z_dec.ev(i,j)
import sys
sys.exit()
plt.show()
model_geodesics.reset_z_vec()
print "rest z_vec"
#v = cz (km/sec)   d (/h Mpc)  v_pec (km/s)   sigma_v   l (degrees) b (degrees)
comp_cz, comp_d, comp_vpec, comp_sigv, comp_ell_deg, comp_bee_deg = \
np.loadtxt("COMPOSITEn-survey-dsrt.dat",unpack=True)

comp_ell = comp_ell_deg*np.pi/180. 
comp_bee = (90.-comp_bee_deg)*np.pi/180.
comp_angle = zip(comp_bee,comp_ell)
wiltshire_model = open("MyWay.dat",'w')
wiltshire_model.write("#cz [km/s]     dist [Mpc]   ell  bee \n")
for i, angle in zip(np.arange(comp_d.size),comp_angle):
	ans = model_geodesics( [model_age,loc, 29.3*np.pi/180.,276.4*np.pi/180.],
                           angle)
	#sp_z = spline_1d(ans[:][-1],model_geodesics.z_vec,s=0)
	#redshift = sp_z(comp_d[i]*H_out)
	redshift = 0.
	wiltshire_model.write("%15.6f   %10.6f    %6.2f %6.2f \n" %(redshift*c/1e3, comp_d[i], 
	                   comp_ell_deg[i], comp_bee_deg[i]))
import sys
sys.exit()
i = 0
for geo_tuple in geos:
	geo_t_vec[i,:], geo_r_vec[i,:], geo_theta_vec[i,:], geo_phi_vec[i,:] ,\
	geo_theta_vec[i,:] = geo_tuple
	i = i + 1

#finally make the 2d splines
sp_z_dec = spline_2d(angles,geo_z_vec,geo_affine_vec,s=0) 
sp_t_dec = spline_2d(angles,geo_z_vec,geo_t_vec,s=0)
sp_DA_dec = spline_2d(angles,geo_z_vec,geo_r_vec,s=0)


ras, dec = np.loadtxt("pixel_center_galactic_coord_12288.dat",unpack=True)
#Rascension, declination, gammas = get_angles(ras, dec)
from GP_profiles import get_GP_angles
## NOTE: 
# Set ell_d=0 and bee_d = 90 to get theta=0, phi=0
# in get_GP_angles(ell=ras, bee=dec,ell_d = 51.7, bee_d = -24.9)
## and the manual spherical harmonic decomposition agrees with Healpix 
## because the change of coordinates is along the z-axis and gamma=xi=theta
#Rascension, declination, gammas = get_GP_angles(ell=ras,bee=dec,ell_d = 96.4, bee_d = -29.3)
Rascension, declination, gammas = get_GP_angles(ell=ras,bee=dec,ell_d = 276.4, bee_d = 29.3)
#cmb dipole direction
#Rascension, declination, gammas = get_GP_angles(ell=ras,bee=dec,ell_d = 263.99, bee_d = 48.26)
#Rascension, declination, gammas = get_GP_angles(ell=ras,bee=dec,ell_d = 0., bee_d = np.pi/2.)
z_of_gamma = np.empty_like(gammas)
z_star = 1100.
#age_central = sp_center_t(z_star)
age_central = sp_t_vec.ev(0.,z_star)
@Findroot
def z_at_tdec(z,gamma):
	return sp_t_vec.ev(gamma,z)/age_central - 1.

z_at_tdec.set_options(xtol=1e-8,rtol=1e-8)
z_at_tdec.set_bounds(z_star-20.,z_star+20.) 
#Because Job lib can not pickle z_at_tdec.root directly
def z_at_tdec_root(gamma):
	return z_at_tdec.root(gamma)

z_of_angles = Parallel(n_jobs=num_cores,verbose=0)(delayed(z_at_tdec_root)(gamma) for gamma in angles)
z_of_angles = np.asarray(z_of_angles)

z_of_angles_sp = spline_1d(angles,z_of_angles,s=0)
z_of_gamma = z_of_angles_sp(gammas) 
#z_of_gamma = 1100. - (age_central-sp_t_vec.ev(gammas,1100.))/sp_t_vec.ev(gammas,1100.,dy=1)
np.savetxt("zw_of_gamma_1000.dat",z_of_gamma)
#my_map = (z_of_gamma.mean() - z_of_gamma)/(1.+z_of_gamma)
import healpy as hp
#############
@Integrate
def get_bar_z(gamma,robs):
	return np.sin(gamma)/(1.+z_of_angles_sp(gamma))
get_bar_z.set_options(epsabs=1.49e-16,epsrel=1.49e-12)
get_bar_z.set_limits(0.,np.pi)
#my_map = (hp.pixelfunc.fit_monopole(z_of_gamma) - z_of_gamma)/(1.+z_of_gamma)
my_map = 2.7255*( (2./get_bar_z.integral(loc)-1.) - z_of_gamma)/(1.+z_of_gamma)
#############
#using spherical harmonics decomposition
############
z_mean = 2./get_bar_z.integral(loc) - 1.
def Delta_T(xi):
	"""
	0<= xi <= pi 
	"""
	return 2.7255*(z_mean - z_of_angles_sp(xi))/(1.+z_of_angles_sp(xi))

from scipy.special import legendre as legendre

@Integrate
def al0(xi,ell):
	"""
	For m=0
	Ylm = 1/2 sqrt((2l+1)/pi) LegendreP(l,x)
	xi: angle in radians
	Note: The integral over the other angle gives a factor of 2pi
	While healpix does the spherical harmonic decomposition w.r.t spherical 
	polar coordinates (theta,phi), this manual decomposition is w.r.t the 
	angle (xi,phi) and xi is not theta.
	"""
	LegPol = legendre(ell)
	return 2.*np.pi*Delta_T(xi)*np.sqrt((2.*ell+1.)/(4.*np.pi))*LegPol(np.cos(xi))*np.sin(xi)

al0.set_options(epsabs=1.49e-14,epsrel=1.49e-12)
al0.set_limits(0.,np.pi)
print "\n One has to be careful as to how the spherical harmonics are normalized"
print "There are atleast three different ways adopted in literature"
print " now manually calculating alms , divided 4pi/(2l+1)"
print "alm , l=0, m=0", al0.integral(0), al0.integral(0)/ np.sqrt(4*np.pi/1) 
print "alm , l=1, m=0", al0.integral(1), al0.integral(1)/ np.sqrt(4*np.pi/3)
print "alm , l=2, m=0", al0.integral(2), al0.integral(2)/ np.sqrt(4*np.pi/5)

flip = 'geo' #'astro' # 'geo'
hp.mollview(map = my_map, title = "temp_map" ,
flip = flip,format='%.4e')
hp.mollview(map = my_map, title = "simulated dipole" ,
flip = flip, remove_mono=True,format='%.4e')
hp.mollview(map = my_map, title = "Simulated quadrupole" ,
flip = flip, remove_dip=True,format='%.4e')
plt.show()

#my_map = hp.remove_monopole(my_map)
#cls,alm = hp.sphtfunc.anafast(my_map,mmax=10,lmax=10,pol=False,alm=True)
cls,alm = hp.sphtfunc.anafast(my_map,pol=False,alm=True)
print "checking with C_l = abs(al0)^2/(2l+1)"
print 'alm ', alm
print 'cls ', cls
cls,alm = hp.sphtfunc.anafast(my_map,pol=False,alm=True,lmax=10,mmax=0)
print "once again"
print 'alm ', alm
print 'cls ', cls
print "using map2alm"
alm = hp.sphtfunc.map2alm(my_map,lmax=10,mmax=0,pol=False,use_weights=True)
print alm
import sys
sys.exit()

#fig = plt.figure()
#plt.plot(rw, dLTBw_M_dr(rw),label="dM_dr")
##plt.xscale('log')
##plt.yscale('symlog')
#plt.legend(loc='best')
#fig = plt.figure()
##plt.plot(rw,LTBw_M(rw)/LTB_M(rw),label="M(r)")
#plt.plot(rw,LTBw_M(rw),label="M(r)")
#plt.legend(loc='best')
#plt.yscale('log')
#plt.xscale('log')
#fig = plt.figure()
#plt.plot(rw,dLTBw_M_dr(rw)*2/rw**2,label="rho(r)")
#plt.xscale('log')
#plt.legend(loc='best')
#plt.show()
#
#
#print "all done"
#fig = plt.figure()
#plt.plot(r_vector,E_vec,'g-')
#fig = plt.figure()
#plt.plot(r_vector,E_vec*r_vector**2,'r-')
#plt.show()
#
#fig = plt.figure()
##plt.plot(r_vector,dLTBw_E_dr(r_vector))
#plt.plot(rw,dLTBw_E_dr(rw))
#plt.show()
