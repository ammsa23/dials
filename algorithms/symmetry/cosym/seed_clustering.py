from __future__ import absolute_import, division, print_function

import logging
logger = logging.getLogger(__name__)

import math

import numpy as np
from scipy.cluster import hierarchy
import scipy.spatial.distance as ssd
from sklearn.neighbors import NearestNeighbors
from sklearn import metrics

from libtbx import Auto
from scitbx.array_family import flex
from dials.algorithms.symmetry.cosym import plot_matrix, plot_dendrogram

class seed_clustering(object):

  def __init__(self, coordinates, n_datasets, n_sym_ops,
               min_silhouette_score, n_clusters=Auto, plot_prefix=None):
    self.coords = coordinates

    self.cluster_labels = self.label_clusters_first_pass(n_datasets, n_sym_ops)

    if flex.max(self.cluster_labels) == 0:
      # assume single cluster
      return

    dist_mat, linkage_matrix = self.hierarchical_clustering()
    self.cluster_labels, threshold = self.silhouette_analysis(
      self.cluster_labels, linkage_matrix, 
      n_clusters=n_clusters,
      min_silhouette_score=min_silhouette_score,
      plot_prefix=plot_prefix)

    if plot_prefix is not None:
      plot_matrix(
        1 - ssd.squareform(dist_mat), linkage_matrix,
        '%sseed_clustering_cos_angle_matrix.png' % plot_prefix,
        color_threshold=threshold)
      plot_dendrogram(
        linkage_matrix,
        '%sseed_clustering_cos_angle_dendrogram.png' % plot_prefix,
        color_threshold=threshold)

  def label_clusters_first_pass(self, n_datasets, n_sym_ops):
    """Labels points into clusters such that cluster contains exactly one copy
       of each dataset.
    """

    # initialise cluster labels: -1 signifies doesn't belong to a cluster
    cluster_labels = flex.int(self.coords.all()[0], -1)
    X_orig = self.coords.as_numpy_array()

    cluster_id = 0
    while cluster_labels.count(-1) > 0:
      dataset_ids = (flex.int_range(n_datasets * n_sym_ops) % n_datasets
                     ).as_numpy_array()
      coord_ids = flex.int_range(dataset_ids.size).as_numpy_array()

      # select only those points that don't already belong to a cluster
      sel = np.where(cluster_labels == -1)
      X = X_orig[sel]
      dataset_ids = dataset_ids[sel]
      coord_ids = coord_ids[sel]

      # choose a high density point as seed for cluster
      nbrs = NearestNeighbors(
        n_neighbors=min(11, len(X)), algorithm='brute', metric='cosine').fit(X)
      distances, indices = nbrs.kneighbors(X)
      average_distance = flex.double([dist[1:].mean() for dist in distances])
      i = flex.min_index(average_distance)

      d_id = dataset_ids[i]
      cluster = np.array([coord_ids[i]])
      cluster_dataset_ids = np.array([d_id])
      xis = np.array([X[i]])

      for j in range(n_datasets-1):
        # select only those rows that don't correspond to a dataset already
        # present in current cluster
        sel = np.where(dataset_ids != d_id)
        X = X[sel]
        dataset_ids = dataset_ids[sel]
        coord_ids = coord_ids[sel]

        assert len(X) > 0

        # Find nearest neighbour in cosine-space to the current cluster centroid
        nbrs = NearestNeighbors(
          n_neighbors=min(1, len(X)), algorithm='brute', metric='cosine').fit(X)
        distances, indices = nbrs.kneighbors([xis.mean(axis=0)])
        k = indices[0][0]
        d_id = dataset_ids[k]
        cluster = np.append(cluster, coord_ids[k])
        cluster_dataset_ids = np.append(cluster_dataset_ids, d_id)
        xis = np.append(xis, [X[k]], axis=0)

      # label this cluster
      cluster_labels.set_selected(flex.size_t(cluster.tolist()), cluster_id)
      cluster_id += 1
    return cluster_labels

  def hierarchical_clustering(self):
    cluster_centroids = []
    X = self.coords.as_numpy_array()
    for i in set(self.cluster_labels):
      sel = self.cluster_labels == i
      cluster_centroids.append(
        X[(self.cluster_labels == i).iselection().as_numpy_array()].mean(axis=0))

    # hierarchical clustering of cluster centroids, using cosine metric
    dist_mat = ssd.pdist(cluster_centroids, metric='cosine')
    return dist_mat, hierarchy.linkage(dist_mat, method='average')

  def silhouette_analysis(self, cluster_labels, linkage_matrix,
                          n_clusters, min_silhouette_score,
                          plot_prefix=None):
    """
    Compare valid equal-sized clustering using silhouette scores

    https://en.wikipedia.org/wiki/Silhouette_(clustering)
    http://scikit-learn.org/stable/auto_examples/cluster/plot_kmeans_silhouette_analysis.html
    """

    eps = 1e-6
    X = self.coords.as_numpy_array()

    cluster_labels_input = cluster_labels
    distances = linkage_matrix[::, 2]
    distances = np.insert(distances, 0, 0)
    silhouette_scores = flex.double()
    thresholds = flex.double()
    threshold_n_clusters = flex.size_t()
    for threshold in distances[1:]:
      cluster_labels = cluster_labels_input.deep_copy()
      labels = hierarchy.fcluster(
        linkage_matrix, threshold-eps, criterion='distance').tolist()
      counts = [labels.count(l) for l in set(labels)]
      if len(set(counts)) > 1:
        # only equal-sized clusters are valid
        continue

      n = len(set(labels))
      if n == 1: continue
      for i in range(len(labels)):
        cluster_labels.set_selected(cluster_labels_input == i, int(labels[i]-1))
      silhouette_avg = metrics.silhouette_score(
        X, cluster_labels.as_numpy_array(), metric='cosine')
      # Compute the silhouette scores for each sample
      sample_silhouette_values = metrics.silhouette_samples(
        X, cluster_labels.as_numpy_array(), metric='cosine')
      silhouette_avg = sample_silhouette_values.mean()
      silhouette_scores.append(silhouette_avg)
      thresholds.append(threshold)
      threshold_n_clusters.append(n)

      count_negative = (sample_silhouette_values < 0).sum()
      logger.info('Clustering:')
      logger.info('  Number of clusters: %i' % n)
      logger.info('  Threshold score: %.3f (%.1f deg)' % (
        threshold, math.degrees(math.acos(1-threshold))))
      logger.info('  Silhouette score: %.3f' % silhouette_avg)
      logger.info('  -ve silhouette scores: %.1f%%' % (
        100 * count_negative/sample_silhouette_values.size))

      if plot_prefix is not None:
        plot_silhouette(
          sample_silhouette_values, cluster_labels.as_numpy_array(),
          file_name='%ssilhouette_%i.png' % (plot_prefix, n))

    if n_clusters is Auto:
      idx = flex.max_index(silhouette_scores)
    else:
      idx = flex.first_index(threshold_n_clusters, n_clusters)
      if idx is None:
        raise Sorry('No valid clustering with %i clusters'
                    % n_clusters)

    if (n_clusters is Auto and
        silhouette_scores[idx] < min_silhouette_score):
      # assume single cluster
      cluster_labels = flex.int(cluster_labels.size(), 0)
    else:
      threshold = thresholds[idx] - eps
      labels = hierarchy.fcluster(
        linkage_matrix, threshold, criterion='distance')
      cluster_labels = flex.double(cluster_labels.size(), -1)
      for i in range(len(labels)):
        cluster_labels.set_selected(cluster_labels_input == i, labels[i]-1)

    return cluster_labels, threshold

def plot_silhouette(sample_silhouette_values, cluster_labels, file_name):
  from matplotlib import pyplot as plt

  fig = plt.figure()
  ax1 = fig.gca()
  y_lower = 10

  n_clusters = len(set(cluster_labels))
  silhouette_avg = sample_silhouette_values.mean()
  for i in range(n_clusters):
    # Aggregate the silhouette scores for samples belonging to
    # cluster i, and sort them
    ith_cluster_silhouette_values = \
      sample_silhouette_values[cluster_labels == i]

    ith_cluster_silhouette_values.sort()

    size_cluster_i = ith_cluster_silhouette_values.shape[0]
    y_upper = y_lower + size_cluster_i

    color = plt.cm.Spectral(float(i) / n_clusters)
    ax1.fill_betweenx(np.arange(y_lower, y_upper),
                      0, ith_cluster_silhouette_values,
                      facecolor=color, edgecolor=color, alpha=0.7)

    # Label the silhouette plots with their cluster numbers at the middle
    ax1.text(-0.05, y_lower + 0.5 * size_cluster_i, str(i))

    # Compute the new y_lower for next plot
    y_lower = y_upper + 10  # 10 for the 0 samples

  ax1.set_title("The silhouette plot for the various clusters.")
  ax1.set_xlabel("The silhouette coefficient values")
  ax1.set_ylabel("Cluster label")

  # The vertical line for average silhouette score of all the values
  ax1.axvline(x=silhouette_avg, color="red", linestyle="--")

  ax1.set_yticks([])  # Clear the yaxis labels / ticks
  ax1.set_xticks([-0.1, 0, 0.2, 0.4, 0.6, 0.8, 1])
  fig.savefig(file_name)
  plt.close(fig)
