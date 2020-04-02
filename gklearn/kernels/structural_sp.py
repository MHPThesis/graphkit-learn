#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Mar 30 11:59:57 2020

@author: ljia
"""
import sys
from itertools import product
# from functools import partial
from multiprocessing import Pool
from tqdm import tqdm
# import networkx as nx
import numpy as np
from gklearn.utils.parallel import parallel_gm, parallel_me
from gklearn.utils.utils import get_shortest_paths
from gklearn.kernels import GraphKernel


class StructuralSP(GraphKernel):
	
	def __init__(self, **kwargs):
		GraphKernel.__init__(self)
		self.__node_labels = kwargs.get('node_labels', [])
		self.__edge_labels = kwargs.get('edge_labels', [])
		self.__node_attrs = kwargs.get('node_attrs', [])
		self.__edge_attrs = kwargs.get('edge_attrs', [])
		self.__edge_weight = kwargs.get('edge_weight', None)
		self.__node_kernels = kwargs.get('node_kernels', None)
		self.__edge_kernels = kwargs.get('edge_kernels', None)
		self.__compute_method = kwargs.get('compute_method', 'naive')
		self.__ds_infos = kwargs.get('ds_infos', {})


	def _compute_gm_series(self):
		# get shortest paths of each graph in the graphs.
		splist = []
		if self._verbose >= 2:
			iterator = tqdm(self._graphs, desc='getting sp graphs', file=sys.stdout)
		else:
			iterator = self._graphs
		if self.__compute_method == 'trie':
			for g in iterator:
				splist.append(self.__get_sps_as_trie(g))
		else:
			for g in iterator:
				splist.append(get_shortest_paths(g, self.__edge_weight, self.__ds_infos['directed']))
		
		# compute Gram matrix.
		gram_matrix = np.zeros((len(self._graphs), len(self._graphs)))
		
		from itertools import combinations_with_replacement
		itr = combinations_with_replacement(range(0, len(self._graphs)), 2)
		if self._verbose >= 2:
			iterator = tqdm(itr, desc='calculating kernels', file=sys.stdout)
		else:
			iterator = itr
		if self.__compute_method == 'trie':
			for i, j in iterator:
				kernel = self.__ssp_do_trie(self._graphs[i], self._graphs[j], splist[i], splist[j])
				gram_matrix[i][j] = kernel
				gram_matrix[j][i] = kernel
		else:
			for i, j in iterator:
				kernel = self.__ssp_do_naive(self._graphs[i], self._graphs[j], splist[i], splist[j])
		#		if(kernel > 1):
		#			print("error here ")
				gram_matrix[i][j] = kernel
				gram_matrix[j][i] = kernel
				
		return gram_matrix
			
			
	def _compute_gm_imap_unordered(self):
		# get shortest paths of each graph in the graphs.
		splist = [None] * len(self._graphs)
		pool = Pool(self._n_jobs)
		itr = zip(self._graphs, range(0, len(self._graphs)))
		if len(self._graphs) < 100 * self._n_jobs:
			chunksize = int(len(self._graphs) / self._n_jobs) + 1
		else:
			chunksize = 100
		# get shortest path graphs of self._graphs
		if self.__compute_method == 'trie':
			get_sps_fun = self._wrapper_get_sps_trie	
		else:
			get_sps_fun = self._wrapper_get_sps_naive   
		if self.verbose >= 2:
			iterator = tqdm(pool.imap_unordered(get_sps_fun, itr, chunksize),
							desc='getting shortest paths', file=sys.stdout)
		else:
			iterator = pool.imap_unordered(get_sps_fun, itr, chunksize)
		for i, sp in iterator:
			splist[i] = sp
		pool.close()
		pool.join()
		
		# compute Gram matrix.
		gram_matrix = np.zeros((len(self._graphs), len(self._graphs)))

		def init_worker(spl_toshare, gs_toshare):
			global G_spl, G_gs
			G_spl = spl_toshare
			G_gs = gs_toshare	 
		if self.__compute_method == 'trie':	   
			do_fun = self.__wrapper_ssp_do_trie
		else:  
			do_fun = self._wrapper_ssp_do_naive  
		parallel_gm(do_fun, gram_matrix, self._graphs, init_worker=init_worker, 
							glbv=(splist, self._graphs), n_jobs=self._n_jobs, verbose=self._verbose)
			
		return gram_matrix
	
	
	def _compute_kernel_list_series(self, g1, g_list):
		# get shortest paths of g1 and each graph in g_list.
		sp1 = get_shortest_paths(g1, self.__edge_weight, self.__ds_infos['directed'])
		splist = []
		if self._verbose >= 2:
			iterator = tqdm(g_list, desc='getting sp graphs', file=sys.stdout)
		else:
			iterator = g_list
		if self.__compute_method == 'trie':
			for g in iterator:
				splist.append(self.__get_sps_as_trie(g))
		else:
			for g in iterator:
				splist.append(get_shortest_paths(g, self.__edge_weight, self.__ds_infos['directed']))
		
		# compute kernel list.
		kernel_list = [None] * len(g_list)
		if self._verbose >= 2:
			iterator = tqdm(range(len(g_list)), desc='calculating kernels', file=sys.stdout)
		else:
			iterator = range(len(g_list))
		if self.__compute_method == 'trie':
			for i in iterator:
				kernel = self.__ssp_do_trie(g1, g_list[i], sp1, splist[i])
				kernel_list[i] = kernel
		else:
			for i in iterator:
				kernel = self.__ssp_do_naive(g1, g_list[i], sp1, splist[i])
				kernel_list[i] = kernel
				
		return kernel_list
	
	
	def _compute_kernel_list_imap_unordered(self, g1, g_list):
		# get shortest paths of g1 and each graph in g_list.
		sp1 = get_shortest_paths(g1, self.__edge_weight, self.__ds_infos['directed'])
		splist = [None] * len(g_list)
		pool = Pool(self._n_jobs)
		itr = zip(g_list, range(0, len(g_list)))
		if len(g_list) < 100 * self._n_jobs:
			chunksize = int(len(g_list) / self._n_jobs) + 1
		else:
			chunksize = 100
		# get shortest path graphs of g_list
		if self.__compute_method == 'trie':
			get_sps_fun = self._wrapper_get_sps_trie	
		else:
			get_sps_fun = self._wrapper_get_sps_naive   
		if self.verbose >= 2:
			iterator = tqdm(pool.imap_unordered(get_sps_fun, itr, chunksize),
							desc='getting shortest paths', file=sys.stdout)
		else:
			iterator = pool.imap_unordered(get_sps_fun, itr, chunksize)
		for i, sp in iterator:
			splist[i] = sp
		pool.close()
		pool.join()
		
		# compute Gram matrix.
		kernel_list = [None] * len(g_list)

		def init_worker(sp1_toshare, spl_toshare, g1_toshare, gl_toshare):
			global G_sp1, G_spl, G_g1, G_gl
			G_sp1 = sp1_toshare
			G_spl = spl_toshare
			G_g1 = g1_toshare	 
			G_gl = gl_toshare	 
		if self.__compute_method == 'trie':	   
			do_fun = self.__wrapper_ssp_do_trie
		else: 	 
			do_fun = self._wrapper_kernel_list_do
		def func_assign(result, var_to_assign):	
			var_to_assign[result[0]] = result[1]
		itr = range(len(g_list))
		len_itr = len(g_list)
		parallel_me(do_fun, func_assign, kernel_list, itr, len_itr=len_itr,
			init_worker=init_worker, glbv=(sp1, splist, g1, g_list), method='imap_unordered', n_jobs=self._n_jobs, itr_desc='calculating kernels', verbose=self._verbose)
			
		return kernel_list
	
	
	def _wrapper_kernel_list_do(self, itr):
		return itr, self.__ssp_do_naive(G_g1, G_gl[itr], G_sp1, G_spl[itr])

	
	
	def _compute_single_kernel_series(self, g1, g2):
		sp1 = get_shortest_paths(g1, self.__edge_weight, self.__ds_infos['directed'])
		sp2 = get_shortest_paths(g2, self.__edge_weight, self.__ds_infos['directed'])
		if self.__compute_method == 'trie':
			kernel = self.__ssp_do_trie(g1, g2, sp1, sp2)
		else:
			kernel = self.__ssp_do_naive(g1, g2, sp1, sp2)
		return kernel			
		
	
	def _wrapper_get_sps_naive(self, itr_item):
		g = itr_item[0]
		i = itr_item[1]
		return i, get_shortest_paths(g, self.__edge_weight, self.__ds_infos['directed'])
	
	
	def __ssp_do_naive(self, g1, g2, spl1, spl2):
	
		kernel = 0
	
		# First, compute shortest path matrices, method borrowed from FCSP.
		vk_dict = self.__get_all_node_kernels(g1, g2)
		# Then, compute kernels between all pairs of edges, which is an idea of
		# extension of FCSP. It suits sparse graphs, which is the most case we
		# went though. For dense graphs, this would be slow.
		ek_dict = self.__get_all_edge_kernels(g1, g2)
	
		# compute graph kernels
		if vk_dict:
			if ek_dict:
				for p1, p2 in product(spl1, spl2):
					if len(p1) == len(p2):
						kpath = vk_dict[(p1[0], p2[0])]
						if kpath:
							for idx in range(1, len(p1)):
								kpath *= vk_dict[(p1[idx], p2[idx])] * \
									ek_dict[((p1[idx-1], p1[idx]),
											 (p2[idx-1], p2[idx]))]
								if not kpath:
									break
							kernel += kpath  # add up kernels of all paths
			else:
				for p1, p2 in product(spl1, spl2):
					if len(p1) == len(p2):
						kpath = vk_dict[(p1[0], p2[0])]
						if kpath:
							for idx in range(1, len(p1)):
								kpath *= vk_dict[(p1[idx], p2[idx])]
								if not kpath:
									break
							kernel += kpath  # add up kernels of all paths
		else:
			if ek_dict:
				for p1, p2 in product(spl1, spl2):
					if len(p1) == len(p2):
						if len(p1) == 0:
							kernel += 1
						else:
							kpath = 1
							for idx in range(0, len(p1) - 1):
								kpath *= ek_dict[((p1[idx], p1[idx+1]),
												  (p2[idx], p2[idx+1]))]
								if not kpath:
									break
							kernel += kpath  # add up kernels of all paths
			else:
				for p1, p2 in product(spl1, spl2):
					if len(p1) == len(p2):
						kernel += 1
		try:
			kernel = kernel / (len(spl1) * len(spl2))  # calculate mean average
		except ZeroDivisionError:
			print(spl1, spl2)
			print(g1.nodes(data=True))
			print(g1.edges(data=True))
			raise Exception
	
		# # ---- exact implementation of the Fast Computation of Shortest Path Kernel (FCSP), reference [2], sadly it is slower than the current implementation
		# # compute vertex kernel matrix
		# try:
		#	 vk_mat = np.zeros((nx.number_of_nodes(g1),
		#						nx.number_of_nodes(g2)))
		#	 g1nl = enumerate(g1.nodes(data=True))
		#	 g2nl = enumerate(g2.nodes(data=True))
		#	 for i1, n1 in g1nl:
		#		 for i2, n2 in g2nl:
		#			 vk_mat[i1][i2] = kn(
		#				 n1[1][node_label], n2[1][node_label],
		#				 [n1[1]['attributes']], [n2[1]['attributes']])
	
		#	 range1 = range(0, len(edge_w_g[i]))
		#	 range2 = range(0, len(edge_w_g[j]))
		#	 for i1 in range1:
		#		 x1 = edge_x_g[i][i1]
		#		 y1 = edge_y_g[i][i1]
		#		 w1 = edge_w_g[i][i1]
		#		 for i2 in range2:
		#			 x2 = edge_x_g[j][i2]
		#			 y2 = edge_y_g[j][i2]
		#			 w2 = edge_w_g[j][i2]
		#			 ke = (w1 == w2)
		#			 if ke > 0:
		#				 kn1 = vk_mat[x1][x2] * vk_mat[y1][y2]
		#				 kn2 = vk_mat[x1][y2] * vk_mat[y1][x2]
		#				 Kmatrix += kn1 + kn2
		return kernel
	
	
	def _wrapper_ssp_do_naive(self, itr):
		i = itr[0]
		j = itr[1]
		return i, j, self.__ssp_do_naive(G_gs[i], G_gs[j], G_spl[i], G_spl[j])
	
	
	def __get_all_node_kernels(self, g1, g2):
		# compute shortest path matrices, method borrowed from FCSP.
		vk_dict = {}  # shortest path matrices dict
		if len(self.__node_labels) > 0:
			# node symb and non-synb labeled
			if len(self.__node_attrs) > 0:
				kn = self.__node_kernels['mix']
				for n1, n2 in product(g1.nodes(data=True), g2.nodes(data=True)):
					n1_labels = [n1[1][nl] for nl in self.__node_labels]
					n2_labels = [n2[1][nl] for nl in self.__node_labels]
					n1_attrs = [n1[1][na] for na in self.__node_attrs]
					n2_attrs = [n2[1][na] for na in self.__node_attrs]
					vk_dict[(n1[0], n2[0])] = kn(n1_labels, n2_labels, n1_attrs, n2_attrs)
			# node symb labeled
			else:
				kn = self.__node_kernels['symb']
				for n1 in g1.nodes(data=True):
					for n2 in g2.nodes(data=True):
						n1_labels = [n1[1][nl] for nl in self.__node_labels]
						n2_labels = [n2[1][nl] for nl in self.__node_labels]
						vk_dict[(n1[0], n2[0])] = kn(n1_labels, n2_labels)
		else:
			# node non-synb labeled
			if len(self.__node_attrs) > 0:
				kn = self.__node_kernels['nsymb']
				for n1 in g1.nodes(data=True):
					for n2 in g2.nodes(data=True):
						n1_attrs = [n1[1][na] for na in self.__node_attrs]
						n2_attrs = [n2[1][na] for na in self.__node_attrs]
						vk_dict[(n1[0], n2[0])] = kn(n1_attrs, n2_attrs)
			# node unlabeled
			else:
				pass
			
		return vk_dict
	
	
	def __get_all_edge_kernels(self, g1, g2):
		# compute kernels between all pairs of edges, which is an idea of
		# extension of FCSP. It suits sparse graphs, which is the most case we
		# went though. For dense graphs, this would be slow.
		ek_dict = {}  # dict of edge kernels
		if len(self.__edge_labels) > 0:
			# edge symb and non-synb labeled
			if len(self.__edge_attrs) > 0:
				ke = self.__edge_kernels['mix']
				for e1, e2 in product(g1.edges(data=True), g2.edges(data=True)):
					e1_labels = [e1[2][el] for el in self.__edge_labels]
					e2_labels = [e2[2][el] for el in self.__edge_labels]
					e1_attrs = [e1[2][ea] for ea in self.__edge_attrs]
					e2_attrs = [e2[2][ea] for ea in self.__edge_attrs]
					ek_temp = ke(e1_labels, e2_labels, e1_attrs, e2_attrs)
					ek_dict[((e1[0], e1[1]), (e2[0], e2[1]))] = ek_temp
					ek_dict[((e1[1], e1[0]), (e2[0], e2[1]))] = ek_temp
					ek_dict[((e1[0], e1[1]), (e2[1], e2[0]))] = ek_temp
					ek_dict[((e1[1], e1[0]), (e2[1], e2[0]))] = ek_temp
			# edge symb labeled
			else:
				ke = self.__edge_kernels['symb']
				for e1 in g1.edges(data=True):
					for e2 in g2.edges(data=True):
						e1_labels = [e1[2][el] for el in self.__edge_labels]
						e2_labels = [e2[2][el] for el in self.__edge_labels]
						ek_temp = ke(e1_labels, e2_labels)
						ek_dict[((e1[0], e1[1]), (e2[0], e2[1]))] = ek_temp
						ek_dict[((e1[1], e1[0]), (e2[0], e2[1]))] = ek_temp
						ek_dict[((e1[0], e1[1]), (e2[1], e2[0]))] = ek_temp
						ek_dict[((e1[1], e1[0]), (e2[1], e2[0]))] = ek_temp
		else:
			# edge non-synb labeled
			if len(self.__edge_attrs) > 0:
				ke = self.__edge_kernels['nsymb']
				for e1 in g1.edges(data=True):
					for e2 in g2.edges(data=True):
						e1_attrs = [e1[2][ea] for ea in self.__edge_attrs]
						e2_attrs = [e2[2][ea] for ea in self.__edge_attrs]
						ek_temp = ke(e1_attrs, e2_attrs)
						ek_dict[((e1[0], e1[1]), (e2[0], e2[1]))] = ek_temp
						ek_dict[((e1[1], e1[0]), (e2[0], e2[1]))] = ek_temp
						ek_dict[((e1[0], e1[1]), (e2[1], e2[0]))] = ek_temp
						ek_dict[((e1[1], e1[0]), (e2[1], e2[0]))] = ek_temp
			# edge unlabeled
			else:
				pass
			
			return ek_dict