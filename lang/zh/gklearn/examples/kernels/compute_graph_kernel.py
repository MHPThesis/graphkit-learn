# -*- coding: utf-8 -*-
"""compute_graph_kernel.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/17Q2QCl9CAtDweGF8LiWnWoN2laeJqT0u

**This script demonstrates how to compute a graph kernel.**
---

**0.   Install `graphkit-learn`.**
"""

"""**1.   Get dataset.**"""

from gklearn.utils import Dataset

# Predefined dataset name, use dataset "MUTAG".
ds_name = 'MUTAG'

# Initialize a Dataset.
dataset = Dataset()
# Load predefined dataset "MUTAG".
dataset.load_predefined_dataset(ds_name)
len(dataset.graphs)

"""**2.  Compute graph kernel.**"""

from gklearn.kernels import PathUpToH

# Initailize parameters for graph kernel computation.
kernel_options = {'depth': 3,
			      		  'k_func': 'MinMax',
					        'compute_method': 'trie'
								 }

# Initialize graph kernel.
graph_kernel = PathUpToH(node_labels=dataset.node_labels, # list of node label names.
						 edge_labels=dataset.edge_labels, # list of edge label names.
						 ds_infos=dataset.get_dataset_infos(keys=['directed']), # dataset information required for computation.
						 **kernel_options, # options for computation.
						 )

print('done.')

import multiprocessing
import matplotlib.pyplot as plt

# Compute Gram matrix.
gram_matrix, run_time = graph_kernel.compute(dataset.graphs,
											 parallel='imap_unordered', # or None.
											 n_jobs=multiprocessing.cpu_count(), # number of parallel jobs.
											 normalize=True, # whether to return normalized Gram matrix.
											 verbose=2 # whether to print out results.
											 )
# Print results.
print()
print(gram_matrix)
print(run_time)
plt.imshow(gram_matrix)

import multiprocessing

# Compute grah kernels between a graph and a list of graphs.
kernel_list, run_time = graph_kernel.compute(dataset.graphs, # a list of graphs. 
                                             dataset.graphs[0], # a single graph.
											 parallel='imap_unordered', # or None.
											 n_jobs=multiprocessing.cpu_count(), # number of parallel jobs.
											 verbose=2 # whether to print out results.
                                            )
# Print results.
print()
print(kernel_list)
print(run_time)

import multiprocessing

# Compute a grah kernel between two graphs.
kernel, run_time = graph_kernel.compute(dataset.graphs[0], # a single graph. 
                                        dataset.graphs[1], # another single graph.
										verbose=2 # whether to print out results.
                                       )
# Print results.
print()
print(kernel)
print(run_time)