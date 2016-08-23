from expanalysis.results import get_filters
from expanalysis.experiments.processing import extract_row, post_process_data, post_process_exp, extract_experiment, calc_DVs, extract_DVs,flag_data,  get_DV, generate_reference
from expanalysis.experiments.stats import results_check
from expanalysis.experiments.utils import result_filter
import json
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.decomposition import PCA
from util import *




#***************************************************
# ********* Load Data **********************
#************************************************** 
try:
    worker_lookup = json.load(open("../Data/worker_lookup.json",'r'))
    inverse_lookup = {v: k for k, v in worker_lookup.items()}
except IOError:
    print('no worker lookup found!')

try:
    worker_counts = json.load(open("../Data/worker_counts.json",'r'))
except IOError:
    print('no worker counts found!')
    
try:
    worker_pay = pd.read_json("../Data/worker_pay.json",'r')
except IOError:
    print('no worker pay found!')
    
#load Data
token, data_dir = [line.rstrip('\n').split(':')[1] for line in open('../Self_Regulation_Settings.txt')]

# read preprocessed data
data = pd.read_json(data_dir + 'mturk_discovery_data_post.json')

# get DV df
DV_df = pd.read_json(data_dir + 'mturk_discovery_DV.json')


# ************************************
# ********* Save Components of Data **
# ************************************
items = []
exps = []
for exp in data.experiment_exp_id.unique():
    if 'survey' in exp:
        survey = extract_experiment(data,exp)
        items += list(survey.text.unique())
        exps += [exp] * len(survey.text.unique())
items_df = pd.DataFrame({'survey': exps, 'items': items})
items_df.to_csv('/home/ian/tmp/items.csv')

# ************************************
# ********* DVs **********************
# ************************************
exp = data.experiment_exp_id.unique()[5]
print exp 
dv=get_DV(data,exp)
np.mean([i['Release_clicks'] for i in dv[0].values()])
sns.plt.hist([i['alerting_rt'] for i in dv[0].values()])

# get all DVs

subset = DV_df.drop(DV_df.filter(regex='missed_percent|avg_rt|std_rt|overall_accuracy').columns, axis = 1)
survey_df = subset.filter(regex = 'survey')

EZ_df = subset.filter(regex = 'thresh|drift')
rt_df = DV_df.filter(regex = 'avg_rt')

plot_df = survey_df
plot_df.columns = [' '.join(x.split('_')) for x in  plot_df.columns]
fig = dendroheatmap(plot_df.corr(), labels = True)
fig.savefig('/home/ian/EZ_df.png')
np.mean(np.mean(plot_df.corr().mask(np.triu(np.ones(plot_df.corr().shape)).astype(np.bool))))

# ***************************
#PCA
# ***************************

X = DV_df.corr()
pca = PCA(n_components = 'mle')
pca.fit(X)
Xt = pca.transform(X)
[abs(np.corrcoef(pca.components_[0,:],X.iloc[i,:]))[0,1] for i in range(len(X))]

#PCA plotting
selection = 'EZ'
fig, ax = sns.plt.subplots()
ax.scatter(Xt[:,0],Xt[:,1],100, c = ['r' if selection in x else 'b' for x in X.columns])

for i, txt in enumerate(X.columns):
    if selection in txt:
        ax.annotate(txt, (Xt[i,0],Xt[i,1]))

fig = plt.figure(1, figsize=(12, 9))
plt.clf()
ax = Axes3D(fig, rect=[0, 0, .95, 1], elev=48, azim=134)
ax.scatter(Xt[:, 0], Xt[:, 1], Xt[:, 2], c = ['r' if selection in x else 'b' for x in X.columns], cmap=plt.cm.spectral)
    



sns.plt.plot(pca.explained_variance_ratio_)
summary = results_check(data, silent = True, plot = True)



