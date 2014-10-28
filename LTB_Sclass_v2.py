#!/usr/bin/env python2.7
from __future__ import division
import numpy as np
from scipy.integrate import ode
from LTB_series import t_series, d_t_series_dR, d_t_series_dE, d_t_series_dM

class LTB_ScaleFactor():
	"""
	A class for solving Eq. (2.2) in ``Structures in the Universe by Exact Method``
	by Krzystof Bolejko etal. The user provides E(r), M(r), diff(E(r),r) and diff(M(r),r).
	Once solved they can be used in the geodesic equations for both the LTB and 
	Szekeres models.
	
	args:
	     Optional extra positional arguments for E(r), M(r), diff(E(r),r), diff(M(r),r)
	kwargs:
	     Optional extra positional arguments for E(r), M(r), diff(E(r),r), diff(M(r),r)
	"""
	def __init__(self, Lambda,LTB_E, LTB_Edash, LTB_M, LTB_Mdash, *args, **kwargs):
		self.Lambda    = Lambda
		self.LTB_E     = LTB_E
		self.LTB_Edash = LTB_Edash
		self.LTB_M     = LTB_M
		self.LTB_Mdash = LTB_Mdash
		self.args      = args
		self.kwargs    = kwargs
		# i stands for integer index
		self.i_R = 0; self.i_Rdot = 1; self.i_Rdash = 2
	
	def get_E(self, r):
		"""
		E(r) in Eq. (2.1) of ``Structures in the Universe by Exact Methods``
		2E(r) \equiv -k(r) in http://arxiv.org/abs/0802.1523
		"""
		return self.LTB_E(r, *self.args, **self.kwargs)
	
	def get_dEdr(self, r):
		"""
		E(r) in Eq. (2.1) of ``Structures in the Universe by Exact Methods``
		2E(r) \equiv -k(r) in http://arxiv.org/abs/0802.1523
		Returns diff(E(r),r)
		"""
		return self.LTB_Edash(r, *self.args, **self.kwargs)
	
	def get_M(self,r):
		"""
		M(r) in Eq. (2.2) of ``Structures in the Universe by Exact Methods``
		2M(r) \equiv F(r) in http://arxiv.org/abs/0802.1523
		"""
		return self.LTB_M(r, *self.args, **self.kwargs)

	def get_dMdr(self,r):
		"""
		M(r) in Eq. (2.2) of ``Structures in the Universe by Exact Methods``
		2M(r) \equiv F(r) in http://arxiv.org/abs/0802.1523
		Returns diff(M(r),r)
		"""
		return self.LTB_Mdash(r, *self.args, **self.kwargs)
	
	def LTB_ScaleFactor_derivs(self,t,y,E,dEdr,M,dMdr,Lambda):
		"""
		Returns the partial derivatives, diff(R(t,r),t) , diff(R(t,r),t,t) and
		diff(R(t,r),r,t) for the scale factor in LTB model as given in Eq. (2.1) 
		of ``Structures in the Universe by Exact Methods``
		"""
		dy_dt = np.empty_like(y) #np.zeros(3)
		dy_dt[self.i_R] = np.sqrt(2.*E + 2.*M/y[self.i_R] + Lambda/3.*y[self.i_R]**2)
		
		dy_dt[self.i_Rdot] = -M/y[self.i_R]**2 + Lambda/3.*y[self.i_R]
		
		dy_dt[self.i_Rdash] = 1./(dy_dt[self.i_R])* (dEdr + dMdr/y[self.i_R] + \
		                          dy_dt[self.i_Rdot]*y[self.i_Rdash])
		                          
		return dy_dt
	
	def LTB_ScaleFactor_Jac(self,t,y,E,dEdr,M,dMdr,Lambda):
		raise NotImplementedError('Yo king! Look at LTB_ScaleFactor_derivs and supply the Jacobian, peace.')

	
	def __call__(self,r_loc,R_init=1e-10,num_pt=20000,atol=1e-12,rtol=1e-10):
		"""
		At a given comoving radial coordinate r=r_loc evolve  diff(R(t,r),t) , 
		diff(R(t,r),t,t) and diff(R(t,r),r,t) starting from a time t_init when 
		R(t=t_init,r=r_loc) = R_init and stopping when R(t=t0,r=r_loc)=r_loc with 
		t0 denoting the age of the universe today. 
		r_loc:
		      is the fixed comoving radial coordinate r=r_loc 
		R_init:
		       is R(t=t_init,r=r_loc)
		t_init:
		       the initial time when integration is started. The series solution 
		       is used to find t_init, when R=R_init
		num_pt:
		       number of time steps between time t_init and t0 (age of universe today)
		atol, rtol:
		       are absolute and relative error tolerances for the ode solver
		t_vec:
		     vector of size num_pt containing time values t
		R_vec:
		      vector of size num_pt containing R(t,r=r_loc)
		Rdot_vec:
		      vector of size num_pt containing diff(R(t,r=r_loc),t)
		Rdash_vec:
		      vector of size num_pt containing diff(R(t,r=r_loc),r)
		Rdotdot_vec:
		      vector of size num_pt containing diff(R(t,r=r_loc),t,t)
		Rdashdot_vec:
		      vector of size num_pt containing diff(R(t,r=r_loc),r,t)
		
		Returns t_vec, R_vec, Rdot_vec, Rdotdot_vec, Rdashdot_vec
		"""
		i_R     = self.i_R
		i_Rdot  = self.i_Rdot
		i_Rdash = self.i_Rdash
		
		R_vec        = np.empty(num_pt)
		Rdot_vec     = np.empty(num_pt)
		Rdash_vec    = np.empty(num_pt)
		Rdotdot_vec  = np.empty(num_pt)
		Rdashdot_vec = np.empty(num_pt)
		
		Lambda = self.Lambda
		E    = self.get_E(r_loc)
		dEdr = self.get_dEdr(r_loc)
		M    = self.get_M(r_loc)
		dMdr = self.get_dMdr(r_loc)
		
		t_init = t_series(R=R_init,E=E,M=M,Lambda=Lambda)
		print 't_init = ', t_init
		y_init = np.zeros(3)
		y_init[i_R] = R_init
		y_init[i_Rdot] = 1./d_t_series_dR(R=R_init,E=E,M=M,Lambda=Lambda)
		y_init[i_Rdash] = -(d_t_series_dE(R=R_init,E=E,M=M,Lambda=Lambda)*dEdr +
                d_t_series_dM(R=R_init,E=E,M=M,Lambda=Lambda)*dMdr)/ \
                d_t_series_dR(R=R_init,E=E,M=M,Lambda=Lambda)
		print "at t_init, y is ", y_init
		R_vec[0] = y_init[i_R]; Rdot_vec[0] = y_init[i_Rdot]; Rdash_vec[0] = y_init[i_Rdash]
		crap, Rdotdot_vec[0], Rdashdot_vec[0] = self.LTB_ScaleFactor_derivs(t_init,y_init,E,dEdr,M,dMdr,Lambda)
		#print "at t_init, y is ", Y_init
		
		evolve_LTB = ode(self.LTB_ScaleFactor_derivs).set_integrator('vode', method='adams', with_jacobian=False,atol=atol, rtol=rtol)
		evolve_LTB.set_initial_value(y_init, t_init).set_f_params(E,dEdr,M,dMdr,Lambda)
		#If you wish to experiment with the Jacobian uncomment the two lines below 
		#and implement the function LTB_ScaleFactor_Jac
		#evolve_LTB = ode(self.LTB_ScaleFactor_derivs,self.LTB_ScaleFactor_Jac).set_integrator('vode', method='Bdf', with_jacobian=True,atol=atol, rtol=rtol)
		#evolve_LTB.set_initial_value(y_init, t_init).set_f_params(E,dEdr,M,dMdr,Lambda).set_jac_params(E,dEdr,M,dMdr,Lambda)
		
		#log distributed time steps
		#t_vec = np.logspace(np.log10(t_init),np.log10(2.01),num=num_pt,endpoint=True)
		t_vec = np.logspace(np.log10(1e-4),np.log10(30.01*306.60139383811764),num=num_pt,endpoint=True)#changed from 1e-4 to 1e-5
		i=0
		dt=0.
		t_dump = np.logspace(np.log10(t_init),np.log10(1e-4),num=200,endpoint=True)#num=200 to 20
		#print 'now here'
		while evolve_LTB.successful() and i<200-2:#200-2:
			#print i
			dt = t_dump[i+1]-t_dump[i]
			evolve_LTB.integrate(evolve_LTB.t + dt)
			i = i+1
		R_vec[0], Rdot_vec[0], Rdash_vec[0] = evolve_LTB.y
		crap, Rdotdot_vec[0], Rdashdot_vec[0] = self.LTB_ScaleFactor_derivs(evolve_LTB.t,
			                                evolve_LTB.y,E,dEdr,M,dMdr,Lambda)
		#print 'now there'
		i = 0
		dt= 0.
		while evolve_LTB.successful() and i<=num_pt-2: #evolve_LTB.t<2.:   #evolve_LTB.y[i_R] < r_loc:  
			dt = t_vec[i+1]-t_vec[i]
			evolve_LTB.integrate(evolve_LTB.t + dt)
			R_vec[i+1], Rdot_vec[i+1], Rdash_vec[i+1] = evolve_LTB.y
			#crap, Rdotdot_vec[i+1], Rdashdot_vec[i+1] = self.LTB_ScaleFactor_derivs(evolve_LTB.t,
			#                                evolve_LTB.y,E,dEdr,M,dMdr,Lambda)
			i = i+1
		crap, Rdotdot_vec, Rdashdot_vec = self.LTB_ScaleFactor_derivs(t_vec,
	                               np.array([R_vec,Rdot_vec,Rdash_vec]),E,dEdr,M,dMdr,Lambda)
		print Rdashdot_vec[-1],Rdashdot_vec[-50] , 'and', Rdotdot_vec[-1],Rdotdot_vec[-50]
		print Rdashdot_vec[0] , 'and', Rdotdot_vec[0]
		return t_vec, R_vec, Rdot_vec, Rdash_vec, Rdotdot_vec, Rdashdot_vec


class LTB_geodesics():
	"""
	Solves the geodesics for an off center observer Eq. (3.19)-(3.20) in 
	``Structures in the Universe by Exact Method`` by Krzystof Bolejko etal.
	"""
	def __init__(self, R_spline,Rdot_spline,Rdash_spline,Rdashdot_spline,LTB_E, LTB_Edash, *args, **kwargs):
		self.R         = R_spline
		self.Rdot      = Rdot_spline
		self.Rdash     = Rdash_spline
		self.Rdashdot  = Rdashdot_spline
		self.args      = args
		self.kwargs    = kwargs
		self.E         = LTB_E
		self.Edash     = LTB_Edash
		# i stands for integer index
		self.i_lambda = 0; self.i_t = 1; self.i_r = 2; self.i_p = 3; self.i_theta = 4
		#self.i_z = 0; self.i_t = 1; self.i_r = 2; self.i_p = 3; self.i_theta = 4
	
	def LTB_geodesic_derivs(self,t,y,J):
		"""
		Returns the derivatives w.r.t redshift ``tau``, [tau]=Mpc, for 
		diff(t(tau),tau), diff(r(tau),tau), diff(t(tau),tau,tau) of Eq. (3.19)-(3.20) in 
		``Structures in the Universe by Exact Method`` by Krzystof Bolejko etal.
		Rps:
		    denotes R_p * sin(alpha) = R_p(t_p, r_p) * sin(alpha)
		ktp: 
		    k^t_p which is set to 1 or -1 is the measured energy of the photon
		    at the observer position. It is set to one because its magnitude does 
		    not matter, only its fractional change matters.    
		caution: 
		        In general avoid alpha=pi/2 and 3/2*pi which means the light would
		        be travelling perpendicular to the axis joining the observer and 
		        the center of symmetry.
		"""
		dy_dt = np.empty_like(y)
		
		R        = self.R.ev(y[self.i_r],y[self.i_t])
		Rdot     = self.Rdot.ev(y[self.i_r],y[self.i_t])
		Rdash    = self.Rdash.ev(y[self.i_r],y[self.i_t])
		Rdashdot = self.Rdashdot.ev(y[self.i_r],y[self.i_t])
		Rdashdash = self.Rdash.ev(y[self.i_r],y[self.i_t],dx=1)
######## Get get all derivative from R but is slower!. uncomment below
#		R        = self.R.ev(y[self.i_r],y[self.i_t])
#		Rdot     = self.R.ev(y[self.i_r],y[self.i_t],dy=1)
#		Rdash    = self.R.ev(y[self.i_r],y[self.i_t],dx=1)
#		Rdashdot = self.R.ev(y[self.i_r],y[self.i_t],dx=1,dy=1)
		E = self.E(y[self.i_r])
		Edash = self.Edash(y[self.i_r])
		z = t
		p = y[self.i_p]
		dt_dlambda = -np.sqrt( (Rdash*p)**2/(1.+2.*E)+(J/R)**2)
		
		dz_dlambda = (1.+z)/(-dt_dlambda)*(Rdash*Rdashdot/(1.+2.*E)*p**2 + Rdot/R**3*J**2)
		
		dy_dt[self.i_lambda] = 1.
		
		dy_dt[self.i_t] = dt_dlambda
		
		dy_dt[self.i_r] = p
		
		dy_dt[self.i_p] = 2.*Rdashdot/Rdash*p* (-dt_dlambda) + (1.+2.*E)*J**2/ (R**3*Rdash) + (Edash/(1.+2.*E) - Rdashdash/Rdash)*p**2
		
		dy_dt[self.i_theta] = J/R**2
		
		return dy_dt / dz_dlambda
#		z = y[self.i_z]
#		p = y[self.i_p]
#		#p=p
#		dt_dlambda = -np.sqrt( (Rdash*p)**2/(1.+2.*E)+(J/R)**2)
#		
#		dz_dlambda = (1.+z)/(-dt_dlambda)*(Rdash*Rdashdot/(1.+2.*E)*p**2 + Rdot/R**3*J**2)
#		
#		dy_dt[self.i_z] = dz_dlambda
#		
#		dy_dt[self.i_t] = dt_dlambda
#		
#		dy_dt[self.i_r] = p
#		
#		dy_dt[self.i_p] = 2.*Rdashdot/Rdash*p* (-dt_dlambda) + (1.+2.*E)*J**2/ (R**3*Rdash) + (Edash/(1.+2.*E) - Rdashdash/#Rdash)*p**2
#		
#		dy_dt[self.i_theta] = J/R**2
#		
#		return dy_dt
	
	def __call__(self,rp=45.,tp=0.92,alpha=np.pi/6.,num_pt=20000,atol=1e-12,rtol=1e-10):
		y_init = np.zeros(5)
		p0 = np.cos(alpha)*np.sqrt(1.+2*self.E(rp))/self.Rdash.ev(rp,tp); J = rp*np.sin(alpha)
		y_init[0]=0.; y_init[1]=tp; y_init[2]=rp; y_init[3]=p0; y_init[4] = 0.
		
		#print "R(rp,tp) = ", self.R.ev(rp,tp), rp, tp
		#print "alpha, sign ", alpha, sign
		z_init = 0.
		evolve_LTB_geodesic = ode(self.LTB_geodesic_derivs).set_integrator('vode', method='adams', with_jacobian=False,atol=atol, rtol=rtol)
		evolve_LTB_geodesic.set_initial_value(y_init, z_init).set_f_params(J)
		print 'init_conds ', y_init, z_init, self.Rdash.ev(rp,tp), self.R.ev(rp,tp), 'loc ', rp
		print "and derivs ", self.LTB_geodesic_derivs(t=0.,y=y_init,J=J)
		print "E, Edash, J ", self.E(rp), self.Edash(rp), J
		#lambda_vec =  np.concatenate(([0.],np.logspace(np.log10(1e-6),np.log10(10*tp),num=num_pt,endpoint=True)))
		#z_vec =  np.linspace(0.,3000.,num=num_pt,endpoint=True)
		#z_vec =  np.linspace(0.,3.,num=num_pt,endpoint=True)
		num_pt1 = num_pt-5000
		z_vec = np.concatenate(([0.],np.logspace(np.log10(1e-3),np.log10(1.),num=num_pt1,endpoint=False)))
		z_vec = np.concatenate((z_vec,np.linspace(1.,3000,num=num_pt-num_pt1-1,endpoint=True)))
		null_vec = np.empty((num_pt,1+5))
		null_vec[0] = np.concatenate(([0.],y_init))
		i = 0
		dz= 0.
		#dlambda = 0.
		t_last_scattering = 3e-4*306.60139383811764#3e-4*306.60139383811764
		while evolve_LTB_geodesic.successful() and evolve_LTB_geodesic.y[self.i_t]>=t_last_scattering and evolve_LTB_geodesic.y[self.i_r]>1e-3: 
		#3e-4 billion years is 300,000 years (time of last scattering)
			dz = z_vec[i+1]-z_vec[i]
			#dlambda = lambda_vec[i+1]-lambda_vec[i]
			evolve_LTB_geodesic.integrate(evolve_LTB_geodesic.t + dz)#dlambda)
			null_vec[i][0] = evolve_LTB_geodesic.t
			null_vec[i][1:] = evolve_LTB_geodesic.y
			print "null_vec[i] = ", null_vec[i]
			i = i + 1
		#one last step to get as close to get as close to time of last scattering as possible (linear interpolation)
		if (null_vec[i-1][2] < t_last_scattering):
			#i-1 because it is incremented before failing
			#linearly interpolate for z
			null_vec[i-1][0:1] = null_vec[i-2][0:1]+(null_vec[i-1][0:1]-null_vec[i-2][0:1])*\
			                  (t_last_scattering - null_vec[i-2][2])/ \
			                  (null_vec[i-1][2]-null_vec[i-2][2])
			#and interpolate for r, kt
			null_vec[i-1][3:] = null_vec[i-2][3:]+(null_vec[i-1][3:]-null_vec[i-2][3:])*\
			                  (t_last_scattering - null_vec[i-2][2])/\
			                  (null_vec[i-1][2]-null_vec[i-2][2])
			#and set t to t_last_scattering
			null_vec[i-1][2] = t_last_scattering
			#print "o yeah baby"
		elif (null_vec[i-1][2] == t_last_scattering):
			pass	
		else:
			#raise Exception("did not over shoot in solving the geodesics")
			derivs = self.LTB_geodesic_derivs(evolve_LTB_geodesic.t,evolve_LTB_geodesic.y,J)
			dz = (t_last_scattering - evolve_LTB_geodesic.y[1])/ derivs[1]
			#dlambda = (t_last_scattering - evolve_LTB_geodesic.y[1])/ derivs[1]
			evolve_LTB_geodesic.integrate(evolve_LTB_geodesic.t + dz)#dlambda)
			#i-1 because it is incremented before failing
			null_vec[i-1][0] = evolve_LTB_geodesic.t
			null_vec[i-1][1:] = evolve_LTB_geodesic.y
		#derivs = self.LTB_geodesic_derivs(evolve_LTB_geodesic.t,evolve_LTB_geodesic.y,sign,Rps,ktp)
		#dz = (t_last_scattering - evolve_LTB_geodesic.y[1])/ derivs[1]
		#print "dz ", dz, derivs[1],t_last_scattering, evolve_LTB_geodesic.y[1]     
		#evolve_LTB_geodesic.integrate(evolve_LTB_geodesic.t + dz)
		#print evolve_LTB_geodesic.t, evolve_LTB_geodesic.y
		#print 'redshift ', evolve_LTB_geodesic.y[self.i_tdot],ktp, evolve_LTB_geodesic.y[self.i_tdot]/ktp
		
		#print null_vec[i-1]
		#print 'redshift ', null_vec[i-1][4],ktp,null_vec[i-1][4]/ktp
		return null_vec[:i]







