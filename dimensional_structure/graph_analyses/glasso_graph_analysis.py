import bct
from os.path import join
import seaborn as sns
from selfregulation.utils.r_to_py_utils import qgraph_cor
from selfregulation.utils.utils import get_behav_data, get_info
from selfregulation.utils.plot_utils import dendroheatmap_left
from selfregulation.utils.graph_utils import  Graph_Analysis

base_directory = get_info('base_directory')
plot_dir = join(base_directory,'dimensional_structure','Plots')
data = get_behav_data(file='meaningful_variables_imputed.csv', 
                      dataset = 'Complete_01-31-2017')

# correlation matrix calculated by cor_auto from qgraph
cor = qgraph_cor(data)
# regularized partial correlation matrix calculated by EBICglasso
gcor, tuning_param = qgraph_cor(data, True)
# how similar are these?
sns.plt.scatter(cor.as_matrix().flatten(),gcor.as_matrix().flatten())
# plot heatmaps
fig,leaves = dendroheatmap_left(gcor, label_fontsize=6)
fig.savefig(join(plot_dir,'gcor_dendroheatmap.pdf'))



GA = Graph_Analysis()
GA.setup(data = gcor, 
         thresh_func = bct.threshold_absolute,
         community_alg = bct.modularity_louvain_und_sign)
GA.calculate_communities()
GA.set_visual_style(layout='kk', plot_threshold=0)
GA.display()
