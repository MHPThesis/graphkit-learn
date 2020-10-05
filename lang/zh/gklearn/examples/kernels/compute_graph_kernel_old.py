# -*- coding: utf-8 -*-
"""compute_graph_kernel_v0.1.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/10jUz7-ahPiE_T1qvFrh2NvCVs1e47noj

**This script demonstrates how to compute a graph kernel.**
---

**0.   Install `graphkit-learn`.**
"""

"""**1.   Get dataset.**"""

from gklearn.utils.graphfiles import loadDataset

graphs, targets = loadDataset('../../../datasets/MUTAG/MUTAG_A.txt')

"""**2.  Compute graph kernel.**"""

from gklearn.kernels import untilhpathkernel

gram_matrix, run_time = untilhpathkernel(
	graphs, # The list of input graphs.
	depth=5, # The longest length of paths.
	k_func='MinMax', # Or 'tanimoto'.
	compute_method='trie', # Or 'naive'.
	n_jobs=1, # The number of jobs to run in parallel.
	verbose=True)