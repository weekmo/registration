# -*- coding: utf-8 -*-
"""
1- dipy
2- Non-linear optimizer
3- Non rigid ICP

 --- Eval ---
 left to right
 1- Distances
 2- Visually
 3- local and global deformation
 x- effect on Co Bundle Map
"""

import sys

import numpy as np
from scipy import sparse
from scipy.sparse.linalg import lsqr
from sklearn.neighbors import KDTree

import matplotlib.pyplot as plt

from src.tractography.io import read_ply
from src.tractography.Utils import pca_transform_norm
from src.tractography.viz import draw_bundles

num = 9

static = read_ply('data/197348/m_ex_atr-left_shore.ply')
moving = read_ply('data/197348/m_ex_atr-right_shore.ply')

draw_bundles([moving,static],[[0,0,1],[1,0,0]])

''' Get points cloud '''
con_static = np.concatenate(static)
con_moving = np.concatenate(moving)
print(np.count_nonzero(con_moving))
''' Build KDTree '''
kdtree = KDTree(con_static)
distances = kdtree.query(con_moving,k=1)[0]

''' Get the threshold '''
max_range = max(distances)
plt.hist(distances, bins='auto',range=(0,max_range))
plt.title("Original Position\nTotal distance: {:}".format(round(distances.sum(),2)))
plt.ylabel("Frequncy")
plt.xlabel("Distance")
plt.savefig('new_plan/1{:02d}_hist_original.png'.format(num), dpi=600)

''' Apply PCA '''
pre_moving = pca_transform_norm(static, moving, best=True)
con_moving = np.concatenate(pre_moving)
draw_bundles([pre_moving,static],[[0,0,1],[1,0,0]])

''' Flip '''
'''
pre_moving = flip(moving,x=-1)
con_moving = np.concatenate(pre_moving)
draw_bundles([pre_moving,static],[[0,0,1],[1,0,0]])
'''

''' Get the threshold '''
distances = kdtree.query(con_moving,k=1)[0]
plt.hist(distances, bins='auto', range=(0,max_range))
plt.title("After PCA\nTotal distance: {:2f}".format(distances.sum()))
plt.ylabel("Frequncy")
plt.xlabel("Distance")
plt.savefig('new_plan/1{:02d}_hist_PCA.png'.format(num), dpi=600)

''' Vars '''
# 6 | 99999
# 5 | 99999
# 4 | 99999
# 3 | 99999
# 3 | 999
# 2 | 999
length = len(con_moving)
threshold=7
alpha = 999999
lamb = 1
suff_dist = 5
temp_dist = sys.maxsize

while temp_dist > suff_dist:
    length = len(con_moving)
    ''' Get Distances and indeces for closest points '''
    dist,ids = kdtree.query(con_moving,k=1)
    dist = np.concatenate(dist)
    ids = np.concatenate(ids)
    ''' Get w by applying the threshold '''
    W = np.where(dist>threshold,0,1)
    
    ''' Make w diagonal '''
    W = sparse.diags(W)
    ''' Moving in homogeneouse coordinates '''
    new_con_moving = np.ones((length,4))
    new_con_moving[:,:-1] = con_moving
    
    D = sparse.coo_matrix((np.concatenate(new_con_moving),
                    (np.repeat(np.arange(length),4),np.arange(length*4))),
                    (length,length*4)).tocsr()
    ''' Get WD '''
    WD = W.dot(D)
    ''' Get WD '''
    WU = W.dot(con_static[ids])
    
    ''' Stiffnes '''
    length = con_moving.shape[0]-len(moving)
    data = np.tile([-1,1],length)
    row = np.arange(length).repeat(2)
    
    col=[]
    j=0
    for track in moving:
        end = j+track.shape[0]
        col.append(np.arange(j,end).repeat(2)[1:-1])
        j = end
    col = np.concatenate(col)
    
    M = sparse.csr_matrix((data,(row,col)),(length,con_moving.shape[0]))
    
    ''' Get G '''
    # G = sparse.diags([1,1,1,lamb])
    MG = alpha*sparse.kron(M,sparse.diags([1,1,1,lamb])).tocsr()
    ''' Get Zeros '''
    zer = np.zeros((MG.shape[0],3))
    
    A = sparse.vstack([MG,WD])
    B = np.vstack([zer,WU])
    
    X = np.zeros((A.shape[1],3))
    acon = np.zeros((3))
    
    for i in range(3):
        result = np.array(lsqr(A,B[:,i]))
        X[:,i] = result[0]
        acon[i] = result[6]
    print(acon)
    
    con_moving=D.dot(X)
    temp_dist = np.sum(dist) - np.sum(kdtree.query(con_moving,k=1)[0])
    print(temp_dist)


i = 0
end=0
new_moving=[]
for track in moving:
    end = len(track)+i
    new_moving.append(con_moving[i:end])
    #new_moving.append([i,end])
    i = end
        
# bins='auto'
''' Get the threshold '''
distances = kdtree.query(con_moving,k=1)[0]
plt.hist(distances, bins='auto',range=(0,max_range))
plt.title("After ICP | Total Distance: {:}"
          .format(round(distances.sum(),2))+
          "\nMax distance: "+str(threshold)+"mm, alpha: "+str(alpha))
plt.ylabel("Frequncy")
plt.xlabel("Distance")
plt.savefig('new_plan/1{:02d}_hist_ICP.png'.format(num), dpi=600)
draw_bundles([new_moving,static],[[0,0,1],[1,0,0]])