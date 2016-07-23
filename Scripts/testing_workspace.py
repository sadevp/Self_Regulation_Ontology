from expanalysis.results import get_filters
from expanalysis.experiments.processing import extract_row, post_process_data, post_process_exp, extract_experiment, calc_DVs, extract_DVs,flag_data,  get_DV, generate_reference
from expanalysis.experiments.stats import results_check
from expanalysis.experiments.utils import result_filter, anonymize_data
from expanalysis.experiments.jspsych import calc_time_taken, get_post_task_responses
import pandas as pd
import numpy as np
import seaborn as sns
from sklearn.decomposition import PCA
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from util import *
    
#***************************************************
# ********* Load Data **********************
#**************************************************        
pd.set_option('display.width', 200)
figsize = [16,12]
#set up filters
filters = get_filters()
drop_columns = ['battery_description', 'experiment_reference', 'experiment_version', \
         'experiment_name','experiment_cognitive_atlas_task']
for col in drop_columns:
    filters[col] = {'drop': True}

                  
f = open('/home/ian/Experiments/expfactory/docs/expfactory_token.txt')
access_token = f.read().strip()      
data_loc = '/home/ian/Experiments/expfactory/Self_Regulation_Ontology/Data/Battery_Results'     
data_source = load_data(access_token, data_loc, filters = filters, source = 'web', battery = 'Self Regulation Battery')
data = data_source.query('worker_id not in ["A254JKSDNE44AM", "A1O51P5O9MC5LX"]')

worker_lookup = anonymize_data(data)
calc_bonuses(data)
calc_time_taken(data)
get_post_task_responses(data)
post_process_data(data)
all_data = data # validation and discovery

subject_assignment = pd.read_csv('/home/ian/Experiments/expfactory/Self_Regulation_Ontology/subject_assignment.csv')
data = list(subject_assignment.query('dataset == "discovery"').iloc[:,0])
data = data.query('worker_id in %s' % discovery_sample)
#flag_data(data,'/home/ian/Experiments/expfactory/Self_Regulation_Ontology/post_process_reference.pkl')

# ************************************
# ********* Save Components of Data **
# ************************************
for exp in ['stop_signal','stim_selective_stop_signal','motor_selective_stop_signal']:
    get_DV(data,exp)

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
DV_df = extract_DVs(data)
DV_df.drop(DV_df.filter(regex='missed_percent').columns, axis = 1, inplace = True)

subset = DV_df.drop(DV_df.filter(regex='avg_rt|std_rt|overall_accuracy').columns, axis = 1)
survey_df = DV_df.filter(regex = 'survey')

EZ_df = DV_df.filter(regex = 'thresh|drift')
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


# ************************************
# ********* Misc Code for Reference **********************
# ************************************
worker_count = pd.concat([data.groupby('worker_id')['finishtime'].count(), \
    data.groupby('worker_id')['battery_name'].unique()], axis = 1)
flagged = data.query('flagged == True')

#generate reference
ref_worker = 's028' #this guy works for everything except shift task
file_base = '/home/ian/Experiments/expfactory/Self_Regulation_Ontology/post_process_reference'
generate_reference(result_filter(data, worker = ref_worker), file_base)
exp_dic = pd.read_pickle(file_base + '.pkl')
pd.to_pickle(exp_dic, file_base + '.pkl')

    
  

