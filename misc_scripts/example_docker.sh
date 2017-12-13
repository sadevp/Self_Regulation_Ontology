# example commands to run parts of SRO analysis using docker.

# DATA PREP SCRIPTS
# assumes you have a $HOME/tmp folder

docker run --rm  -ti sro_dataprep

# calculate exp dvs
data_loc=$HOME/tmp/
output=$HOME/tmp
docker run --rm  \
--mount type=bind,src=$data_loc,dst=/Data \
--mount type=bind,src=$output,dst=/output \
-ti sro_dataprep \
python batch_files/helper_funcs/calculate_exp_DVs.py grit_scale_survey mturk_complete --out_dir /output

# save data
data_loc=$HOME/tmp
output_loc=$HOME/tmp
docker run --rm  \
--mount type=bind,src=$data_loc,dst=/Data \
--mount type=bind,src=$output_loc,dst=/SRO/Data \
-ti sro_dataprep python data_preparation/mturk_save_data.py

# run analysis with example data
output_loc=$HOME/tmp 
exp_id=simon
subset=example
docker run --rm  \
--mount type=bind,src=$output_loc,dst=/output \
-ti sro_dataprep python /SRO/batch_files/helper_funcs/calculate_exp_DVs.py ${exp_id} ${subset} --out_dir /output --hddm_samples 100 --hddm_burn 50 --local_out_dir ${output_loc} 

# run analysis with mounted data
data_loc=$HOME/tmp
output_loc=$HOME/tmp
exp_id=simon
subset=mturk_complete # replace with subset name
docker run --rm  \
--mount type=bind,src=$data_loc,dst=/Data \
--mount type=bind,src=$output_loc,dst=/output \
-ti sro_dataprep python /SRO/batch_files/helper_funcs/calculate_exp_DVs.py ${exp_id} ${subset} --out_dir /output --hddm_samples 1000 --hddm_burn 500 --local_out_dir ${output_loc}