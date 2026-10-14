from pathlib import Path
import json, platform, csv
import numpy as np
import scipy
from scipy.optimize import brentq, root, minimize
from scipy.integrate import quad, solve_ivp
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
P=Path(__file__).resolve().parent
A=P/'assets'; A.mkdir(exist_ok=True)
D,dy,L,rho,g=10.,2.,12.,0.8,9.81
w=rho*g

def constants(length):
    ell=np.sqrt(length**2-dy**2)
    u=brentq(lambda u:np.sinh(u)/u-ell/D,1e-7,15,xtol=5e-15)
    a=D/(2*u); v=np.arctanh(dy/length); x0=D/2-a*v
    c=-a*np.cosh(x0/a)
    return a,x0,c

a,x0,c=constants(L)
y=lambda x:a*np.cosh((x-x0)/a)+c
yp=lambda x:np.sinh((x-x0)/a)
ypp=lambda x:np.cosh((x-x0)/a)/a
q=lambda x:np.cosh((x-x0)/a)
H=w*a; V0=w*a*np.sinh(-x0/a); lam=-w*c
T=lambda x:H*q(x)
U=quad(lambda x:w*y(x)*q(x),0,D,epsabs=1e-11)[0]
S=quad(q,0,D,epsabs=1e-11)[0]
s=np.linspace(0,L,501)
xs=lambda s:x0+a*np.arcsinh(s/a+np.sinh(-x0/a))
ys=lambda s:y(xs(s))
# Independent shooting from force equilibrium in material arclength.
def ode(s,r,H,V0):
    v=V0+w*s; tt=np.hypot(H,v)
    return [H/tt,v/tt]
def endpoint(z):
    h=np.exp(z[0]); vv=z[1]
    sol=solve_ivp(lambda s,r:ode(s,r,h,vv),(0,L),[0.,0.],rtol=2e-12,atol=2e-13,dense_output=True)
    return sol
shoot=root(lambda z:endpoint(z).y[:,-1]-[D,dy],[np.log(40.),-40.],tol=1e-10)
sol=endpoint(shoot.x); rr=sol.sol(s)
shoot_err=np.max(np.hypot(rr[0]-xs(s),rr[1]-ys(s)))
# Equal material-length polygon: exact link constraints, exact link potential.
meshes=[]; polygons=[]
for n in [20,40,80]:
    ds=L/n; ss=np.linspace(0,L,n+1)
    init=np.column_stack([xs(ss),ys(ss)])
    init[1:-1,1]+=0.15*np.sin(np.pi*ss[1:-1]/L)
    def unpack(z):return np.vstack(([0.,0.],z.reshape(-1,2),[D,dy]))
    def fun(z):return w*ds*(np.sum(z.reshape(-1,2)[:,1])+dy/2)
    grad=np.tile([0.,w*ds],n-1)
    def con(z):return np.sum(np.diff(unpack(z),axis=0)**2,axis=1)/ds**2-1
    def jac(z):
        e=np.diff(unpack(z),axis=0); J=np.zeros((n,2*(n-1)))
        for k in range(n):
            if k>0:J[k,2*(k-1):2*k]=-2*e[k]/ds**2
            if k<n-1:J[k,2*k:2*(k+1)]=2*e[k]/ds**2
        return J
    res=minimize(fun,init[1:-1].ravel(),jac=lambda z:grad,method='SLSQP',constraints={'type':'eq','fun':con,'jac':jac},options={'ftol':1e-11,'maxiter':1200})
    r=unpack(res.x); err=np.max(np.linalg.norm(r-np.column_stack([xs(ss),ys(ss)]),axis=1))
    lens=np.linalg.norm(np.diff(r,axis=0),axis=1)
    J=jac(res.x); mult=np.linalg.lstsq(J.T,-grad,rcond=None)[0]
    kkt=np.max(np.abs(grad+J.T@mult))
    entry={'N':n,'success':bool(res.success),'iterations':res.nit,'max_position_error_m':float(err),'max_link_length_error_m':float(np.max(np.abs(lens-ds))),'potential_J':float(res.fun),'abs_potential_error_J':float(abs(res.fun-U)),'kkt_residual':float(kkt)}
    assert res.success and entry['max_link_length_error_m']<1e-7, entry
    meshes.append(entry); polygons.append(r)
xx=np.linspace(0,D,801)
metrics={'parameters':{'D_m':D,'dy_m':dy,'L_m':L,'rho_kg_per_m':rho,'g_m_per_s2':g,'w_N_per_m':w},'a_m':a,'x0_m':x0,'c_m':c,'lowest_y_m':a+c,'H_N':H,'V0_N':V0,'V_end_N':V0+w*L,'T_left_N':float(T(0)),'T_right_N':float(T(D)),'lambda_N':lam,'U_J':U,'arc_length_m':S,'arc_length_residual_m':abs(S-L),'boundary_residual_m':max(abs(y(0)),abs(y(D)-dy)),'EL_residual':float(np.max(np.abs((w*y(xx)+lam)*ypp(xx)-w*(1+yp(xx)**2)))),'force_residual_N':float(abs((V0+w*L)-V0-w*L)),'shooting':{'success':bool(shoot.success),'H_N':float(np.exp(shoot.x[0])),'V0_N':float(shoot.x[1]),'endpoint_residual_m':float(np.max(np.abs(rr[:,-1]-[D,dy]))),'max_position_error_m':float(shoot_err)},'mesh_convergence':meshes,'environment':{'python':platform.python_version(),'numpy':np.__version__,'scipy':scipy.__version__,'matplotlib':matplotlib.__version__}}
assert shoot.success and shoot_err<1e-8 and abs(S-L)<1e-9
(P/'results.json').write_text(json.dumps(metrics,indent=2,ensure_ascii=False))
with (P/'curve.csv').open('w') as f:
    out=csv.writer(f);out.writerow(['x_m','y_m','s_m','slope','tension_N','vertical_component_N'])
    for x in xx:out.writerow([x,y(x),a*(np.sinh((x-x0)/a)-np.sinh(-x0/a)),yp(x),T(x),H*yp(x)])
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':12,'axes.spines.top':False,'axes.spines.right':False,'axes.labelcolor':'#15263c','text.color':'#15263c','axes.edgecolor':'#718096','figure.facecolor':'white','savefig.facecolor':'white'})
navy,teal,orange='#173453','#008b8b','#de8634'
def save(fig,name):
    fig.tight_layout();fig.savefig(A/(name+'.png'),dpi=220);fig.savefig(A/(name+'.svg'));plt.close(fig)
fig,ax=plt.subplots(figsize=(8,4.5));ax.plot(xx,y(xx),color=teal,lw=3,label='Analytic catenary');ax.plot(rr[0,::25],rr[1,::25],'o',mfc='white',mec=orange,ms=5,label='Force-equilibrium shooting');ax.plot([0,D],[0,dy],'--',color='#a2adbb',label='Endpoint chord');ax.scatter([0,D],[0,dy],color=navy,s=65,zorder=5);ax.scatter([x0],[a+c],color=orange,zorder=6);ax.annotate('Lowest point',xy=(x0,a+c),xytext=(x0+1.0,a+c+.6),arrowprops={'arrowstyle':'->','color':navy});ax.set(xlabel='x (m)',ylabel='y (m)',xlim=(-.3,10.3),ylim=(-3.3,2.5));ax.grid(alpha=.15);ax.legend(fontsize=10,loc='upper left');save(fig,'shape')
fig,ax=plt.subplots(figsize=(8,4.2));ax.plot(xx,T(xx),color=teal,lw=3,label='Tension magnitude T');ax.plot(xx,H+0*xx,'--',color=navy,label='Horizontal component H');ax.plot(xx,H*yp(xx),color=orange,lw=2,label='Signed vertical component V');ax.axhline(0,color='#a2adbb',lw=.7);ax.set(xlabel='x (m)',ylabel='Force (N)');ax.grid(alpha=.15);ax.legend(fontsize=10);save(fig,'tension')
fig,axs=plt.subplots(1,2,figsize=(9,4));nn=np.array([m['N'] for m in meshes]);ee=np.array([m['max_position_error_m'] for m in meshes]);axs[0].loglog(nn,ee,'o-',color=teal,label='Position error');axs[0].loglog(nn,ee[0]*(nn[0]/nn)**2,'--',color=orange,label='Reference N^-2');axs[0].set(xlabel='Number of links N',ylabel='Max position error (m)');axs[0].legend(fontsize=10);axs[0].grid(alpha=.15,which='both');axs[1].plot(xx,y(xx),color=teal,lw=2,label='Continuum');axs[1].plot(polygons[0][:,0],polygons[0][:,1],'o-',color=orange,ms=3,label='N=20 polygon');axs[1].set(xlabel='x (m)',ylabel='y (m)');axs[1].legend(fontsize=10);axs[1].grid(alpha=.15);save(fig,'convergence')
fig,axs=plt.subplots(1,2,figsize=(9,4));LL=np.linspace(np.hypot(D,dy)+.02,16,100);aa=[];ssag=[]
for length in LL:
    aa1,x01,c1=constants(length);aa.append(aa1);ssag.append(-(aa1+c1))
axs[0].plot(LL,w*np.array(aa),color=teal,lw=2.5);axs[0].set(xlabel='Rope length L (m)',ylabel='Horizontal tension H (N)');axs[0].grid(alpha=.15)
for length in [10.5,12,14,16]:
    aa1,x01,c1=constants(length);axs[1].plot(xx,aa1*np.cosh((xx-x01)/aa1)+c1,label=f'L={length:g} m')
axs[1].set(xlabel='x (m)',ylabel='y (m)');axs[1].grid(alpha=.15);axs[1].legend(fontsize=10);save(fig,'sensitivity')
# Symmetric example checks the small-sag approximation at equal endpoint heights.
ratios=np.array([.10,.25,.5,1.,1.5]);para=[]
for z in ratios:
    # |x-x0|/a <= z, relative error measured against exact sag at endpoint
    para.append(float(1-z*z/(2*(np.cosh(z)-1))))
metrics['parabola_relative_sag_errors']=dict(zip(map(str,ratios),para))
(P/'results.json').write_text(json.dumps(metrics,indent=2,ensure_ascii=False))
print(json.dumps(metrics,indent=2,ensure_ascii=False))
