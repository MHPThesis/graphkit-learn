#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu May  5 09:42:30 2022

@author: ljia
"""
import sys
import multiprocessing
import time
import numpy as np
import networkx as nx

# from abc import ABC, abstractmethod
from sklearn.base import BaseEstimator # , TransformerMixin
from sklearn.utils.validation import check_is_fitted # check_X_y, check_array,
from sklearn.exceptions import NotFittedError

from gklearn.ged.model.distances import euclid_d
from gklearn.ged.util import pairwise_ged, get_nb_edit_operations
# from gklearn.utils import normalize_gram_matrix
from gklearn.utils import get_iters


class GEDModel(BaseEstimator): #, ABC):
	"""The graph edit distance model class compatible with `scikit-learn`.

	Attributes
    ----------
    _graphs : list
        Stores the input graphs on fit input data.
        Default format of the list objects is `NetworkX` graphs.
		**We don't guarantee that the input graphs remain unchanged during the
		computation.**

	References
	----------
	https://ysig.github.io/GraKeL/0.1a8/_modules/grakel/kernels/kernel.html#Kernel.
	"""

	def __init__(self,
			  ed_method='BIPARTITE',
			  edit_cost_fun='CONSTANT',
			  init_edit_cost_constants=[3, 3, 1, 3, 3, 1],
			  optim_method='init',
			  optim_options={'y_distance': euclid_d, 'mode': 'reg'},
			  node_labels=[],
			  edge_labels=[],
			  parallel=None,
			  n_jobs=None,
			  chunksize=None,
#			  normalize=True,
			  copy_graphs=True, # make sure it is a full deep copy. and faster!
			  verbose=2):
		"""`__init__` for `GEDModel` object."""
		# @todo: the default settings of the parameters are different from those in the self.compute method.
#		self._graphs = None
		self.ed_method = ed_method
		self.edit_cost_fun = edit_cost_fun
		self.init_edit_cost_constants = init_edit_cost_constants
		self.optim_method=optim_method
		self.optim_options=optim_options
		self.node_labels=node_labels
		self.edge_labels=edge_labels
		self.parallel = parallel
		self.n_jobs = n_jobs
		self.chunksize = chunksize
#		self.normalize = normalize
		self.copy_graphs = copy_graphs
		self.verbose = verbose
#		self._run_time = 0
#		self._gram_matrix = None
#		self._gram_matrix_unnorm = None


	##########################################################################
	# The following is the 1st paradigm to compute GED distance matrix, which is
	# compatible with `scikit-learn`.
	##########################################################################


	def fit(self, X, y=None):
		"""Fit a graph dataset for a transformer.

		Parameters
		----------
		X : iterable
			DESCRIPTION.

		y : None, optional
			There is no need of a target in a transformer, yet the `scikit-learn`
			pipeline API requires this parameter.

		Returns
		-------
		object
			Returns self.

		"""
#		self._is_tranformed = False

		# Clear any prior attributes stored on the estimator, # @todo: unless warm_start is used;
		self.clear_attributes()

		# Validate parameters for the transformer.
		self.validate_parameters()

		# Validate the input.
		self._graphs = self.validate_input(X)
		if y is not None:
 			self._targets = y
 			# self._targets = self.validate_input(y)

#		self._X = X
#		self._kernel = self._get_kernel_instance()

		# Return the transformer.
		return self


	def transform(self, X=None, return_dm_train=False):
		"""Compute the graph kernel matrix between given and fitted data.

		Parameters
		----------
		X : TYPE
			DESCRIPTION.

		Raises
		------
		ValueError
			DESCRIPTION.

		Returns
		-------
		None.

		"""
		# If `return_dm_train`, return the fitted GED distance matrix of training data.
		if return_dm_train:
			check_is_fitted(self, '_dm_train')
			self._is_transformed = True
			return self._dm_train # @todo: copy or not?

		# Check if method "fit" had been called.
		check_is_fitted(self, '_graphs')

		# Validate the input.
		Y = self.validate_input(X)

		# Transform: compute the graph kernel matrix.
		dis_matrix = self.compute_distance_matrix(Y)
		self._Y = Y

		# Self transform must appear before the diagonal call on normilization.
		self._is_transformed = True
# 		if self.normalize:
# 			X_diag, Y_diag = self.diagonals()
# 			old_settings = np.seterr(invalid='raise') # Catch FloatingPointError: invalid value encountered in sqrt.
# 			try:
# 				kernel_matrix /= np.sqrt(np.outer(Y_diag, X_diag))
# 			except:
# 				raise
# 			finally:
# 				np.seterr(**old_settings)

		return dis_matrix


	def fit_transform(self, X, y=None, save_dm_train=False):
		"""Fit and transform: compute GED distance matrix on the same data.

		Parameters
		----------
		X : list of graphs
			Input graphs.

		Returns
		-------
		dis_matrix : numpy array, shape = [len(X), len(X)]
			The distance matrix of X.

		"""
		self.fit(X, y)

		# Compute edit cost constants.
		self.compute_edit_costs()

		# Transform: compute Gram matrix.
		dis_matrix = self.compute_distance_matrix()

#		# Normalize.
#		if self.normalize:
#			self._X_diag = np.diagonal(gram_matrix).copy()
#			old_settings = np.seterr(invalid='raise') # Catch FloatingPointError: invalid value encountered in sqrt.
#			try:
#				gram_matrix /= np.sqrt(np.outer(self._X_diag, self._X_diag))
#			except:
#				raise
#			finally:
#				np.seterr(**old_settings)

		if save_dm_train:
			self._dm_train = dis_matrix

		return dis_matrix


	def get_params(self):
		pass


	def set_params(self):
		pass


	def clear_attributes(self): # @todo: update
#		if hasattr(self, '_X_diag'):
#			delattr(self, '_X_diag')
		if hasattr(self, '_graphs'):
			delattr(self, '_graphs')
		if hasattr(self, '_Y'):
			delattr(self, '_Y')
		if hasattr(self, '_run_time'):
			delattr(self, '_run_time')


	def validate_parameters(self):
		"""Validate all parameters for the transformer.

		Returns
		-------
		None.

		"""
		if self.parallel is not None and self.parallel != 'imap_unordered':
			raise ValueError('Parallel mode is not set correctly.')

		if self.parallel == 'imap_unordered' and self.n_jobs is None:
			self.n_jobs = multiprocessing.cpu_count()


	def validate_input(self, X):
		"""Validate the given input and raise errors if it is invalid.

		Parameters
		----------
		X : list
			The input to check. Should be a list of graph.

		Raises
		------
		ValueError
			Raise if the input is not correct.

		Returns
		-------
		X : list
			The input. A list of graph.

		"""
		if X is None:
			raise ValueError('Please add graphs before computing.')
		elif not isinstance(X, list):
			raise ValueError('Cannot detect graphs. The input must be a list.')
		elif len(X) == 0:
			raise ValueError('The graph list given is empty. No computation will be performed.')

		return X


	def compute_distance_matrix(self, Y=None):
		"""Compute the distance matrix between a given target graphs (Y) and
		the fitted graphs (X / self._graphs) or the distance matrix for the fitted
		graphs (X / self._graphs).

		Parameters
		----------
		Y : list of graphs, optional
			The target graphs. The default is None. If None kernel is computed
			between X and itself.

		Returns
		-------
		kernel_matrix : numpy array, shape = [n_targets, n_inputs]
			The computed kernel matrix.

		"""
		if Y is None:
			# Compute Gram matrix for self._graphs (X).
			dis_matrix = self._compute_X_distance_matrix()
#			self._gram_matrix_unnorm = np.copy(self._gram_matrix)

		else:
			# Compute kernel matrix between Y and self._graphs (X).
			start_time = time.time()

			if self.parallel == 'imap_unordered':
				dis_matrix = self._compute_distance_matrix_imap_unordered(Y)

			elif self.parallel is None:
				Y_copy = ([g.copy() for g in Y] if self.copy_graphs else Y)
				graphs_copy = ([g.copy() for g in self._graphs] if self.copy_graphs else self._graphs)
				dis_matrix = self._compute_distance_matrix_series(Y_copy, graphs_copy)

			self._run_time = time.time() - start_time
			if self.verbose:
				print('Distance matrix of size (%d, %d) built in %s seconds.'
				  % (len(Y), len(self._graphs), self._run_time))

		return dis_matrix


	def _compute_distance_matrix_series(self, X, Y):
		"""Compute the GED distance matrix between two sets of graphs (X and Y)
		without parallelization.

		Parameters
		----------
		X, Y : list of graphs
			The input graphs.

		Returns
		-------
		dis_matrix : numpy array, shape = [n_X, n_Y]
			The computed distance matrix.

		"""
		dis_matrix = np.zeros((len(X), len(Y)))

		for i_x, g_x in enumerate(X):
			for i_y, g_y in enumerate(Y):
				dis_matrix[i_x, i_y], _ = self.compute_ged(g_x, g_y)

		return dis_matrix


	def _compute_kernel_matrix_imap_unordered(self, Y):
		"""Compute the kernel matrix between a given target graphs (Y) and
		the fitted graphs (X / self._graphs) using imap unordered parallelization.

		Parameters
		----------
		Y : list of graphs, optional
			The target graphs.

		Returns
		-------
		kernel_matrix : numpy array, shape = [n_targets, n_inputs]
			The computed kernel matrix.

		"""
		raise Exception('Parallelization for kernel matrix is not implemented.')


	def diagonals(self):
		"""Compute the kernel matrix diagonals of the fit/transformed data.

		Returns
		-------
        X_diag : numpy array
            The diagonal of the kernel matrix between the fitted data.
            This consists of each element calculated with itself.

        Y_diag : numpy array
            The diagonal of the kernel matrix, of the transform.
            This consists of each element calculated with itself.

		"""
		# Check if method "fit" had been called.
		check_is_fitted(self, ['_graphs'])

		# Check if the diagonals of X exist.
		try:
			check_is_fitted(self, ['_X_diag'])
		except NotFittedError:
			# Compute diagonals of X.
			self._X_diag = np.empty(shape=(len(self._graphs),))
			graphs = ([g.copy() for g in self._graphs] if self.copy_graphs else self._graphs)
			for i, x in enumerate(graphs):
				self._X_diag[i] = self.pairwise_kernel(x, x) # @todo: parallel?

		try:
            # If transform has happened, return both diagonals.
			check_is_fitted(self, ['_Y'])
			self._Y_diag = np.empty(shape=(len(self._Y),))
			Y = ([g.copy() for g in self._Y] if self.copy_graphs else self._Y)
			for (i, y) in enumerate(Y):
				self._Y_diag[i] = self.pairwise_kernel(y, y) # @todo: parallel?

			return self._X_diag, self._Y_diag
		except NotFittedError:
            # Else just return both X_diag
			return self._X_diag


#	@abstractmethod
	def pairwise_distance(self, x, y):
		"""Compute pairwise kernel between two graphs.

		Parameters
		----------
		x, y : NetworkX Graph.
			Graphs bewteen which the kernel is computed.

		Returns
		-------
		kernel: float
			The computed kernel.

#		Notes
#		-----
#		This method is abstract and must be implemented by a subclass.

		"""
		raise NotImplementedError('Pairwise kernel computation is not implemented!')



	def compute_edit_costs(self, Y=None, Y_targets=None):
		"""Compute edit cost constants. When optimizing method is `fiited`,
		apply Jia2021's metric learning method by using a given target graphs (Y)
		the fitted graphs (X / self._graphs).

		Parameters
		----------
		Y : TYPE, optional
			DESCRIPTION. The default is None.

		Returns
		-------
		None.

		"""
		# Get or compute.
		if self.optim_method == 'random':
			self._edit_cost_constants = np.random.rand(6)

		elif self.optim_method == 'init':
			self._edit_cost_constants = self.init_edit_cost_constants


		elif self.optim_method == 'expert':
			self._edit_cost_constants = [3, 3, 1, 3, 3, 1]


		elif self.optim_method == 'fitted': # Jia2021 method
			# Get proper inputs.
			if Y is None:
				check_is_fitted(self, ['_graphs'])
				check_is_fitted(self, ['_targets'])
				graphs = ([g.copy() for g in self._graphs] if self.copy_graphs else self._graphs)
				targets = self._targets
			else:
				graphs = ([g.copy() for g in Y] if self.copy_graphs else Y)
				targets = Y_targets

			# Get optimization options.
			node_labels = self.node_labels
			edge_labels = self.edge_labels
			unlabeled = (len(node_labels) == 0 and len(edge_labels) == 0)
			from gklearn.ged.model.optim_costs import compute_optimal_costs
			self._edit_cost_constants = compute_optimal_costs(
				graphs, targets,
				node_labels=node_labels, edge_labels=edge_labels,
				unlabeled=unlabeled, ed_method=self.ed_method,
				verbose=(self.verbose >= 2),
				**self.optim_options)


	##########################################################################
	# The following is the 2nd paradigm to compute kernel matrix. It is
	# simplified and not compatible with `scikit-learn`.
	##########################################################################


#	def compute(self, *graphs, **kwargs):
#		self.parallel = kwargs.get('parallel', 'imap_unordered')
#		self.n_jobs = kwargs.get('n_jobs', multiprocessing.cpu_count())
#		self.normalize = kwargs.get('normalize', True)
#		self.verbose = kwargs.get('verbose', 2)
#		self.copy_graphs = kwargs.get('copy_graphs', True)
#		self.save_unnormed = kwargs.get('save_unnormed', True)
#		self.validate_parameters()

#		# If the inputs is a list of graphs.
#		if len(graphs) == 1:
#			if not isinstance(graphs[0], list):
#				raise Exception('Cannot detect graphs.')
#			elif len(graphs[0]) == 0:
#				raise Exception('The graph list given is empty. No computation was performed.')
#			else:
#				if self.copy_graphs:
#					self._graphs = [g.copy() for g in graphs[0]] # @todo: might be very slow.
#				else:
#					self._graphs = graphs
#				self._gram_matrix = self._compute_gram_matrix()

#				if self.save_unnormed:
#					self._gram_matrix_unnorm = np.copy(self._gram_matrix)
#				if self.normalize:
#					self._gram_matrix = normalize_gram_matrix(self._gram_matrix)
#				return self._gram_matrix, self._run_time

#		elif len(graphs) == 2:
#			# If the inputs are two graphs.
#			if self.is_graph(graphs[0]) and self.is_graph(graphs[1]):
#				if self.copy_graphs:
#					G0, G1 = graphs[0].copy(), graphs[1].copy()
#				else:
#					G0, G1 = graphs[0], graphs[1]
#				kernel = self._compute_single_kernel(G0, G1)
#				return kernel, self._run_time

#			# If the inputs are a graph and a list of graphs.
#			elif self.is_graph(graphs[0]) and isinstance(graphs[1], list):
#				if self.copy_graphs:
#					g1 = graphs[0].copy()
#					g_list = [g.copy() for g in graphs[1]]
#					kernel_list = self._compute_kernel_list(g1, g_list)
#				else:
#					kernel_list = self._compute_kernel_list(graphs[0], graphs[1])
#				return kernel_list, self._run_time

#			elif isinstance(graphs[0], list) and self.is_graph(graphs[1]):
#				if self.copy_graphs:
#					g1 = graphs[1].copy()
#					g_list = [g.copy() for g in graphs[0]]
#					kernel_list = self._compute_kernel_list(g1, g_list)
#				else:
#					kernel_list = self._compute_kernel_list(graphs[1], graphs[0])
#				return kernel_list, self._run_time

#			else:
#				raise Exception('Cannot detect graphs.')

#		elif len(graphs) == 0 and self._graphs is None:
#			raise Exception('Please add graphs before computing.')

#		else:
#			raise Exception('Cannot detect graphs.')


#	def normalize_gm(self, gram_matrix):
#		import warnings
#		warnings.warn('gklearn.kernels.graph_kernel.normalize_gm will be deprecated, use gklearn.utils.normalize_gram_matrix instead', DeprecationWarning)

#		diag = gram_matrix.diagonal().copy()
#		for i in range(len(gram_matrix)):
#			for j in range(i, len(gram_matrix)):
#				gram_matrix[i][j] /= np.sqrt(diag[i] * diag[j])
#				gram_matrix[j][i] = gram_matrix[i][j]
#		return gram_matrix


#	def compute_distance_matrix(self):
#		if self._gram_matrix is None:
#			raise Exception('Please compute the Gram matrix before computing distance matrix.')
#		dis_mat = np.empty((len(self._gram_matrix), len(self._gram_matrix)))
#		for i in range(len(self._gram_matrix)):
#			for j in range(i, len(self._gram_matrix)):
#				dis = self._gram_matrix[i, i] + self._gram_matrix[j, j] - 2 * self._gram_matrix[i, j]
#				if dis < 0:
#					if dis > -1e-10:
#						dis = 0
#					else:
#						raise ValueError('The distance is negative.')
#				dis_mat[i, j] = np.sqrt(dis)
#				dis_mat[j, i] = dis_mat[i, j]
#		dis_max = np.max(np.max(dis_mat))
#		dis_min = np.min(np.min(dis_mat[dis_mat != 0]))
#		dis_mean = np.mean(np.mean(dis_mat))
#		return dis_mat, dis_max, dis_min, dis_mean


	def _compute_X_distance_matrix(self):
		start_time = time.time()

		if self.parallel == 'imap_unordered':
			dis_matrix = self._compute_X_dm_imap_unordered()
		elif self.parallel is None:
			graphs = ([g.copy() for g in self._graphs] if self.copy_graphs else self._graphs)
			dis_matrix = self._compute_X_dm_series(graphs)
		else:
			raise Exception('Parallel mode is not set correctly.')

		self._run_time = time.time() - start_time
		if self.verbose:
			print('Distance matrix of size %d built in %s seconds.'
			  % (len(self._graphs), self._run_time))

		return dis_matrix


	def _compute_X_dm_series(self, graphs):
		N = len(graphs)
		dis_matrix = np.zeros((N, N))

		for i, G1 in get_iters(enumerate(graphs), desc='Computing distance matrix', file=sys.stdout, verbose=(self.verbose >= 2)):
			for j, G2 in enumerate(graphs[i+1:], i+1):
				dis_matrix[i, j], _ = self.compute_ged(G1, G2)
				dis_matrix[j, i] = dis_matrix[i, j]
		return dis_matrix


	def _compute_X_dm_imap_unordered(self, graphs):
		pass


	def compute_ged(self, Gi, Gj, **kwargs):
		"""
		Compute GED between two graph according to edit_cost.
		"""
		ged_options = {'edit_cost': self.edit_cost_fun,
				 'method': self.ed_method,
				 'edit_cost_constants': self._edit_cost_constants}
		dis, pi_forward, pi_backward = pairwise_ged(Gi, Gj, ged_options, repeats=10)
		n_eo_tmp = get_nb_edit_operations(Gi, Gj, pi_forward, pi_backward,
									 edit_cost=self.edit_cost_fun,
									 node_labels=self.node_labels,
									 edge_labels=self.edge_labels)
		return dis, n_eo_tmp


# 	def _compute_kernel_list(self, g1, g_list):
# 		start_time = time.time()

# 		if self.parallel == 'imap_unordered':
# 			kernel_list = self._compute_kernel_list_imap_unordered(g1, g_list)
# 		elif self.parallel is None:
# 			kernel_list = self._compute_kernel_list_series(g1, g_list)
# 		else:
# 			raise Exception('Parallel mode is not set correctly.')

# 		self._run_time = time.time() - start_time
# 		if self.verbose:
# 			print('Graph kernel bewteen a graph and a list of %d graphs built in %s seconds.'
# 			  % (len(g_list), self._run_time))

# 		return kernel_list


# 	def _compute_kernel_list_series(self, g1, g_list):
# 		pass


# 	def _compute_kernel_list_imap_unordered(self, g1, g_list):
# 		pass


# 	def _compute_single_kernel(self, g1, g2):
# 		start_time = time.time()

# 		kernel = self._compute_single_kernel_series(g1, g2)

# 		self._run_time = time.time() - start_time
# 		if self.verbose:
# 			print('Graph kernel bewteen two graphs built in %s seconds.' % (self._run_time))

# 		return kernel


# 	def _compute_single_kernel_series(self, g1, g2):
# 		pass


	def is_graph(self, graph):
		if isinstance(graph, nx.Graph):
			return True
		if isinstance(graph, nx.DiGraph):
			return True
		if isinstance(graph, nx.MultiGraph):
			return True
		if isinstance(graph, nx.MultiDiGraph):
			return True
		return False


	@property
	def graphs(self):
		return self._graphs


#	@property
#	def parallel(self):
#		return self.parallel


#	@property
#	def n_jobs(self):
#		return self.n_jobs


#	@property
#	def verbose(self):
#		return self.verbose


#	@property
#	def normalize(self):
#		return self.normalize


	@property
	def run_time(self):
		return self._run_time


	@property
	def dis_matrix(self):
		return self._dis_matrix

	@dis_matrix.setter
	def dis_matrix(self, value):
		self._dis_matrix = value


# 	@property
# 	def gram_matrix_unnorm(self):
# 		return self._gram_matrix_unnorm

# 	@gram_matrix_unnorm.setter
# 	def gram_matrix_unnorm(self, value):
# 		self._gram_matrix_unnorm = value