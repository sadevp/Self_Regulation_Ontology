# -*- coding: utf-8 -*-
"""
Spyder Editor

This is a temporary script file.
"""

import numpy,pandas
import os
import json


def get_data(basedir='/Users/poldrack/code/Self_Regulation_Ontology/discovery_survey_analyses'):

    datafile=os.path.join(basedir,'demographics.csv')

    data=pandas.read_csv(datafile,index_col=0)
    data=data.rename(columns={'worker_id':'worker'})
    return data,basedir


def get_demog_items(data):
    demog_items={}
    for i,r in data.iterrows():
        if not r.text in demog_items.keys():
            demog_items[r.text]=r
    return demog_items


def setup_itemid_dict():
    nominalvars=[]
    id_to_name={}
    id_to_name['demographics_survey_2']='Sex'
    nominalvars.append('demographics_survey_2')
    id_to_name['demographics_survey_3']='Age'
    id_to_name['demographics_survey_4']='Race'
    nominalvars.append('demographics_survey_4')
    id_to_name['demographics_survey_5']='OtherRace'
    nominalvars.append('demographics_survey_5')
    id_to_name['demographics_survey_6']='HispanicLatino'
    nominalvars.append('demographics_survey_6')
    id_to_name['demographics_survey_7']='HighestEducation'
    id_to_name['demographics_survey_8']='HeightInches'
    id_to_name['demographics_survey_9']='WeightPounds'
    id_to_name['demographics_survey_10']='RelationshipStatus'
    nominalvars.append('demographics_survey_10')
    id_to_name['demographics_survey_11']='DivorceCount'
    id_to_name['demographics_survey_12']='LongestRelationship'
    id_to_name['demographics_survey_13']='RelationshipNumber'
    id_to_name['demographics_survey_14']='ChildrenNumber'
    id_to_name['demographics_survey_15']='HouseholdIncome'
    id_to_name['demographics_survey_16']='RetirementAccount'
    nominalvars.append('demographics_survey_16')
    id_to_name['demographics_survey_17']='RetirementPercentStocks'
    id_to_name['demographics_survey_18']='RentOwn'
    nominalvars.append('demographics_survey_18')
    id_to_name['demographics_survey_19']='MortgageDebt'
    id_to_name['demographics_survey_20']='CarDebt'
    id_to_name['demographics_survey_21']='EducationDebt'
    id_to_name['demographics_survey_22']='CreditCardDebt'
    id_to_name['demographics_survey_23']='OtherDebtSources'
    nominalvars.append('demographics_survey_23')
    id_to_name['demographics_survey_24']='OtherDebtAmount'
    id_to_name['demographics_survey_25']='CoffeeCupsPerDay'
    id_to_name['demographics_survey_26']='TeaCupsPerDay'
    id_to_name['demographics_survey_27']='CaffienatedSodaCansPerDay'
    id_to_name['demographics_survey_28']='CaffieneOtherSourcesDayMG'
    id_to_name['demographics_survey_29']='GamblingProblem'
    nominalvars.append('demographics_survey_29')
    id_to_name['demographics_survey_30']='TrafficTicketsLastYearCount'
    id_to_name['demographics_survey_31']='TrafficAccidentsLifeCount'
    id_to_name['demographics_survey_32']='ArrestedChargedLifeCount'
    id_to_name['demographics_survey_33']='MotivationForParticipation'
    nominalvars.append('demographics_survey_33')
    id_to_name['demographics_survey_34']='MotivationOther'
    nominalvars.append('demographics_survey_34')
    return id_to_name,nominalvars

def save_metadata(demog_items,
                  outdir='/Users/poldrack/code/Self_Regulation_Ontology/discovery_survey_analyses/metadata'):

    if not os.path.exists(outdir):
        os.mkdir(outdir)
    id_to_name,nominalvars=setup_itemid_dict()

    demog_dict={"MeasurementToolMetadata": {"Description": 'Demographics',
            "TermURL": ''}}
    for i in demog_items:
            r=demog_items[i]
            if not pandas.isnull(r.options):
                itemoptions=eval(r.options)
            else:
                itemoptions=None
            itemid='_'.join(r['id'].split('_')[:3])
            assert itemid not in demog_dict  # check for duplicates
            demog_dict[itemid]={}
            demog_dict[itemid]['Description']=r.text
            demog_dict[itemid]['Levels']={}
            if itemid in nominalvars:
                demog_dict[itemid]['Nominal']=True
            levelctr=0
            if itemoptions is not None:
                for i in itemoptions:
                    if not 'value' in i:
                        value=levelctr
                        levelctr+=1
                    else:
                        value=i['value']
                    demog_dict[itemid]['Levels'][value]=i['text']
    #rename according to more useful names
    demog_dict_renamed={}
    for k in demog_dict.keys():
        if not k in id_to_name.keys():
            demog_dict_renamed[k]=demog_dict[k]
        else:
            demog_dict_renamed[id_to_name[k]]=demog_dict[k]
    with open(os.path.join(outdir,'demographics.json'), 'w') as outfile:
            json.dump(demog_dict_renamed, outfile, sort_keys = True, indent = 4,
                  ensure_ascii=False)
    return demog_dict_renamed,outdir

def add_demog_item_labels(data):
    item_ids=[]
    for i,r in data.iterrows():
        item_ids.append('_'.join(r['id'].split('_')[:3]))
    data['item_id']=item_ids
    return data

def save_demog_data(data,survey_metadata,
              outdir='/Users/poldrack/code/Self_Regulation_Ontology/discovery_survey_analyses/surveydata'):
    id_to_name,nominalvars=setup_itemid_dict()
    if not os.path.exists(outdir):
        os.mkdir(outdir)

    unique_items=list(data.item_id.unique())
    surveydata=pandas.DataFrame({'worker':list(data.worker.unique())})
    for i in unique_items:
        matchitem=data.query('item_id=="%s"'%i)
        matchitem=pandas.DataFrame({'worker':matchitem.worker,i:matchitem.response})
        surveydata=surveydata.merge(matchitem,on='worker',how='outer')

    surveydata_renamed=surveydata.rename(columns=id_to_name)
    surveydata_renamed.to_csv(os.path.join(outdir,'demographics.tsv'),sep='\t',index=False)
    for v in nominalvars:
        del surveydata[v]
    surveydata_renamed=surveydata.rename(columns=id_to_name)
    surveydata_renamed.to_csv(os.path.join(outdir,'demographics_ordinal.tsv'),sep='\t',index=False)

    return outdir

if __name__=='__main__':
    id_to_name,nominalvars=setup_itemid_dict()
    data,basedir=get_data()
    demog_items=get_demog_items(data)
    demog_metadata,metadatdir=save_metadata(demog_items)
    data=add_demog_item_labels(data)
    datadir=save_demog_data(data,demog_metadata)
