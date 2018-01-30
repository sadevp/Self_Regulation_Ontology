# Defines Results and Analysis Classes to run on subsets of data

# imports
from utils import (
        create_factor_tree, distcorr,  find_optimal_components, 
        get_loadings, get_scores_from_subset, get_top_factors, 
        hdbscan_cluster, hierarchical_cluster, 
        quantify_lower_nesting
        )
from prediction_utils import run_EFA_prediction
import glob
from os import makedirs, path
import pandas as pd
import numpy as np
import pickle
import random
from scipy.cluster.hierarchy import leaves_list, linkage
from scipy.spatial.distance import squareform
from scipy.stats import entropy
from selfregulation.utils.graph_utils import  (get_adj, Graph_Analysis)
from selfregulation.utils.utils import get_behav_data, get_info
from selfregulation.utils.r_to_py_utils import get_attr, get_Rpsych, psychFA
from sklearn.preprocessing import scale

# load the psych R package
psych = get_Rpsych()

# ****************************************************************************
# Peform factor analysis
# ****************************************************************************
# test if sample is suitable for factor analysis

class EFA_Analysis:
    def __init__(self, data, data_no_impute=None):
        self.results = {}
        self.data = data
        if data_no_impute is not None:
            self.data_no_impute = data_no_impute
        # global variables to hold certain aspects of the analysis
        self.num_factors = 1
        self.results['factor_tree'] = {}
        self.results['factor_tree_Rout'] = {}
        self.results['factor2_tree'] = {}
        self.results['factor2_tree_Rout'] = {}
    
    # private methods
    def _get_attr(self, attribute, c=None):
        if c is None:
            c = self.num_factors
            print('# of components not specified, using BIC determined #')
        return get_attr(self.results['factor_tree_Rout'][c],
                        attribute)
    
    def _thresh_loading(loading, threshold=.2):
        over_thresh = loading.max(1)>threshold
        rejected = loading.index[~over_thresh]
        return loading.loc[over_thresh,:], rejected
    
    def _get_factor_reorder(self, c):
        # reorder factors based on correlation matrix
        phi=get_attr(self.results['factor_tree_Rout'][c],'Phi')
        new_order = list(leaves_list(linkage(squareform(np.round(1-phi,3)))))
        return new_order[::-1] # reversing because it works better for task EFA
            
    # public methods
    def adequacy_test(self, verbose=False):
        """ Determine whether data is adequate for EFA """
        data = self.data
        # KMO test should be > .6
        KMO_MSA = psych.KMO(data.corr())[0][0]
        # barlett test should be significant
        Barlett_p = psych.cortest_bartlett(data.corr(), data.shape[0])[1][0]
        adequate = KMO_MSA>.6 and Barlett_p < .05
        if verbose:
            print('Is the data adequate for factor analysis? %s' % \
                  ['No', 'Yes'][adequate])
        return adequate, {'Barlett_p': Barlett_p, 'KMO': KMO_MSA}
    
    def create_factor_tree(self, start=1, end=None):
        if end is None:
            end = max(self.num_factors, start)
        ftree, ftree_rout = create_factor_tree(self.data,  (start, end))
        self.results['factor_tree'] = ftree
        self.results['factor_tree_Rout'] = ftree_rout
        
    def get_dimensionality(self, metrics=None, verbose=False):
        """ Use multiple methods to determine EFA dimensionality
        
        Args
            Metrics: A list including a subset of the following strings:
                BIC, parallel, SABIC, and CV. Default [BIC, parallel]
        """
        if metrics is None:
            metrics = ['BIC', 'parallel']
        if 'BIC' in metrics:
            BIC_c, BICs = find_optimal_components(self.data, metric='BIC')
            self.results['c_metric-BIC'] = BIC_c
            self.results['cscores_metric-BIC'] = BICs
        if 'parallel' in metrics:
            # parallel analysis
            parallel_out = psych.fa_parallel(self.data, fa='fa', fm='ml',
                                             plot=False, **{'n.iter': 100})
            parallel_c = parallel_out[parallel_out.names.index('nfact')][0]
            self.results['c_metric-parallel'] = int(parallel_c)
        if 'SABIC' in metrics:
            # using SABIC
            SABIC_c, SABICs = find_optimal_components(self.data, metric='SABIC')
            self.results['c_metric-SABIC'] = SABIC_c
            self.results['cscores_metric-SABIC'] = SABICs
        if 'CV' in metrics:
            try:
                 # using CV
                CV_c, CVs = find_optimal_components(self.data_no_impute, 
                                                    maxc=50, metric='CV')
                self.results['c_metric-CV'] = CV_c
                self.results['cscores_metric-CV'] = CVs
            except AttributeError:
                print("CV dimensionality could not be calculated. " + \
                      "data_no_impute not found.")
        # record max_factors
        best_cs = {k:v for k,v in self.results.items() if 'c_metric-' in k}
        self.num_factors = BIC_c
        if verbose:
                print('Best Components: ', best_cs)
    
    def get_higher_order_factors(self, c=None):
        """ Return higher order EFA """
        if c is None:
            c = self.num_factors
            print('# of components not specified, using BIC determined #')
        if ('factor_tree' in self.results.keys() and 
            c in self.results['factor_tree_Rout'].keys()):
            # get factor correlation matrix
            phi = pd.DataFrame(get_attr(self.results['factor_tree_Rout'][c], 'Phi'))
            n_obs = self.data.shape[0]
            labels = list(self.results['factor_tree'][c].columns)
            BIC_c, BICs = find_optimal_components(phi, 
                                                  metric='BIC', 
                                                  nobs=n_obs)
            Rout, higher_order_out = psychFA(phi, BIC_c, nobs=n_obs)
            loadings = get_loadings(higher_order_out, labels)
            self.results['factor2_tree'][c] = loadings
            self.results['factor2_tree_Rout'][c] = Rout
        else:
            print('No %s factor solution computed yet!' % c)
            
    def get_loading(self, c=None):
        """ Return the loading for an EFA solution at the specified c """
        if c is None:
            c = self.num_factors
            print('# of components not specified, using BIC determined #')
        if ('factor_tree' in self.results.keys() and 
            c in self.results['factor_tree'].keys()):
            return self.results['factor_tree'][c]
        else:
            print('No %s factor solution computed yet! Computing...' % c)
            fa, output = psychFA(self.data, c, method='ml')
            loadings = get_loadings(output, labels=self.data.columns)
            self.results['factor_tree'][c] = loadings
            self.results['factor_tree_Rout'][c] = fa
            return loadings
    
    def get_loading_entropy(self, c=None):
        if c is None:
            c = self.num_factors
            print('# of components not specified, using BIC determined #')
        assert c>1
        loading = self.get_loading(c)
        # calculate entropy of each variable
        loading_entropy = abs(loading).apply(entropy, 1)
        max_entropy = entropy([1/loading.shape[1]]*loading.shape[1])
        return loading_entropy/max_entropy
    
    def get_null_loading_entropy(self, c=None, reps=50):
        if c is None:
            c = self.num_factors
            print('# of components not specified, using BIC determined #')
        assert c>1
        # get absolute loading
        loading = abs(self.get_loading(c))
        max_entropy = entropy([1/loading.shape[1]]*loading.shape[1])
        permuted_entropies = np.array([])
        for _ in range(reps):
            # shuffle matrix
            for i, col in enumerate(loading.values.T):
                shuffle_vec = np.random.permutation(col)
                loading.iloc[:, i] = shuffle_vec
            # calculate entropy of each variable
            loading_entropy = loading.apply(entropy, 1)
            permuted_entropies = np.append(permuted_entropies,
                                           (loading_entropy/max_entropy).values)
        return permuted_entropies
    
    def get_factor_entropies(self):
        # calculate entropy for each measure at different c's
        entropies = {}
        null_entropies = {}
        for c in self.results['factor_tree'].keys():
            if c > 1:
                entropies[c] = self.get_loading_entropy(c)
                null_entropies[c] = self.get_null_loading_entropy(c)
        self.results['entropies'] = pd.DataFrame(entropies)
        self.results['null_entropies'] = pd.DataFrame(null_entropies)
        
    def get_metric_cs(self):
        metric_cs = {k:v for k,v in self.results.items() if 'c_metric-' in k}
        return metric_cs
    
    def get_factor_names(self, c=None):
        if c is None:
            c = self.num_factors
            print('# of components not specified, using BIC determined #')
        return self.get_loading(c).columns
    
    def get_scores(self, c=None):
        if c is None:
            c = self.num_factors
            print('# of components not specified, using BIC determined #')
        scores = self._get_attr('scores', c)
        names = self.get_factor_names(c)
        scores = pd.DataFrame(scores, index=self.data.index,
                              columns=names)
        return scores
        
    def get_task_representations(self, tasks, c=None):
        """Take a list of tasks and reconstructs factor scores"""   
        if c is None:
            c = self.num_factors
            print('# of components not specified, using BIC determined #')         
        fa_output = self.results['factor_tree_Rout'][c]
        output = {'weights': get_attr(fa_output, 'weights'),
                  'scores': get_attr(fa_output, 'scores')}
        subset_scores, r2_scores = get_scores_from_subset(self.data,
                                                          output,
                                                          tasks)
        return subset_scores, r2_scores
        
    def get_nesting_matrix(self, explained_threshold=.5):
        factor_tree = self.results['factor_tree']
        explained_scores = -np.ones((len(factor_tree), len(factor_tree)-1))
        sum_explained = np.zeros((len(factor_tree), len(factor_tree)-1))
        for key in self.results['lower_nesting'].keys():
            r =self.results['lower_nesting'][key]
            adequately_explained = r['scores'] > explained_threshold
            explained_score = np.mean(r['scores'][adequately_explained])
            if np.isnan(explained_score): explained_score = 0
            explained_scores[key[1]-1, key[0]-1] = explained_score
            sum_explained[key[1]-1, key[0]-1] = (np.sum(adequately_explained/key[0]))
        return explained_scores, sum_explained
    
    def name_factors(self, labels):
        loading = self.get_loading(len(labels))
        loading.columns = labels
    
    def print_top_factors(self, c=None, n=5):
        if c is None:
            c = self.num_factors
            print('# of components not specified, using BIC determined #')
        tmp = get_top_factors(self.get_loading(c), n=n, verbose=True)
      
    def reorder_factors(self, mat):
        c = mat.shape[1]
        reorder_vec = self._get_factor_reorder(c)
        if type(mat) == pd.core.frame.DataFrame:
            mat = mat.iloc[:, reorder_vec]
        else:
            mat = mat[reorder_vec][:, reorder_vec]
        return mat
    
    def run(self, loading_thresh=None, verbose=False):
        # check adequacy
        adequate, adequacy_stats = self.adequacy_test(verbose)
        assert adequate, "Data is not adequate for EFA!"
        self.results['EFA_adequacy'] = {'adequate': adequate, 
                                            'adequacy_stats': adequacy_stats}
        
        # get optimal dimensionality
        if 'c_metric-parallel' not in self.results.keys():
            if verbose: print('Determining Optimal Dimensionality')
            self.get_dimensionality(verbose=verbose)
            
        # create factor tree
        if verbose: print('Creating Factor Tree')
        self.get_loading(c=self.num_factors)
        # optional threshold
        if loading_thresh is not None:
            for c, loading in self.results['factor_tree'].items():
                thresh_loading = self._thresh_loading(loading, loading_thresh)
                self.results['factor_tree'][c], rejected = thresh_loading
        # get higher level factor solution
        if verbose: print('Determining Higher Order Factors')
        self.get_higher_order_factors()
        # quantify lower nesting
        self.results['lower_nesting'] = quantify_lower_nesting(self.results['factor_tree'])
        # get entropies
        self.get_factor_entropies()
    
    def verify_factor_solution(self):
        fa, output = psychFA(self.data, 10)
        scores = output['scores'] # factor scores per subjects derived from psychFA
        scaled_data = scale(self.data)
        redone_scores = scaled_data.dot(output['weights'])
        redone_score_diff = np.mean(scores-redone_scores)
        assert(redone_score_diff < 1e-5)
        
class HDBScan_Analysis():
    """ Runs Hierarchical Clustering Analysis """
    def __init__(self, dist_metric):
        self.results = {}
        self.dist_metric = dist_metric
        self.metric_name = 'unknown'
        if self.dist_metric == distcorr:
            self.metric_name = 'distcorr'
        else:
            self.metric_name = self.dist_metric
    
    def cluster_data(self, data):
        output = hierarchical_cluster(data.T)
        self.results['clustering_input-data'] = output
        
    def cluster_EFA(self, EFA, c):
        loading = EFA.get_loading(c)
        output = hdbscan_cluster(loading)
        self.results['clustering_input-EFA%s' % c] = output
        
    
    def get_cluster_labels(self, inp='data'):
        cluster = self.results['clustering_input-%s' % inp]
        dist = cluster['distance_df']
        labels = cluster['labels']
        probs = cluster['probs']
        label_names = [[(dist.index[i], probs[i]) 
                        for i,l in enumerate(labels) if l == ii]
                        for ii in np.unique(labels)]
        return label_names
    
    def get_cluster_loading(self, EFA, inp, c):
        cluster_labels = self.get_cluster_labels(inp)
        cluster_loadings = []
        for cluster in cluster_labels:
            subset = abs(EFA.get_loading(c).loc[cluster,:])
            cluster_vec = subset.mean(0)
            cluster_loadings.append((cluster, cluster_vec))
        return cluster_loadings
    
    def run(self, data, EFA, cluster_EFA=False, c=None, verbose=False):
        if verbose: print("Clustering data")
        self.cluster_data(data)
        if cluster_EFA:
            if verbose: print("Clustering EFA")
            self.cluster_EFA(EFA, c)
            
class HCA_Analysis():
    """ Runs Hierarchical Clustering Analysis """
    def __init__(self, dist_metric):
        self.results = {}
        self.dist_metric = dist_metric
        self.metric_name = 'unknown'
        if self.dist_metric == distcorr:
            self.metric_name = 'distcorr'
        else:
            self.metric_name = self.dist_metric
        
    def cluster_data(self, data):
        output = hierarchical_cluster(data.T, 
                                      pdist_kws={'metric': self.dist_metric})
        self.results['clustering_input-data'] = output
        
    def cluster_EFA(self, EFA, c):
        loading = EFA.get_loading(c)
        output = hierarchical_cluster(loading, 
                                      pdist_kws={'metric': self.dist_metric})
        self.results['clustering_input-EFA%s' % c] = output
        
    def get_cluster_labels(self, inp='data'):
        cluster = self.results['clustering_input-%s' % inp]
        labels = cluster['clustered_df'].index
        reorder_vec = cluster['reorder_vec']
        cluster_index = cluster['labels'][reorder_vec]
        cluster_labels = [[labels[i] for i,index in enumerate(cluster_index) \
                           if index == j] for j in np.unique(cluster_index)]
        return cluster_labels
    
    def build_graphs(self, inp, graph_data):
        """ Build graphs from clusters from HCA analysis
        Args:
            inp: the input label used for the hierarchical analysis
            graph_data: the data to subset based on the clusters found using
                inp. This data will be passed to a graph analysis. E.G, 
                graph_data can be the original data matrix or a EF embedding
        """
        cluster_labels = self.get_cluster_labels(inp)
        graphs = []
        for cluster in cluster_labels:
            if len(cluster)>1:
                subset = graph_data.loc[:,cluster]
                cor = get_adj(subset, 'abs_pearson')
                GA = Graph_Analysis()
                GA.setup(adj = cor)
                GA.calculate_centrality()
                graphs.append(GA)
            else:
                graphs.append(np.nan)
        return graphs
    
    def get_cluster_loading(self, EFA, inp, c):
        cluster_labels = self.get_cluster_labels(inp)
        cluster_loadings = []
        for cluster in cluster_labels:
            subset = abs(EFA.get_loading(c).loc[cluster,:])
            cluster_vec = subset.mean(0)
            cluster_loadings.append((cluster, cluster_vec))
        return cluster_loadings
            
    def get_graph_vars(self, graphs):
        """ returns variables for each cluster sorted by centrality """
        graph_vars = []
        for GA in graphs:
            g_vars = [(i['name'], i['eigen_centrality']) for i in list(GA.G.vs)]
            sorted_vars = sorted(g_vars, key = lambda x: x[1])
            graph_vars.append(sorted_vars)
        return graph_vars
    
    def run(self, data, EFA, cluster_EFA=False,
            run_graphs=False, verbose=False):
        if verbose: print("Clustering data")
        self.cluster_data(data)
        if cluster_EFA:
            if verbose: print("Clustering EFA")
            self.cluster_EFA(EFA, EFA.num_factors)
        if run_graphs == True:
            # run graph analysis on raw data
            graphs = self.build_graphs('data', data)
            self.results['clustering_input-data']['graphs'] = graphs
        
class Results(EFA_Analysis, HCA_Analysis):
    """ Class to hold olutput of EFA, HCA and graph analyses """
    def __init__(self, datafile, 
                 loading_thresh=None,
                 dist_metric=distcorr,
                 name='',
                 filter_regex='.',
                 ID=None,
                 results_dir=None
                 ):
        """
        Args:
            loading_thresh: threshold to use for factor analytic result
            dist_metric: distance metric for hierarchical clustering that is 
            passed to pdist
            name: string to append to ID, default to empty string
            filter_regex: regex string passed to data.filter
        """
        # load data
        self.data = get_behav_data(dataset=datafile, 
                                  file='meaningful_variables_imputed.csv',
                                  filter_regex=filter_regex)
        self.data_no_impute = get_behav_data(dataset=datafile,
                                             file='meaningful_variables_clean.csv',
                                             filter_regex=filter_regex)
        self.dataset = datafile
        if ID is None:
            self.ID =  '%s_%s' % (name, str(random.getrandbits(16)))
        else:
            self.ID = '%s_%s' % (name, str(ID))
        # set up output files
        if results_dir is None:
            results_dir = get_info('results_directory')
        self.plot_file = path.join(results_dir, 'dimensional_structure', datafile, 'Plots', self.ID)
        self.output_file = path.join(results_dir, 'dimensional_structure', datafile, 'Output', self.ID)
        makedirs(self.plot_file, exist_ok = True)
        makedirs(self.output_file, exist_ok = True)
        # set vars
        self.loading_thresh = None
        self.dist_metric = dist_metric
        # initialize analysis classes
        self.EFA = EFA_Analysis(self.data, self.data_no_impute)
        self.HCA = HCA_Analysis(dist_metric=self.dist_metric)
        self.hdbscan = HDBScan_Analysis(dist_metric=self.dist_metric)
        
    def run_EFA_analysis(self, verbose=False):
        if verbose:
            print('*'*79)
            print('Running EFA')
            print('*'*79)
        self.EFA.run(self.loading_thresh, verbose=verbose)

    def run_clustering_analysis(self, cluster_EFA=True, run_graphs=True,
                                dist_metric=None, verbose=False):
        """ Run HCA Analysis
        
        Args:
            dist_metric: if provided, create a new HCA instances with the
                provided dist_metric and return it. If None (default) run
                the results' internal HCA with the dist_metric provided
                at creation
        """
        if verbose:
            print('*'*79)
            print('Running HCA')
            print('*'*79)
        if dist_metric is None: 
            self.HCA.run(self.data, self.EFA, cluster_EFA=cluster_EFA,
                         run_graphs=run_graphs, verbose=verbose)
            self.hdbscan.run(self.data, self.EFA, cluster_EFA=cluster_EFA,
                             verbose=verbose)
        else:
            HCA = HCA_Analysis(dist_metric=dist_metric)
            HCA.run(self.data, self.EFA, cluster_EFA=cluster_EFA,
                    run_graphs=run_graphs, verbose=verbose)
            hdbscan = HDBScan_Analysis(dist_metric=dist_metric)
            hdbscan.run(self.data, self.EFA, cluster_EFA=cluster_EFA,
                        verbose=verbose)
            return {'HCA': HCA, 'hdbscan': hdbscan}
    
    def run_prediction(self, c, shuffle=False, no_baseline_vars=True,
                       outfile=None):
        scores = self.EFA.get_scores(c)
        if outfile is None:
            run_EFA_prediction(self.dataset, scores, self.output_file,
                               shuffle=shuffle, 
                               no_baseline_vars=no_baseline_vars)
        else:
            run_EFA_prediction(self.dataset, scores, outfile,
                               shuffle=shuffle, 
                               no_baseline_vars=no_baseline_vars)
    
    def load_prediction_object(self, ID=None, shuffle=False):
        prediction_files = glob.glob(path.join(self.output_file,
                                               'prediction_outputs',
                                               '*'))
        if shuffle:
            prediction_files = [f for f in prediction_files if 'shuffle' in f]
        else:
            prediction_files = [f for f in prediction_files if 'shuffle' not in f]
        # sort by time
        if ID is not None:
            filey = [i for i in prediction_files if ID in i][0]
        else:
            prediction_files.sort(key=path.getmtime)
            filey = prediction_files[-1]
        behavpredict = pickle.load(open(filey,'rb'))
        return behavpredict

    def set_EFA(self, EFA):
        """ replace current EFA object with another """
        self.EFA = EFA
        
    def set_HCA(self, HCA):
        """ replace current EFA object with another """
        self.HCA = HCA
        
    # Bootstrap Functions
    def gen_resample_data(self):
        return self.data.sample(self.data.shape[0], replace=True)
    
    def run_EFA_bootstrap(self, boot_data=None, verbose=False):
        if boot_data is None:
            boot_data = self.gen_resample_data()
        EFA_boot = EFA_Analysis(boot_data)
        EFA_boot.run(self.loading_thresh, verbose=verbose)
        return EFA_boot
    
    def run_clustering_bootstrap(self, EFA, boot_data=None, cluster_EFA=True, 
                                 verbose=False):
        if boot_data is None:
            boot_data = self.gen_resample_data()
        HCA_boot = HCA_Analysis(self.dist_metric)
        HCA_boot.run(boot_data, EFA, cluster_EFA=cluster_EFA, verbose=verbose)
        
        hdbscan_boot = HDBScan_Analysis(dist_metric=self.dist_metric)
        hdbscan_boot.run(boot_data, EFA, cluster_EFA=cluster_EFA,
                        verbose=verbose)
            
        return {'HCA': HCA_boot, 'hdbscan': hdbscan_boot}

    def run_bootstrap(self, run_HCA=True, verbose=False, save=False):
        boot_data = self.gen_resample_data()
        EFA_boot = self.run_EFA_bootstrap(boot_data, verbose)
        boot_run = {'data': boot_data, 'EFA': EFA_boot}
        if run_HCA:
            cluster_boot = self.run_clustering_bootstrap(EFA_boot, boot_data, verbose)
            boot_run['HCA'] = cluster_boot['HCA']
            boot_run['hdbscan'] = cluster_boot['hdbscan']
        if save==True:
            boot_path = path.join(self.output_file, 'bootstrap_output')
            makedirs(boot_path, exist_ok=True)
            ID = random.getrandbits(16)
            filename = 'bootstrap_ID-%s.pkl' % ID
            pickle.dump(boot_run, open(path.join(boot_path, filename), 'wb'))
        else:
            return boot_run
        
    def reduce_boot(self, boot_run):
        EFA = boot_run['EFA']
        HCA = boot_run['HCA']
        cs = EFA.get_metric_cs()
        factors = {i: EFA.get_loading(c) for i, c in cs.items()}
        results = {}
        results['metric_cs'] = cs
        results['factor_solutions'] = factors
        results['HCA_solutions'] = HCA.results
        return results
        
    def reduce_boot_files(self, boot_loc, save=False):
        """ Run "run_boostrap", but only save important params """
        results = []
        for filey in glob.glob(path.join(boot_loc, 'bootstrap*ID*')):
            boot_run = pickle.load(open(filey, 'rb'))
            results.append(self.reduce_boot(boot_run))
        if save == True:
            pickle.save(open(path.join(boot_loc, 'bootstrap_aggregate.pkl', 'wb')))
        else:
            return results
    

                


    
    
    