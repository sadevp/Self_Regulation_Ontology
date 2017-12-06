import hddm
import numpy
import pandas
import pickle
import sys

task = sys.argv[1]
input_dir = sys.argv[2]
output_dir = sys.argv[3]

def fit_HDDM(df, response_col = 'correct', condition = None, fixed= ['t','a'], 
             estimate_task_vars = True, outfile = None, samples=40000):
    """ fit_HDDM is a helper function to run hddm analyses.
    :df: that dataframe to perform hddm analyses on
    :response_col: a column of correct/incorrect values
    :condition: optional, categoricla variable to use to separately calculated ddm parameters
    :fixed: a list of ddm parameters (e.g. ['a', 't']) where 'a' is threshold, 'v' is drift and 't' is non-decision time
        to keep fixed when using the optional condition argument
    :estimate_task_vars: bool, if True estimate DDM vars using the entire task in addition to conditional vars
    """  
    assert estimate_task_vars or condition != None, "Condition must be defined or estimate_task_vars must be set to true"
    variable_conversion = {'a': ('thresh', 'Pos'), 'v': ('drift', 'Pos'), 't': ('non_decision', 'NA')}
    # set up condition variables
    if condition:
        condition_vars = [var for var in ['a','v','t'] if var not in fixed]
        depends_dict = {var: 'condition' for var in condition_vars}
    else:
        condition_vars = []
        depends_dict = {}
    # set up data
    data = (df.loc[:,'rt']/1000).astype(float).to_frame()
    data.insert(0, 'response', df[response_col].astype(float))
    if condition:
        data.insert(0, 'condition', df[condition])
        conditions = [i for i in data.condition.unique() if i]
    
    # add subject ids 
    data.insert(0,'subj_idx', df['worker_id'])
    # remove missed responses and extremely short response
    data = data.query('rt > .05')
    subj_ids = data.subj_idx.unique()
    ids = {subj_ids[i]:int(i) for i in range(len(subj_ids))}
    data.replace(subj_ids, [ids[i] for i in subj_ids],inplace = True)
    if outfile:
        db_base = outfile + '_base_traces.db'
        db_condition = outfile + '_condition_traces.db'
    else:
        db_base = db_condition = None
    # extract dvs pip install -U --no-deps kabuki
    group_dvs = {}
    dvs = {}
    # run if estimating variables for the whole task
    if estimate_task_vars:
        # run hddm
        m = hddm.HDDM(data)
        # find a good starting point which helps with the convergence.
        m.find_starting_values()
        # start drawing 10000 samples and discarding 1000 as burn-in
        m.sample(samples, burn=samples/10, thin = 5,
                 dbname=db_base, db='pickle')
        #dvs = {var: m.nodes_db.loc[m.nodes_db.index.str.contains(var + '_subj'),'mean'] for var in ['a', 'v', 't']}  
        dvs = {var: m.nodes_db.loc[m.nodes_db.index.str.contains(var),'mean'][0] for var in ['a', 'v', 't']} 
        if outfile:
            try:
                pickle.dump(m, open(outfile + '_base.model', 'wb'))
            except Exception:
                print('Saving base model failed')
    # if there is a condition that the hddm depends on, use that
    if len(depends_dict) > 0:
        # run hddm
        m_depends = hddm.HDDM(data, depends_on=depends_dict)
        # find a good starting point which helps with the convergence.
        m_depends.find_starting_values()
        # start drawing 10000 samples and discarding 1000 as burn-in
        m_depends.sample(samples, burn=samples/10, thin = 5, 
                         dbname=db_condition, db='pickle')
        if outfile:
            try:
                pickle.dump(m_depends, 
                            open(outfile + '_condition.model', 'wb'))
            except Exception:
                print('Saving condition model failed')
    for var in depends_dict.keys():
        dvs[var + '_conditions'] = m_depends.nodes_db.loc[m_depends.nodes_db.index.str.contains(var + '_subj'),'mean']
    
    for i,subj in enumerate(subj_ids):
        group_dvs[subj] = {}
        hddm_vals = {}
        for var in ['a','v','t']:
            var_name, var_valence = variable_conversion[var]
            if var in list(dvs.keys()):
                hddm_vals.update({'hddm_' + var_name: {'value': dvs[var], 'valence': var_valence}})
            if var in condition_vars:
                for c in conditions:
                    try:
                        hddm_vals.update({'hddm_' + var_name + '_' + c: {'value': dvs[var + '_conditions'].filter(regex = '\(' + c + '\)', axis = 0)[i], 'valence': var_valence}})
                    except IndexError:
                        print('%s failed on condition %s for var: %s' % (subj, c, var_name))                
        group_dvs[subj].update(hddm_vals)
    return group_dvs


def SS_HDDM(df, samples):
    x = df.query('SS_trial_type == "go" \
                 and exp_stage not in ["practice","NoSS_practice"]')
    return fit_HDDM(x, outfile = 'stop_signal', samples=samples)

def get_HDDM_fun(task=None, samples=40000):
    hddm_fun_dict = \
    {
        'adaptive_n_back': lambda df: fit_HDDM(df.query('load == 2'), 
                                               outfile='adaptive_n_back',
                                               samples=samples),
        'attention_network_task': lambda x: ANT_HDDM(x, samples),
        'choice_reaction_time': lambda x: fit_HDDM(x, 
                                        outfile = 'choice_reaction_time', 
                                        samples=samples),
        'directed_forgetting': lambda x: fit_HDDM(x.query('trial_id == "probe"'), 
                                                  condition = 'probe_type', 
                                                  outfile = 'directed_forgetting',
                                                  samples=samples),
        'dot_pattern_expectancy': lambda x: fit_HDDM(x, 
                                  condition =  'condition', 
                                  outfile = 'dot_pattern_expectancy',
                                  samples=samples), 
        'local_global_letter': lambda x: local_global_HDDM(x, samples),
        'motor_selective_stop_signal': lambda x: motor_SS_HDDM(x, samples),
        'recent_probes': lambda x: fit_HDDM(x, 
                                            condition = 'probeType', 
                                            outfile = 'recent_probes',
                                            samples=samples),
        'shape_matching': lambda x: fit_HDDM(x, 
                                             condition = 'condition', 
                                             outfile = 'shape_matching',
                                             samples=samples),
        'simon': lambda x: fit_HDDM(x, 
                                    condition = 'condition', 
                                    outfile = 'simon',
                                    samples=samples),
        'stim_selective_stop_signal': lambda x: stim_SS_HDDM(x, samples),
        'stop_signal': lambda x: SS_HDDM(x, samples),
        'stroop': lambda x: fit_HDDM(x, 
                                     condition = 'condition', 
                                     outfile = 'stroop',
                                     samples=samples),
        'threebytwo': lambda x: threebytwo_HDDM(x, samples),
        'twobytwo': lambda x: twobytwo_HDDM(x, samples)
    }
    if task is None:
        return hddm_fun_dict
    else:
        return hddm_fun_dict[task]

#read data in
all_data = pandas.read_csv(input_dir+task+'.csv', compression='gzip')

for i in range(all_data.worker_id.unique().shape[0]):
    sub_id = all_data.worker_id.unique()[i]
    df = all_data.query('worker_id == %s' % sub_id)

