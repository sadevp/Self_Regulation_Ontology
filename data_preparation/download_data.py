from expanalysis.experiments.jspsych import calc_time_taken, get_post_task_responses
from expanalysis.experiments.processing import post_process_data, extract_DVs
from expanalysis.results import get_filters
import json
import numpy as np
from os import path
import pandas as pd
import sys

sys.path.append('../utils')
from data_preparation_utils import anonymize_data, calc_trial_order, convert_date, download_data, get_bonuses, get_pay,  remove_failed_subjects
from utils import get_info

# Fix Python 2.x.
try: input = raw_input
except NameError: pass
    
# get options
job = input('Type "download", "extras", "post", or "all": ')
sample = ['discovery', 'validation', 'incomplete']

#load Data
token = get_info('expfactory_token')
try:
    data_dir=get_info('data_directory')
except Exception:
    data_dir=path.join(get_info('base_directory'),'Data')

if job == 'download' or job == "all":
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
    
    #***************************************************
    # ********* Download Data**********************
    #**************************************************  
    #load Data
    f = open(token)
    access_token = f.read().strip()  
    data = download_data(data_dir, access_token, filters = filters,  battery = 'Self Regulation Battery')
    data.reset_index(drop = True, inplace = True)
    
if job in ['extras', 'all']:
    #Process Data
    if job == "extras":
        #load Data
        data = pd.read_json(path.join(data_dir, 'mturk_data.json'))
        data.reset_index(drop = True, inplace = True)
        print('Finished loading raw data')
    
    #anonymize data
    worker_lookup = anonymize_data(data)
    json.dump(worker_lookup, open(path.join(data_dir, 'worker_lookup.json','w')))
    
    # record subject completion statistics
    (data.groupby('worker_id').count().finishtime).to_json(path.join(data_dir, 'worker_counts.json'))
    
    # add a few extras
    convert_date(data)
    bonuses = get_bonuses(data)
    calc_time_taken(data)
    get_post_task_responses(data)   
    calc_trial_order(data)
    
    # save data
    data.to_json(path.join(data_dir, 'mturk_data_extras.json'))
    
    # calculate pay
    pay = get_pay(data)
    pay.to_json(path.join(data_dir, 'worker_pay.json'))
    print('Finished saving worker pay')
    
if job in ['post', 'all']:
    #Process Data
    if job == "post":
        data = pd.read_json(path.join(data_dir, 'mturk_data_extras.json'))
        data.reset_index(drop = True, inplace = True)
        print('Finished loading raw data')
    
    #get subject assignment
    subject_assignment = pd.read_csv('samples/subject_assignment.csv', index_col = 0)
    discovery_sample = list(subject_assignment.query('dataset == "discovery"').index)
    validation_sample = list(subject_assignment.query('dataset == "validation"').index)
    extra_sample =  ['s' + str(i) for i in range(501,600)]
    
    # create dataframe to hold failed data
    failed_data = pd.DataFrame()
    # preprocess extras
    # only get extra data
    extra_data = data.query('worker_id in %s' % extra_sample).reset_index(drop = True)
    post_process_data(extra_data)
    failures = remove_failed_subjects(extra_data)
    failed_data = pd.concat([failed_data,failures])
    extra_workers = np.sort(extra_data.worker_id.unique())
    print('Finished processing extra data')    
    
    # preprocess and save each sample individually
    if 'discovery' in sample:
        # only get discovery data
        discovery_data = data.query('worker_id in %s' % discovery_sample).reset_index(drop = True)
        post_process_data(discovery_data)
        failures = remove_failed_subjects(discovery_data)
        failed_data = pd.concat([failed_data,failures])
        # add extra workers if necessary
        num_failures = len(failures.worker_id.unique())
        if num_failures > 0:
            makeup_workers = extra_workers[0:num_failures]
            new_data = extra_data[extra_data['worker_id'].isin(makeup_workers)]
            discovery_data = pd.concat([discovery_data, new_data]).reset_index(drop = True)
            extra_data.drop(new_data.index, inplace = True)
            extra_workers = np.sort(extra_data.worker_id.unique())
        discovery_data.to_json(path.join(data_dir,'mturk_discovery_data_post.json'))
        print('Finished saving post-processed discovery data')
        # save raw data
        discovery_raw = data.query('worker_id in %s' % list(discovery_data.worker_id.unique())).reset_index(drop = True)
        discovery_raw.to_json(path.join(data_dir,'mturk_discovery_data_raw.json'))
        print('Finished saving raw discovery data')
        
    if 'validation' in sample:
        # only get validation data
        validation_data = data.query('worker_id in %s' % validation_sample).reset_index(drop = True)
        post_process_data(validation_data)
        failures = remove_failed_subjects(validation_data)
        failed_data = pd.concat([failed_data,failures])
        # add extra workers to validation dataset
        validation_data = pd.concat([validation_data, extra_data]).reset_index(drop = True)
        validation_data.to_json(path.join(data_dir,'mturk_validation_data_post.json'))
        print('Finished saving post-processed validation data')
        # save raw data
        validation_raw = data.query('worker_id in %s' % list(validation_data.worker_id.unique())).reset_index(drop = True)
        validation_raw.to_json(path.join(data_dir,'mturk_validation_data_raw.json'))
        print('Finished saving raw validation data')
        
    if 'incomplete' in sample:
        # only get incomplete data
        incomplete_data = data.query('worker_id not in %s' % (validation_sample + discovery_sample + extra_sample)).reset_index(drop = True)
        post_process_data(incomplete_data)
        incomplete_data.to_json(data_dir + 'mturk_incomplete_data_post.json')
        print('Finished saving post-processed incomplete data')
    
    # save failed data
    failed_data = failed_data.reset_index(drop = True)
    failed_data.to_json(data_dir + 'mturk_failed_data_post.json')
    print('Finished saving post-processed failed data')
    