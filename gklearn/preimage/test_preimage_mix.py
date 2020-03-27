#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Sep  5 15:59:00 2019

@author: ljia
"""

import numpy as np
import networkx as nx
import matplotlib.pyplot as plt
import time
import random
#from tqdm import tqdm

from gklearn.utils.graphfiles import loadDataset
from gklearn.preimage.ged import ged_median
from gklearn.preimage.utils import compute_kernel, get_same_item_indices, remove_edges
from gklearn.preimage.preimage_iam import preimage_iam_random_mix

###############################################################################
# tests on different values on grid of median-sets and k.

def test_preimage_mix_grid_k_median_nb():
    ds = {'name': 'MUTAG', 'dataset': '../datasets/MUTAG/MUTAG_A.txt',
          'extra_params': {}}  # node/edge symb
    Gn, y_all = loadDataset(ds['dataset'], extra_params=ds['extra_params'])
#    Gn = Gn[0:50]
    remove_edges(Gn)
    gkernel = 'marginalizedkernel'
    
    lmbda = 0.03 # termination probalility
    r_max = 5 # iteration limit for pre-image.
    l_max = 500 # update limit for random generation
#    alpha_range = np.linspace(0.5, 0.5, 1)
#    k = 5 # k nearest neighbors
    epsilon = 1e-6
    InitIAMWithAllDk = True
    InitRandomWithAllDk = True
    # parameters for GED function
    ged_cost='CHEM_1'
    ged_method='IPFP'
    saveGXL='gedlib'
    # parameters for IAM function
    c_ei=1
    c_er=1
    c_es=1
    ite_max_iam = 50
    epsilon_iam = 0.001
    removeNodes = True
    connected_iam = False
    
    # number of graphs; we what to compute the median of these graphs. 
    nb_median_range = [2, 3, 4, 5, 10, 20, 30, 40, 50, 100]
    # number of nearest neighbors.
    k_range = [5, 6, 7, 8, 9, 10, 20, 30, 40, 50, 100]
    
    # find out all the graphs classified to positive group 1.
    idx_dict = get_same_item_indices(y_all)
    Gn = [Gn[i] for i in idx_dict[1]]
    
#    # compute Gram matrix.
#    time0 = time.time()
#    km = compute_kernel(Gn, gkernel, True)
#    time_km = time.time() - time0    
#    # write Gram matrix to file.
#    np.savez('results/gram_matrix_marg_itr10_pq0.03_mutag_positive.gm', gm=km, gmtime=time_km)
        
    
    time_list = []
    dis_ks_min_list = []
    sod_gs_list = []
    sod_gs_min_list = []
    nb_updated_list_iam = []
    nb_updated_list_random = []
    nb_updated_k_list_iam = []
    nb_updated_k_list_random = []
    g_best = []
    for idx_nb, nb_median in enumerate(nb_median_range):
        print('\n-------------------------------------------------------')
        print('number of median graphs =', nb_median)
        random.seed(1)
        idx_rdm = random.sample(range(len(Gn)), nb_median)
        print('graphs chosen:', idx_rdm)
        Gn_median = [Gn[idx].copy() for idx in idx_rdm]
        
#        for g in Gn_median:
#            nx.draw(g, labels=nx.get_node_attributes(g, 'atom'), with_labels=True)
##            plt.savefig("results/preimage_mix/mutag.png", format="PNG")
#            plt.show()
#            plt.clf()                         
                    
        ###################################################################
        gmfile = np.load('results/gram_matrix_marg_itr10_pq0.03_mutag_positive.gm.npz')
        km_tmp = gmfile['gm']
        time_km = gmfile['gmtime']
        # modify mixed gram matrix.
        km = np.zeros((len(Gn) + nb_median, len(Gn) + nb_median))
        for i in range(len(Gn)):
            for j in range(i, len(Gn)):
                km[i, j] = km_tmp[i, j]
                km[j, i] = km[i, j]
        for i in range(len(Gn)):
            for j, idx in enumerate(idx_rdm):
                km[i, len(Gn) + j] = km[i, idx]
                km[len(Gn) + j, i] = km[i, idx]
        for i, idx1 in enumerate(idx_rdm):
            for j, idx2 in enumerate(idx_rdm):
                km[len(Gn) + i, len(Gn) + j] = km[idx1, idx2]
                
        ###################################################################
        alpha_range = [1 / nb_median] * nb_median
        
        time_list.append([])
        dis_ks_min_list.append([])
        sod_gs_list.append([])
        sod_gs_min_list.append([])
        nb_updated_list_iam.append([])
        nb_updated_list_random.append([])
        nb_updated_k_list_iam.append([])
        nb_updated_k_list_random.append([])
        g_best.append([])   
        
        for k in k_range:
            print('\n++++++++++++++++++++++++++++++++++++++++++++++++++++++++++\n')
            print('k =', k)
            time0 = time.time()
            dhat, ghat_list, dis_of_each_itr, nb_updated_iam, nb_updated_random, \
                nb_updated_k_iam, nb_updated_k_random = \
                preimage_iam_random_mix(Gn, Gn_median,
                alpha_range, range(len(Gn), len(Gn) + nb_median), km, k, r_max, 
                l_max, gkernel, epsilon=epsilon, InitIAMWithAllDk=InitIAMWithAllDk, 
                InitRandomWithAllDk=InitRandomWithAllDk,
                params_iam={'c_ei': c_ei, 'c_er': c_er, 'c_es': c_es, 
                            'ite_max': ite_max_iam, 'epsilon': epsilon_iam,
                            'removeNodes': removeNodes, 'connected': connected_iam},
                params_ged={'ged_cost': ged_cost, 'ged_method': ged_method, 
                            'saveGXL': saveGXL})
                
            time_total = time.time() - time0 + time_km
            print('time: ', time_total)
            time_list[idx_nb].append(time_total)
            print('\nsmallest distance in kernel space: ', dhat) 
            dis_ks_min_list[idx_nb].append(dhat)
            g_best[idx_nb].append(ghat_list)
            print('\nnumber of updates of the best graph by IAM: ', nb_updated_iam)
            nb_updated_list_iam[idx_nb].append(nb_updated_iam)
            print('\nnumber of updates of the best graph by random generation: ', 
                  nb_updated_random)
            nb_updated_list_random[idx_nb].append(nb_updated_random)
            print('\nnumber of updates of k nearest graphs by IAM: ', nb_updated_k_iam)
            nb_updated_k_list_iam[idx_nb].append(nb_updated_k_iam)
            print('\nnumber of updates of k nearest graphs by random generation: ', 
                  nb_updated_k_random)
            nb_updated_k_list_random[idx_nb].append(nb_updated_k_random) 
            
            # show the best graph and save it to file.
            print('the shortest distance is', dhat)
            print('one of the possible corresponding pre-images is')
            nx.draw(ghat_list[0], labels=nx.get_node_attributes(ghat_list[0], 'atom'), 
                    with_labels=True)
            plt.savefig('results/preimage_mix/mutag_median_nb' + str(nb_median) + 
                        '_k' + str(k) + '.png', format="PNG")
    #        plt.show()
            plt.clf()
    #        print(ghat_list[0].nodes(data=True))
    #        print(ghat_list[0].edges(data=True))
        
            # compute the corresponding sod in graph space.
            sod_tmp, _ = ged_median([ghat_list[0]], Gn_median, ged_cost=ged_cost, 
                                         ged_method=ged_method, saveGXL=saveGXL)
            sod_gs_list[idx_nb].append(sod_tmp)
            sod_gs_min_list[idx_nb].append(np.min(sod_tmp))
            print('\nsmallest sod in graph space: ', np.min(sod_tmp))
        
    print('\nsods in graph space: ', sod_gs_list)
    print('\nsmallest sod in graph space for each set of median graphs and k: ', 
          sod_gs_min_list)  
    print('\nsmallest distance in kernel space for each set of median graphs and k: ', 
          dis_ks_min_list) 
    print('\nnumber of updates of the best graph for each set of median graphs and k by IAM: ', 
          nb_updated_list_iam)
    print('\nnumber of updates of the best graph for each set of median graphs and k by random generation: ', 
          nb_updated_list_random)
    print('\nnumber of updates of k nearest graphs for each set of median graphs and k by IAM: ', 
          nb_updated_k_list_iam)
    print('\nnumber of updates of k nearest graphs for each set of median graphs and k by random generation: ', 
          nb_updated_k_list_random)
    print('\ntimes:', time_list)
    
    


###############################################################################
# tests on different numbers of median-sets.

def test_preimage_mix_median_nb():
    ds = {'name': 'MUTAG', 'dataset': '../datasets/MUTAG/MUTAG_A.txt',
          'extra_params': {}}  # node/edge symb
    Gn, y_all = loadDataset(ds['dataset'], extra_params=ds['extra_params'])
#    Gn = Gn[0:50]
    remove_edges(Gn)
    gkernel = 'marginalizedkernel'
    
    lmbda = 0.03 # termination probalility
    r_max = 5 # iteration limit for pre-image.
    l_max = 500 # update limit for random generation
#    alpha_range = np.linspace(0.5, 0.5, 1)
    k = 5 # k nearest neighbors
    epsilon = 1e-6
    InitIAMWithAllDk = True
    InitRandomWithAllDk = True
    # parameters for GED function
    ged_cost='CHEM_1'
    ged_method='IPFP'
    saveGXL='gedlib'
    # parameters for IAM function
    c_ei=1
    c_er=1
    c_es=1
    ite_max_iam = 50
    epsilon_iam = 0.001
    removeNodes = True
    connected_iam = False
    
    # number of graphs; we what to compute the median of these graphs. 
    nb_median_range = [2, 3, 4, 5, 10, 20, 30, 40, 50, 100]
    
    # find out all the graphs classified to positive group 1.
    idx_dict = get_same_item_indices(y_all)
    Gn = [Gn[i] for i in idx_dict[1]]
    
#    # compute Gram matrix.
#    time0 = time.time()
#    km = compute_kernel(Gn, gkernel, True)
#    time_km = time.time() - time0    
#    # write Gram matrix to file.
#    np.savez('results/gram_matrix_marg_itr10_pq0.03_mutag_positive.gm', gm=km, gmtime=time_km)
        
    
    time_list = []
    dis_ks_min_list = []
    sod_gs_list = []
    sod_gs_min_list = []
    nb_updated_list_iam = []
    nb_updated_list_random = []
    nb_updated_k_list_iam = []
    nb_updated_k_list_random = []
    g_best = []
    for nb_median in nb_median_range:
        print('\n-------------------------------------------------------')
        print('number of median graphs =', nb_median)
        random.seed(1)
        idx_rdm = random.sample(range(len(Gn)), nb_median)
        print('graphs chosen:', idx_rdm)
        Gn_median = [Gn[idx].copy() for idx in idx_rdm]
        
#        for g in Gn_median:
#            nx.draw(g, labels=nx.get_node_attributes(g, 'atom'), with_labels=True)
##            plt.savefig("results/preimage_mix/mutag.png", format="PNG")
#            plt.show()
#            plt.clf()                         
                    
        ###################################################################
        gmfile = np.load('results/gram_matrix_marg_itr10_pq0.03_mutag_positive.gm.npz')
        km_tmp = gmfile['gm']
        time_km = gmfile['gmtime']
        # modify mixed gram matrix.
        km = np.zeros((len(Gn) + nb_median, len(Gn) + nb_median))
        for i in range(len(Gn)):
            for j in range(i, len(Gn)):
                km[i, j] = km_tmp[i, j]
                km[j, i] = km[i, j]
        for i in range(len(Gn)):
            for j, idx in enumerate(idx_rdm):
                km[i, len(Gn) + j] = km[i, idx]
                km[len(Gn) + j, i] = km[i, idx]
        for i, idx1 in enumerate(idx_rdm):
            for j, idx2 in enumerate(idx_rdm):
                km[len(Gn) + i, len(Gn) + j] = km[idx1, idx2]
                
        ###################################################################
        alpha_range = [1 / nb_median] * nb_median
        time0 = time.time()
        dhat, ghat_list, dis_of_each_itr, nb_updated_iam, nb_updated_random, \
            nb_updated_k_iam, nb_updated_k_random = \
            preimage_iam_random_mix(Gn, Gn_median,
            alpha_range, range(len(Gn), len(Gn) + nb_median), km, k, r_max, 
            l_max, gkernel, epsilon=epsilon, InitIAMWithAllDk=InitIAMWithAllDk, 
            InitRandomWithAllDk=InitRandomWithAllDk,
            params_iam={'c_ei': c_ei, 'c_er': c_er, 'c_es': c_es, 
                        'ite_max': ite_max_iam, 'epsilon': epsilon_iam,
                        'removeNodes': removeNodes, 'connected': connected_iam},
            params_ged={'ged_cost': ged_cost, 'ged_method': ged_method, 
                        'saveGXL': saveGXL})
            
        time_total = time.time() - time0 + time_km
        print('time: ', time_total)
        time_list.append(time_total)
        print('\nsmallest distance in kernel space: ', dhat) 
        dis_ks_min_list.append(dhat)
        g_best.append(ghat_list)
        print('\nnumber of updates of the best graph by IAM: ', nb_updated_iam)
        nb_updated_list_iam.append(nb_updated_iam)
        print('\nnumber of updates of the best graph by random generation: ', 
              nb_updated_random)
        nb_updated_list_random.append(nb_updated_random)
        print('\nnumber of updates of k nearest graphs by IAM: ', nb_updated_k_iam)
        nb_updated_k_list_iam.append(nb_updated_k_iam)
        print('\nnumber of updates of k nearest graphs by random generation: ', 
              nb_updated_k_random)
        nb_updated_k_list_random.append(nb_updated_k_random) 
        
        # show the best graph and save it to file.
        print('the shortest distance is', dhat)
        print('one of the possible corresponding pre-images is')
        nx.draw(ghat_list[0], labels=nx.get_node_attributes(ghat_list[0], 'atom'), 
                with_labels=True)
        plt.savefig('results/preimage_mix/mutag_median_nb' + str(nb_median) + 
                    '.png', format="PNG")
#        plt.show()
        plt.clf()
#        print(ghat_list[0].nodes(data=True))
#        print(ghat_list[0].edges(data=True))
    
        # compute the corresponding sod in graph space.
        sod_tmp, _ = ged_median([ghat_list[0]], Gn_median, ged_cost=ged_cost, 
                                     ged_method=ged_method, saveGXL=saveGXL)
        sod_gs_list.append(sod_tmp)
        sod_gs_min_list.append(np.min(sod_tmp))
        print('\nsmallest sod in graph space: ', np.min(sod_tmp))
        
    print('\nsods in graph space: ', sod_gs_list)
    print('\nsmallest sod in graph space for each set of median graphs: ', sod_gs_min_list)  
    print('\nsmallest distance in kernel space for each set of median graphs: ', 
          dis_ks_min_list) 
    print('\nnumber of updates of the best graph for each set of median graphs by IAM: ', 
          nb_updated_list_iam)
    print('\nnumber of updates of the best graph for each set of median graphs by random generation: ', 
          nb_updated_list_random)
    print('\nnumber of updates of k nearest graphs for each set of median graphs by IAM: ', 
          nb_updated_k_list_iam)
    print('\nnumber of updates of k nearest graphs for each set of median graphs by random generation: ', 
          nb_updated_k_list_random)
    print('\ntimes:', time_list)
    
    

###############################################################################
# test on the combination of the two randomly chosen graphs. (the same as in the
# random pre-image paper.)

def test_preimage_mix_2combination_all_pairs():
    ds = {'name': 'MUTAG', 'dataset': '../datasets/MUTAG/MUTAG_A.txt',
          'extra_params': {}}  # node/edge symb
    Gn, y_all = loadDataset(ds['dataset'], extra_params=ds['extra_params'])
#    Gn = Gn[0:50]
    remove_edges(Gn)
    gkernel = 'marginalizedkernel'
    
    lmbda = 0.03 # termination probalility
    r_max = 10 # iteration limit for pre-image.
    l_max = 500 # update limit for random generation
    alpha_range = np.linspace(0.5, 0.5, 1)
    k = 5 # k nearest neighbors
    epsilon = 1e-6
    InitIAMWithAllDk = True
    InitRandomWithAllDk = True
    # parameters for GED function
    ged_cost='CHEM_1'
    ged_method='IPFP'
    saveGXL='gedlib'
    # parameters for IAM function
    c_ei=1
    c_er=1
    c_es=1
    ite_max_iam = 50
    epsilon_iam = 0.001
    removeNodes = True
    connected_iam = False
    
    nb_update_mat_iam = np.full((len(Gn), len(Gn)), np.inf)
    nb_update_mat_random = np.full((len(Gn), len(Gn)), np.inf)
    # test on each pair of graphs.
#    for idx1 in range(len(Gn) - 1, -1, -1):
#        for idx2 in range(idx1, -1, -1):
    for idx1 in range(187, 188):
        for idx2 in range(167, 168):
            g1 = Gn[idx1].copy()
            g2 = Gn[idx2].copy()
        #    Gn[10] = []
        #    Gn[10] = []
            
            nx.draw(g1, labels=nx.get_node_attributes(g1, 'atom'), with_labels=True)
            plt.savefig("results/preimage_mix/mutag187.png", format="PNG")
            plt.show()
            plt.clf()
            nx.draw(g2, labels=nx.get_node_attributes(g2, 'atom'), with_labels=True)
            plt.savefig("results/preimage_mix/mutag167.png", format="PNG")
            plt.show()
            plt.clf()

            ###################################################################            
#            Gn_mix = [g.copy() for g in Gn]
#            Gn_mix.append(g1.copy())
#            Gn_mix.append(g2.copy())
#            
#            # compute
#            time0 = time.time()
#            km = compute_kernel(Gn_mix, gkernel, True)
#            time_km = time.time() - time0
#            
#            # write Gram matrix to file and read it.
#            np.savez('results/gram_matrix_uhpath_itr7_pq0.8.gm', gm=km, gmtime=time_km)
            
            ###################################################################
            gmfile = np.load('results/gram_matrix_marg_itr10_pq0.03.gm.npz')
            km = gmfile['gm']
            time_km = gmfile['gmtime']
            # modify mixed gram matrix.
            for i in range(len(Gn)):
                km[i, len(Gn)] = km[i, idx1]
                km[i, len(Gn) + 1] = km[i, idx2]
                km[len(Gn), i] = km[i, idx1]
                km[len(Gn) + 1, i] = km[i, idx2]
            km[len(Gn), len(Gn)] = km[idx1, idx1]
            km[len(Gn), len(Gn) + 1] = km[idx1, idx2]
            km[len(Gn) + 1, len(Gn)] = km[idx2, idx1]
            km[len(Gn) + 1, len(Gn) + 1] = km[idx2, idx2]
            
            ###################################################################
#            # use only the two graphs in median set as candidates.
#            Gn = [g1.copy(), g2.copy()]
#            Gn_mix = Gn + [g1.copy(), g2.copy()]
#            # compute         
#            time0 = time.time()
#            km = compute_kernel(Gn_mix, gkernel, True)
#            time_km = time.time() - time0
    
            
            time_list = []
            dis_ks_min_list = []
            sod_gs_list = []
            sod_gs_min_list = []
            nb_updated_list_iam = []
            nb_updated_list_random = []
            nb_updated_k_list_iam = []
            nb_updated_k_list_random = []
            g_best = []
            # for each alpha
            for alpha in alpha_range:
                print('\n-------------------------------------------------------\n')
                print('alpha =', alpha)
                time0 = time.time()
                dhat, ghat_list, dis_of_each_itr, nb_updated_iam, nb_updated_random, \
                    nb_updated_k_iam, nb_updated_k_random = \
                    preimage_iam_random_mix(Gn, [g1, g2],
                    [alpha, 1 - alpha], range(len(Gn), len(Gn) + 2), km, k, r_max, 
                    l_max, gkernel, epsilon=epsilon, InitIAMWithAllDk=InitIAMWithAllDk, 
                    InitRandomWithAllDk=InitRandomWithAllDk,
                    params_iam={'c_ei': c_ei, 'c_er': c_er, 'c_es': c_es, 
                                'ite_max': ite_max_iam, 'epsilon': epsilon_iam,
                                'removeNodes': removeNodes, 'connected': connected_iam},
                    params_ged={'ged_cost': ged_cost, 'ged_method': ged_method, 
                                'saveGXL': saveGXL})
                time_total = time.time() - time0 + time_km
                print('time: ', time_total)
                time_list.append(time_total)
                dis_ks_min_list.append(dhat)
                g_best.append(ghat_list)
                nb_updated_list_iam.append(nb_updated_iam)       
                nb_updated_list_random.append(nb_updated_random)
                nb_updated_k_list_iam.append(nb_updated_k_iam)       
                nb_updated_k_list_random.append(nb_updated_k_random) 
                
            # show best graphs and save them to file.
            for idx, item in enumerate(alpha_range):
                print('when alpha is', item, 'the shortest distance is', dis_ks_min_list[idx])
                print('one of the possible corresponding pre-images is')
                nx.draw(g_best[idx][0], labels=nx.get_node_attributes(g_best[idx][0], 'atom'), 
                        with_labels=True)
                plt.savefig('results/preimage_mix/mutag' + str(idx1) + '_' + str(idx2) 
                            + '_alpha' + str(item) + '.png', format="PNG")
#                plt.show()
                plt.clf()
#                print(g_best[idx][0].nodes(data=True))
#                print(g_best[idx][0].edges(data=True))
                
        #        for g in g_best[idx]:
        #            draw_Letter_graph(g, savepath='results/gk_iam/')
        ##            nx.draw_networkx(g)
        ##            plt.show()
        #            print(g.nodes(data=True))
        #            print(g.edges(data=True))
                    
            # compute the corresponding sod in graph space.
            for idx, item in enumerate(alpha_range):
                sod_tmp, _ = ged_median([g_best[0]], [g1, g2], ged_cost=ged_cost, 
                                             ged_method=ged_method, saveGXL=saveGXL)
                sod_gs_list.append(sod_tmp)
                sod_gs_min_list.append(np.min(sod_tmp))
                
            print('\nsods in graph space: ', sod_gs_list)
            print('\nsmallest sod in graph space for each alpha: ', sod_gs_min_list)  
            print('\nsmallest distance in kernel space for each alpha: ', dis_ks_min_list) 
            print('\nnumber of updates of the best graph for each alpha by IAM: ', nb_updated_list_iam)
            print('\nnumber of updates of the best graph for each alpha by random generation: ', 
                  nb_updated_list_random)
            print('\nnumber of updates of k nearest graphs for each alpha by IAM: ', 
                  nb_updated_k_list_iam)
            print('\nnumber of updates of k nearest graphs for each alpha by random generation: ', 
                  nb_updated_k_list_random)
            print('\ntimes:', time_list)
            nb_update_mat_iam[idx1, idx2] = nb_updated_list_iam[0]
            nb_update_mat_random[idx1, idx2] = nb_updated_list_random[0]
            
            str_fw = 'graphs %d and %d: %d times by IAM, %d times by random generation.\n' \
                % (idx1, idx2, nb_updated_list_iam[0], nb_updated_list_random[0])
            with open('results/preimage_mix/nb_updates.txt', 'r+') as file:
                content = file.read()
                file.seek(0, 0)
                file.write(str_fw + content)
    
###############################################################################

    
if __name__ == '__main__':
###############################################################################
# test on the combination of the two randomly chosen graphs. (the same as in the
# random pre-image paper.)
#    test_preimage_mix_2combination_all_pairs()
    
###############################################################################
# tests on different numbers of median-sets.
#    test_preimage_mix_median_nb()
    
###############################################################################
# tests on different values on grid of median-sets and k.
    test_preimage_mix_grid_k_median_nb()