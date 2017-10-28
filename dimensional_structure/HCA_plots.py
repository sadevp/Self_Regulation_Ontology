# imports
import argparse
from dimensional_structure.utils import  save_figure
from itertools import combinations
import matplotlib.pyplot as plt
import numpy as np
from os import path
import pandas as pd
import seaborn as sns
from selfregulation.utils.plot_utils import dendroheatmap
from sklearn.decomposition import PCA
from sklearn.manifold import MDS
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


def plot_clusterings(HCA, plot_dir=None, verbose=False):    
    # get all clustering solutions
    clusterings = [(k ,v) for k,v in 
                    HCA.results.items() if 'clustering' in k]
    
    # plot dendrogram heatmaps
    for name, clustering in clusterings:
        filename = None
        if plot_dir is not None:
            filename = path.join(plot_dir, '%s.png' % name)
        fig = dendroheatmap(clustering['linkage'], clustering['distance_df'], 
                            clustering['clustering']['labels'],
                            figsize=(50,50),  filename = filename)
    
    
    # plot cluster agreement across embedding spaces
    names = [k.split('-')[-1] for k,v in 
                    HCA.results.items() if 'clustering' in k]
    cluster_similarity = np.zeros((len(clusterings), len(clusterings)))
    cluster_similarity = pd.DataFrame(cluster_similarity, 
                                     index=names,
                                     columns=names)
    for clustering1, clustering2 in combinations(clusterings, 2):
        name1 = clustering1[0].split('-')[-1]
        name2 = clustering2[0].split('-')[-1]
        clusters1 = clustering1[1]['clustering']['labels']
        clusters2 = clustering2[1]['clustering']['labels']
        rand_score = adjusted_rand_score(clusters1, clusters2)
        MI_score = adjusted_mutual_info_score(clusters1, clusters2)
        cluster_similarity.loc[name1, name2] = rand_score
        cluster_similarity.loc[name2, name1] = MI_score
    
    with sns.plotting_context(context='notebook', font_scale=1.4):
        fig = plt.figure(figsize = (12,12))
        sns.heatmap(cluster_similarity, square=True)
        plt.title('Cluster Similarity: TRIL: Adjusted MI, TRIU: Adjusted Rand',
                  y=1.02)
        
    if plot_dir is not None:
        save_figure(fig, path.join(plot_dir, 
                                   'cluster_similarity_across_measures.pdf'),
                    {'bbox_inches': 'tight'})
    
    if verbose:
        # assess relationship between two measurements
        rand_scores = cluster_similarity.values[np.triu_indices_from(cluster_similarity, k=1)]
        MI_scores = cluster_similarity.T.values[np.triu_indices_from(cluster_similarity, k=1)]
        score_consistency = np.corrcoef(rand_scores, MI_scores)[0,1]
        print('Correlation between measures of cluster consistency: %.2f' \
              % score_consistency)
        
        
def visualize_loading(results, c, plot_dir):
    HCA = results.HCA=None
    EFA = results.EFA
    c = 9
    
    cluster_loadings = HCA.get_cluster_loading(EFA, 'data', c)
    cluster_loadings_mat = np.vstack([i[1] for i in cluster_loadings])
    EFA_loading = abs(EFA.get_loading(c))
    EFA_loading_mat = EFA_loading.values
    input_data = np.vstack([cluster_loadings_mat, EFA_loading_mat])
    
    
    n_clusters = cluster_loadings_mat.shape[0]
    color_palette = sns.color_palette(palette='hls', n_colors=n_clusters)
    colors = []
    for var in EFA_loading.index:
        # find which cluster this variable is in
        index = [i for i,cluster in enumerate(cluster_loadings) \
                 if var in cluster[0]][0]
        colors.append(color_palette[index])
        
    
    mds = MDS()
    mds_out = mds.fit_transform(input_data)
    
    with sns.axes_style('white'):
        f=plt.figure(figsize=(14,14))
        plt.scatter(mds_out[n_clusters:,0], mds_out[n_clusters:,1], 
                    s=50, color=colors)
        plt.scatter(mds_out[:n_clusters,0], mds_out[:n_clusters,1], 
                    marker='*', s=2200, color=color_palette)
        # plot cluster number
        offset = .011
        font_dict = {'fontsize': 17, 'color':'white'}
        for i,(x,y) in enumerate(mds_out[:n_clusters]):
            if i<9:
                plt.text(x-offset,y-offset,i+1, font_dict)
            else:
                plt.text(x-offset*2,y-offset,i+1, font_dict)
    if plot_dir:
        save_figure(f, path.join(plot_dir, 'MDS_factor_loadings'))
    
    # same plot as above but over the raw data
    plt.figure(figsize=(12,12))
    mds = MDS()
    mds_out = mds.fit_transform(scale(results.data).T)
    plt.scatter(mds_out[:,0], mds_out[:,1], 
                    s=100, color=colors)

       
"""      
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
    
"""    
    
    
    













