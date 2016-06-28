"""
Network analysis
"""
from colorsys import hsv_to_rgb
 
def gen_color(h):
    # Source: http://www.goldennumber.net/color/
    golden_ratio = (1 + 5 ** 0.5) / 2
    h += golden_ratio
    h %= 1
    return '#%02x%02x%02x' % tuple(int(a*100) for a in hsv_to_rgb(h, 0.55, 2.3))

import networkx as nx
G = nx.Graph()

DVs = subset
heatmap = DVs.corr()
color_vals = {}
for i,exp in enumerate(heatmap.columns):
    color_vals[exp.split('.')[0]] = gen_color(i/float(len(heatmap)))

for DV in heatmap.columns:
    G.add_node(DV)
    
for i,DV in enumerate(heatmap.columns):
    for j in range(i+1,len(heatmap)):
        target = heatmap[DV].index[j]
        weight = heatmap[DV][j]
        if weight > 0:
            color = 'm'
        else:
            color = 'c'
        # color = color_vals[DV.split('.')[0]]
        if abs(weight)>.05:
            G.add_edge(DV, target, color = color, weight = weight)


import matplotlib.pyplot as plt

edges = G.edges()
weights = [G[u][v]['weight']**2 for u,v in edges]
colors = [G[u][v]['color'] for u,v in edges]

plt.figure(figsize=(14,14))
pos = nx.circular_layout(G) #spring or circular
nx.draw(G, pos = pos, edges = edges, edge_color = colors,  width=weights)
nx.draw_networkx_labels(G,pos,labels={key:key for key in G.nodes()})


