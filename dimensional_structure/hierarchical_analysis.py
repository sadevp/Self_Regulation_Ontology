# imports
import argparse
from dimensional_structure.utils import (
        distcorr, hierarchical_cluster, save_figure
        )
from glob import glob
from itertools import combinations
import matplotlib.pyplot as plt
import numpy as np
from os import makedirs, path, remove
import pandas as pd
import pickle
from scipy.spatial.distance import pdist, squareform
import seaborn as sns
from selfregulation.utils.plot_utils import dendroheatmap
from sklearn.decomposition import PCA
from sklearn.metrics import adjusted_mutual_info_score, adjusted_rand_score
from sklearn.preprocessing import scale
import subprocess

# parse arguments
parser = argparse.ArgumentParser()
parser.add_argument('-rerun', action='store_true')
parser.add_argument('-no_plot', action='store_true')
args = parser.parse_args()

rerun = args.rerun
plot_on = not args.no_plot

# ****************************************************************************
# Laad Data
# ****************************************************************************
datafile = 'Complete_10-08-2017'
plot_file = path.join('Plots', datafile, 'HCA')
output_file = path.join('Output', datafile)
makedirs(plot_file, exist_ok = True)
makedirs(output_file, exist_ok = True)

results = pickle.load(open(path.join(output_file, 'EFA_results.pkl'),'rb'))
results['HCA'] = results.get('HCA', {})
data = results['data']


# ****************************************************************************
# Analysis
# ****************************************************************************

if ('clustering_metric-distcorr_input-data' not in results['HCA'].keys() 
    or rerun==True):
    output = hierarchical_cluster(data.T, pdist_kws={'metric': distcorr})
    results['HCA']['clustering_metric-distcorr_input-data'] = output



metrics = [(i[9:], int(results['EFA'][i])) 
            for i in results['EFA'].keys() if 'c_metric' in i]
if ('clustering_metric-distcorr_input-EFA%s' % metrics[-1][1]
    not in results['HCA'].keys()  or rerun==True):
    for metric, c in metrics:
        loadings = results['EFA']['factor_tree'][c]
        output = hierarchical_cluster(loadings, pdist_kws={'metric': distcorr})
        results['HCA']['clustering_metric-distcorr_input-EFA%s' % c] = output
        
# save more results
pickle.dump(results, open(path.join(output_file, 'EFA_results.pkl'),'wb'))


# ****************************************************************************
# Plotting
# ****************************************************************************  
if plot_on:
    
    # get all clustering solutions
    clusterings = [(k.split('-')[-1] ,v) for k,v in 
                    results['HCA'].items() if 'clustering' in k]
    
    # plot dendrogram heatmaps
    for name, clustering in clusterings:
        filename = path.join(plot_file, 
                             'clustering_metric-distcorr_input-%s.png' % name)
        fig = dendroheatmap(clustering['linkage'], clustering['distance_df'], 
                            clustering['clustering']['labels'],
                            figsize=(50,50),  filename = filename)
    
    # plot cluster agreement across embedding spaces
    names = [i[0] for i in clusterings]
    cluster_similarity = np.zeros((len(clusterings), len(clusterings)))
    cluster_similarity = pd.DataFrame(cluster_similarity, 
                                     index=names,
                                     columns=names)
    for clustering1, clustering2 in combinations(clusterings, 2):
        clusters1 = clustering1[1]['clustering']['labels']
        clusters2 = clustering2[1]['clustering']['labels']
        rand_score = adjusted_rand_score(clusters1, clusters2)
        MI_score = adjusted_mutual_info_score(clusters1, clusters2)
        cluster_similarity.loc[clustering1[0], clustering2[0]] = rand_score
        cluster_similarity.loc[clustering2[0], clustering1[0]] = MI_score
    
    with sns.plotting_context(context='notebook', font_scale=1.4):
        fig = plt.figure(figsize = (12,12))
        sns.heatmap(cluster_similarity, square=True)
        plt.title('Cluster Similarity: TRIL: Adjusted MI, TRIU: Adjusted Rand',
                  y=1.02)
    save_figure(fig, path.join(plot_file, 'cluster_similarity_across_measures.pdf'))

    # assess relationship between two measurements
    rand_scores = cluster_similarity.values[np.triu_indices_from(cluster_similarity, k=1)]
    MI_scores = cluster_similarity.T.values[np.triu_indices_from(cluster_similarity, k=1)]
    score_consistency = np.corrcoef(rand_scores, MI_scores)[0,1]
    print('Correlation between measures of cluster consistency: %.2f' \
          % score_consistency)
    
    # plot distance correlation for factor solutions in the same order as the
    # clustered solution
    clustered_df = results['HCA']['clustering_metric-distcorr_input-data']['clustered_df']
    cluster_order = clustered_df.index
    
    fig = plt.figure(figsize=(12,12))
    sns.heatmap(clustered_df, square=True, xticklabels=False,
                yticklabels=False, cbar=False)
    plt.title('Data', fontsize=20, y=1.02)
    fig.savefig(path.join(plot_file,  'heatmap_metric-distcorr.png'), 
                bbox_inches='tight')
    factor_distances = {}
    for c, loadings in results['EFA']['factor_tree'].items():
        if c>2:
            loadings = loadings.copy().loc[cluster_order, :]
            distances = squareform(pdist(loadings, metric=distcorr))
            distances = pd.DataFrame(distances, 
                                     index=loadings.index, 
                                     columns=loadings.index)
            factor_distances[c] = squareform(distances)
            # plot
            fig = plt.figure(figsize=(12,12))
            sns.heatmap(distances, square=True, xticklabels=False,
                yticklabels=False, cbar=False)
            plt.title('EFA %s' % c, fontsize=20, y=1.02)
            fig.savefig(path.join(plot_file,
                                  'heatmap_metric-distcorr_c-%02d.png' % c), 
                        bbox_inches='tight')
    factor_distances = pd.DataFrame(factor_distances)
    factor_distances.loc[:, 'raw'] = squareform(clustered_df)
    # create gif from files
    cmd = 'convert -delay 80 -loop 1 %s %s' % (path.join(plot_file, 'heatmap*'),
                                                path.join(plot_file, 'EFA_heatmaps.gif'))
    subprocess.call(cmd, shell=True)
    # delete still files
    for filey in glob(path.join(plot_file, 'heatmap*')):
        remove(filey)
    
    # repeat factor analysis above using PCA
    scaled_data = scale(data.loc[:, cluster_order]).T
    pca_distances = {}
    for c in results['EFA']['factor_tree'].keys():
        if c>2:
            pca = PCA(c)
            pca_out = pca.fit_transform(scaled_data)
            distances = pdist(pca_out, metric=distcorr)
            pca_distances[c] = distances
    pca_distances = pd.DataFrame(pca_distances)
    pca_distances.loc[:, 'raw'] = squareform(clustered_df)
    
    # plot correlations between distance matrices
    with sns.plotting_context('notebook', font_scale=1.8):
        f = plt.figure(figsize=(12,8))
        pca_distances.corr()['raw'][:-1].plot(label = 'PCA')
        factor_distances.corr()['raw'][:-1].plot(label = 'EFA')
        plt.xlabel('Components in Decomposition')
        plt.ylabel('Correlation with Raw Values')
        plt.title('Distance Matrix Correlations')
        plt.legend()
        f.savefig(path.join(plot_file, 
                            'distance_correlations_across_components_metric-distcorr.png'))
    
    
    
    
    













