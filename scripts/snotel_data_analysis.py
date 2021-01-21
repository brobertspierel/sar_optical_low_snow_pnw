# -*- coding: utf-8 -*-


#author broberts

#import modules and functions from the other intermittence function script
import os
import snotel_intermittence_functions as combine
import sys
import json
import pickle
import pandas as pd
import glob
import geopandas as gpd
import pyParz
import matplotlib.pyplot as plt
from collections import defaultdict
#import geoplot
from mpl_toolkits.axes_grid1 import make_axes_locatable
from mpl_toolkits.axes_grid1.inset_locator import inset_axes
from matplotlib import colors


def run_model(huc_id,snotel_param_dict,start_date,end_date,sentinel_dict):
	#station_id,param_dict,start_date,end_date,sentinel_dict = args 
	station_ls = []
	for k,v in snotel_param_dict.items(): #go through the possible snotel params  
		station_ls.append(v[huc_id])
		#station_ls.append(v[station_id]) #dict like {'station id:df of years for a param'}
	station_df = pd.concat(station_ls,axis=1) #make a new df that has the years of interest and the snotel params 
	#print(station_df)
	#station_df = station_df.fillna(0)
	for year in range(int(start_date[0:4])+1,int(end_date[0:4])+1): #run analysis annually- this will likely need to be changed
		#select the params for that year 
		try: 
			#print(station_df)
			snotel_year = station_df.loc[:, station_df.columns.str.contains(str(year))]
			#print(snotel_year)
			analysis_df = combine.PrepPlottingData(station_df,None,None,sentinel_dict[str(year)][huc_id]).make_plot_dfs(str(year))
			print(analysis_df)
			for column in analysis_df.columns: 
				if str(year) in column:
					param = column.split('_') #cols are formatted like param_year or stat_param
					analysis_df[f'plus_std_{param[0]}'] = analysis_df[column]+analysis_df[column].std(axis=0)
					analysis_df[f'minus_std_{param[0]}'] = analysis_df[column]-analysis_df[column].std(axis=0)
				elif 'filter' in column: 
					analysis_df[f'plus_std_filter'] = analysis_df[column]+analysis_df[column].std(axis=0)
					analysis_df[f'minus_std_filter'] = analysis_df[column]-analysis_df[column].std(axis=0)
				else: 
					continue
				print(analysis_df)
		except KeyError: 
			print('That file may not exist')
			continue 
		#modify the df with anomalies 

		param_list = ['WTEQ','PRCP','TAVG','SNWD'] #this is what dictates the plots created in the next line. Can be more automated. 
		
		vis = combine.LinearRegression(analysis_df,param_list).vis_relationship(year,huc_id)
		#mlr = combine.LinearRegression(analysis_df).multiple_lin_reg()
		#print(mlr)
def get_years(input_df): 
	years = input_df.columns[:-1] #drop one for the stats column
	years = [int(i.split('_')[1]) for i in years]
	years_min = min(years)
	years_max = max(years)
	return years_min,years_max

def combine_dfs(sites_ids,param_dict,start_date,end_date,year_of_interest,time_step,agg_step): 
	#station_id,param_dict,start_date,end_date = args
	#here the param_dict is like {param:{station_id:df for param}}
	dry = dict(zip(sites_ids, ([] for _ in sites_ids)))
	warm = dict(zip(sites_ids, ([] for _ in sites_ids)))
	warm_dry = dict(zip(sites_ids, ([] for _ in sites_ids)))
	dry_sites = dict(zip(sites_ids, ([] for _ in sites_ids)))
	warm_sites = dict(zip(sites_ids, ([] for _ in sites_ids)))
	warm_dry_sites = dict(zip(sites_ids, ([] for _ in sites_ids)))
	print('Working...')
	for station_id in sites_ids: 

		try:
			wteq_df = param_dict['wteq'][station_id]
			prcp_df = param_dict['prcp'][station_id]
			tavg_df = param_dict['tavg'][station_id]
			start_year = max([get_years(wteq_df)[0],get_years(prcp_df)[0],get_years(tavg_df)[0]]) #get the min year from each of these dataframes and then get the most recent one so there is data for all years
			end_year = min([get_years(wteq_df)[1],get_years(prcp_df)[1],get_years(tavg_df)[1]]) #get the max year from each of the dataframes and then take the min so you get the earliest year that has data for all years
		except KeyError: 
			print('that station is missing')
			continue
		for year in range(start_year,end_year+1):#range(int(start_date[0:4])+1,int(end_date[0:4])+1): the first year will actually be the start of the water year, not the water year itself 
			try: 
				if (time_step.lower() == 'weekly') and (year == year_of_interest): #run for just a year of weeks
					num_weeks = wteq_df.shape[0]/agg_step
					for i in range(0,wteq_df.shape[0]+agg_step,agg_step): #get the number of rows in the dataframe which is the season length. Weekly is set to step by seven right now, not sure if that's the best way of doing it 
						print('i is ', i)
						try: 
							wteq_df_sub = wteq_df.iloc[i:i+agg_step]
							prcp_df_sub = prcp_df.iloc[i:i+agg_step]
							tavg_df_sub = tavg_df.iloc[i:i+agg_step]
						except Exception as e: 
							print('final week')
							wteq_df_sub = wteq_df.iloc[i:]
							prcp_df_sub = prcp_df.iloc[i:]
							tavg_df_sub = tavg_df.iloc[i:]
						wteq_df_sub.drop(columns='stat_WTEQ',inplace=True)
						prcp_df_sub.drop(columns='stat_PREC',inplace=True)
						tavg_df_sub.drop(columns='stat_TAVG',inplace=True)
						wteq_df_sub['week_wteq'] = (wteq_df_sub.max()).mean()
						#print('df with week col added is ', wteq_df_sub)
						prcp_df_sub['week_prcp'] = (prcp_df_sub.max()).mean()
						#print(prcp_df_sub)
						tavg_df_sub['week_tavg'] = (tavg_df_sub[tavg_df_sub > 0 ].count()).mean() 
						#print(tavg_df_sub)
						if (wteq_df_sub[f'WTEQ_{year}'].max() < wteq_df_sub[f'week_wteq'].iloc[0]) and (prcp_df_sub[f'PREC_{year}'].max()<prcp_df_sub['week_prcp'].iloc[0]) and ((tavg_df_sub[f'TAVG_{year}'][tavg_df_sub[f'TAVG_{year}']>0].shape[0])<tavg_df_sub[f'week_tavg'].iloc[0]): #(tavg_df[f'TAVG_{year}'].mean()<tavg_df[f'stat_TAVG'][0]):
							#dry_year.update({station_id:i+7})
							dry_sites[station_id].append(i+agg_step)#dry_sites.update({station_id:dry_sites[station_id].append(i+7)})
						elif (wteq_df_sub[f'WTEQ_{year}'].max() < wteq_df_sub[f'week_wteq'].iloc[0]) and (prcp_df_sub[f'PREC_{year}'].max()>=prcp_df_sub['week_prcp'].iloc[0]): 
							#warm_year.update({station_id:i+7})
							warm_sites[station_id].append(i+agg_step)#warm_sites.update({station_id:warm_sites[station_id].append(i+7)})
						elif (wteq_df_sub[f'WTEQ_{year}'].max() < wteq_df_sub[f'week_wteq'].iloc[0]) and (prcp_df_sub[f'PREC_{year}'].max()<prcp_df_sub['week_prcp'].iloc[0]) and ((tavg_df_sub[f'TAVG_{year}'][tavg_df_sub[f'TAVG_{year}']>0].shape[0])>tavg_df_sub[f'week_tavg'].iloc[0]): 
							#warm_dry_year.update({station_id:i+7})
							warm_dry_sites[station_id].append(i+agg_step)#warm_dry_sites.update({station_id:warm_dry_sites[station_id].append(i+7)})
						else:
							print('passed')

						
				# else: 
				# 	pass
				#run for full seasons
				elif time_step.lower() == 'annual': 
					num_weeks = None
					if (wteq_df[f'WTEQ_{year}'].max() < wteq_df[f'stat_WTEQ'][0]) and (prcp_df[f'PREC_{year}'].max()<prcp_df['stat_PREC'][0]) and ((tavg_df[f'TAVG_{year}'][tavg_df[f'TAVG_{year}']>0].shape[0])<tavg_df[f'stat_TAVG'][0]): #(tavg_df[f'TAVG_{year}'].mean()<tavg_df[f'stat_TAVG'][0]):
						dry[station_id].append(year)#dry.update({station_id:year})
					elif (wteq_df[f'WTEQ_{year}'].max() < wteq_df[f'stat_WTEQ'][0]) and (prcp_df[f'PREC_{year}'].max()>=prcp_df['stat_PREC'][0]): 
						warm[station_id].append(year)#warm.update({station_id:year})
					elif (wteq_df[f'WTEQ_{year}'].max() < wteq_df[f'stat_WTEQ'][0]) and (prcp_df[f'PREC_{year}'].max()<prcp_df['stat_PREC'][0]) and ((tavg_df[f'TAVG_{year}'][tavg_df[f'TAVG_{year}']>0].shape[0])>tavg_df[f'stat_TAVG'][0]): 
						warm_dry[station_id].append(year)#warm_dry.update({station_id:year})
					else: 
						pass
						#print(f'station {station_id} for {year} was normal or above average. The swe value was: {wteq_df[f"WTEQ_{year}"].max()} and the long term mean max value was: {wteq_df[f"stat_WTEQ"][0]}')
				else: 
					pass#print('Double check your time step. It can be weekly or annual')
				
			except Exception as e:
				print(f'error is: {e}')
				#print(f'The year {year} does not exist in the df whose first year is: {wteq_df.columns[0]}')
				continue
			
	#print(dry,warm,warm_dry)
	# 	small_df=
	#inter_list = combined_df.index[df['BoolCol'] == True].tolist()
	#df.filter(like='spike').columns
	#get the full study area
	output_years = {'dry':dry_sites,'warm':warm_sites,'warm_dry':warm_dry_sites}
	output = {'dry':dry,'warm':warm,'warm_dry':warm_dry}
	#print(output)
	#print(output_years)
	return output,output_years,num_weeks

def define_hucs(input_dict,hucs): 
	"""Subdivide results of combine_dfs above by huc level."""
	#print(hucs)
	hucs = {str(k):str(v) for k,v in hucs.items()}
	#print(hucs)

	huc_list = list(set(i for i in hucs.values())) #get a list of the unique hucs 
	#print('huc_list is: ', huc_list)
	#need to make a dictionary of dictionaries of dictionaries ie {huc:{dry:{station_id:[list of ids]}}}
	output_dict = dict(zip(huc_list, ({} for _ in huc_list)))
	# for k,v in output_dict.items(): 
	# 	dry={}
	# 	warm={}
	# 	warm_dry={}
	# 	v.update({'dry':dry,'warm':{},'warm_dry'{}})

	#output_dict = {}
	for i in huc_list:
		dry = {}
		warm = {}
		warm_dry = {}

		for k,v in input_dict.items(): #will get dry, warm,warm_dry
			for k1,v1 in v.items(): #will go through stations that were classified in that group 
				try: 
					if hucs[k1] == i: 
						if k.lower()=='dry': 
							dry.update({k1:v1})
						elif k.lower()=='warm': 
							warm.update({k1:v1})
						elif k.lower()=='warm_dry': 
							warm_dry.update({k1:v1})
						else: 
							pass	
				except Exception as e: 
					print('the error was ',e)
					continue 

		output_dict[i].update({'dry':dry,'warm':warm,'warm_dry':warm_dry})
	#print(output_dict)
	return output_dict

	# for k1,v1 in input_dict.items(): #goes through the three drought type dictionaries  
	# 	for k,v in hucs.items(): 
	# 		dry_dict = {}
	# 		warm_dict = {}
	# 		warm_dry_dict = {}
def snow_drought_ratios(input_dict,num_weeks): 
	output_dict = input_dict
	for k,v in input_dict.items(): #this is the top level dict of hucs
		for k1,v1 in v.items(): #this is the dict of weeks or years in dry, warm etc for each huc
				v.update({k1:len(v1)/int(num_weeks)})
	#print('output dict is: ')
	#print(output_dict)
	#print('num weeks is: ',num_weeks)
	#.rename(columns=['station_id','weekly_ratio']) 
	# print(warm_dry_df)
	# print(warm_dry_df.shape)

	return output_dict
def reformat_dict(input_dict): 
	return {int(k):round(v,2) for k,v in input_dict.items()}
def plot_snow_drought_ratios(input_dict,pnw_shapefile,huc_shapefile,us_boundary,input_pts_data,year_of_interest):
	#dry_df = pd.DataFrame(input_dict['dry'],index=['weekly_ratio']).T.reset_index().rename(columns={'index':'station_id'})
	#warm_df=pd.DataFrame(input_dict['warm'],index=['weekly_ratio']).T.reset_index().rename(columns={'index':'station_id'}) 
	#warm_dry_df=pd.DataFrame(input_dict['warm_dry'],index=['weekly_ratio']).T.reset_index().rename(columns={'index':'station_id'})
	gdf = gpd.GeoDataFrame(input_pts_data, geometry=gpd.points_from_xy(input_pts_data.lon, input_pts_data.lat)) 
	#print(type(input_dict['dry']))
	#print(input_dict)
	#print(type(gdf['site_num'].iloc[0]))

	gdf['dry'] = gdf['site_num'].map(reformat_dict(input_dict['dry'])) 
	gdf['warm'] = gdf['site_num'].map(reformat_dict(input_dict['warm']))
	gdf['warm_dry'] = gdf['site_num'].map(reformat_dict(input_dict['warm_dry']))
	type_list = ['dry','warm','warm_dry']
	print('gdf is: ')
	print(gdf.dry)
	print(gdf.warm_dry)
	#print(gdf)countries_gdf = geopandas.read_file("package.gpkg", layer='countries')
	#get background shapefiles
	hucs=gpd.read_file(huc_shapefile)
	hucs['coords'] = hucs['geometry'].apply(lambda x: x.representative_point().coords[:]) #add label column to gpd
	hucs['coords'] = [coords[0] for coords in hucs['coords']]

	pnw = gpd.read_file(pnw_shapefile)
	us_bounds = gpd.read_file(us_boundary)
	#df["B"] = df["A"].map(equiv)
	fig, ax = plt.subplots(1, 3,figsize=(18,18))
	#ax = ax.flatten()
	for x in range(3):  
		#divider = make_axes_locatable(ax[x])
		#cax = divider.append_axes("right", size="5%", pad=0.1)
		#cmap = 'Reds'#colors.ListedColormap(['b','g','y','r'])
		#bounds=[0,.25,.5,.75,1]
		#cmap = colors.ListedColormap(['b','g','y','r'])#
		#norm = colors.BoundaryNorm(bounds, cmap)
		divider = make_axes_locatable(ax[x])
		cax = divider.append_axes('right', size='5%', pad=0.05)
		hucs.plot(ax=ax[x],color='lightgray', edgecolor='black')
		pcm=gdf.plot(column=type_list[x],ax=ax[x],legend=True,cax=cax,cmap='Reds',vmin=0,vmax=1)#,norm=norm)
		#fig.colorbar(pcm, cax=cax, orientation='vertical')


		#divider = make_axes_locatable(ax[x])
		#cax = divider.append_axes("right", size="5%", pad=0.1)
		#cbar=fig.colorbar(pcm,cax=cax)
		#ax[x].set_clim(vmin=0, vmax=1)

		if '_' in type_list[x]: 
			drought_type=" ".join(type_list[x].split("_")).capitalize()
			ax[x].set_title(f'Proportion of weeks classified as {drought_type} snow drought \n {year_of_interest} water year')
		else: 
			ax[x].set_title(f'{type_list[x].capitalize()} snow drought \n {year_of_interest} water year')
		for idx, row in hucs.iterrows():
			ax[x].annotate(s=row['huc4'], xy=row['coords'],horizontalalignment='center')
		#add a context map
		axins = inset_axes(ax[0], width="30%", height="40%", loc=4)#,bbox_to_anchor=(.1, .5, .5, .5),bbox_transform=ax[x].transAxes)
		axins.tick_params(labelleft=False, labelbottom=False)
		us_bounds.plot(ax=axins,color='darkgray', edgecolor='black')
		hucs.plot(ax=axins,color='red', edgecolor='black')

	plt.tight_layout()
	plt.show()
	plt.close('all')

def plot_anoms(input_dict,anom_start_date,anom_end_date,state,year_of_interest,time_step,hucs): 
	western = ['1708','1801','1710','1711','1709']
	eastern = ['1701','1702','1705','1703','1601','1707','1706','1712','1704']

	#ax = ax.flatten()

	count1 = 0
	# if count1 <= len(western): 
	fig,ax=plt.subplots(len(western),3,sharex=True,sharey=True,figsize=(15,10))

	for k1,v1 in input_dict.items(): #each of these are now formatted as the huc id is k and then each v1 is a dict of warm,dry,warm dry with each of those a dictionary of stations/years or weeks
		if str(k1[:3]) in western: 
			#print('k1 is: ',k1)
			#print('v1 is: ', v1)
			dry_df=pd.DataFrame(dict([ (k,pd.Series(v)) for k,v in v1['dry'].items()])) #changed from input_dict 
			warm_df=pd.DataFrame(dict([ (k,pd.Series(v)) for k,v in v1['warm'].items()]))
			warm_dry_df=pd.DataFrame(dict([ (k,pd.Series(v)) for k,v in v1['warm_dry'].items()]))
			#pd.DataFrame(dict([ (k,pd.Series(v)) for k,v in d.items() ]))
			dry_stats=pd.Series(dry_df.values.ravel()).dropna().value_counts()
			warm_stats=pd.Series(warm_df.values.ravel()).dropna().value_counts()
			warm_dry_stats=pd.Series(warm_dry_df.values.ravel()).dropna().value_counts()
			
			dry_stats = pd.DataFrame({'time':dry_stats.index,'counts':dry_stats.values})
			warm_stats = pd.DataFrame({'time':warm_stats.index,'counts':warm_stats.values})
			warm_dry_stats = pd.DataFrame({'time':warm_dry_stats.index,'counts':warm_dry_stats.values})
			#pd.DataFrame({'email':sf.index, 'list':sf.values})

			plot_dict = {'dry':dry_stats,'warm':warm_stats,'warm_dry':warm_dry_stats}
			print(plot_dict)
			print('k1 is',k1)
			print('count1 is: ',count1)
			#print(dry_df)
			#print(plot_dict)
			#print(dry_stats)
			#print(dry_df)
			#for i in range(4): #iterate the rows
			count = 0
			try:
				for k,v in plot_dict.items(): 
					ax[count1][count].bar(v.time, v.counts, color='g') #plot by row and then for cols plot three across
					if time_step.lower() == 'weekly': 
						ax[count1][count].set_title(f'HUC {k1} {year_of_interest} weekly \n{k} snow drought')	
					else:
						ax[count1][count].set_title(f'HUC {k1} {k} snow drought')
					count +=1
				count1+=1
					# plt.xticks(rotation=45)
			# else: 
			# 	continue
			except Exception as e: 
				pass
	plt.tight_layout()
	plt.show()
	plt.close('all')
		
	return plot_dict

def create_basin_scale_datasets(state,output_filepath,anom_start_date,anom_end_date,season,anom_bool):
	"""Helper function to take the pickled files that store all the state level snotel data and then make it into something useable for next steps."""
	try: 
		# #params currently considered, either update here or include as a param 
		# param_list = ['WTEQ','PREC','TAVG','SNWD']
		# param_dict = {}

		#read the dfs of each snotel param into a dict for further processing 
		wteq_wy = combine.StationDataCleaning(combine.pickle_opener(
			output_filepath+f'{state}_WTEQ_{anom_start_date}_{anom_end_date}_snotel_data_list'),
			'WTEQ',season)
		prec_wy = combine.StationDataCleaning(combine.pickle_opener(
			output_filepath+f'{state}_PREC_{anom_start_date}_{anom_end_date}_snotel_data_list'),
			'PREC',season)
		tavg_wy = combine.StationDataCleaning(combine.pickle_opener(
			output_filepath+f'{state}_TAVG_{anom_start_date}_{anom_end_date}_snotel_data_list'),
			'TAVG',season)
		snwd_wy = combine.StationDataCleaning(combine.pickle_opener(
			output_filepath+f'{state}_SNWD_{anom_start_date}_{anom_end_date}_snotel_data_list'),
			'SNWD',season)
		
	except FileNotFoundError: 
		raise FileNotFoundError('Something is wrong with the pickled file you requested, double check that file exists and run again')
	#make outputs 
	#water_years=combine.StationDataCleaning(results,parameter,new_parameter,start_date,end_date,season)
	#generate a dictionary with each value being a dict of site_id:df of years of param
	#organize_plots('/vol/v1/general_files/user_files/ben/excel_files/snow_drought_outputs/',season)

	#format snotel data by paramater
	param_dict = {'wteq':wteq_wy.prepare_data(anom_bool,anom_start_date,anom_end_date,state),'prcp':prec_wy.prepare_data(anom_bool,anom_start_date,anom_end_date,state),
	'tavg':tavg_wy.prepare_data(anom_bool,anom_start_date,anom_end_date,state),'snwd':snwd_wy.prepare_data(anom_bool,anom_start_date,anom_end_date,state)}
	return param_dict

def main():
	"""Master function for snotel intermittence from SNOTEL and RS data. 
	Requirements: 
	snotel_intermittence_functions.py - this is where most of the actual work takes place, this script just relies on code in that script 
	snotel_intermittence_master.txt - this is the param file for running all of the snotel/rs functions outlined in the functions script
	run this in a python 3 conda environment and make sure that the climata package is installed

	"""
	
	params = sys.argv[1]
	with open(str(params)) as f:
		variables = json.load(f)
		
		#construct variables from param file
		state_shapefile = variables["state_shapefile"]
		pnw_shapefile = variables["pnw_shapefile"]
		huc_shapefile = variables['huc_shapefile']
		us_boundary = variables['us_boundary']
		epsg = variables["epsg"]
		output_filepath=variables["output_filepath"]
		season = variables["season"]
		csv_dir = variables["csv_dir"]
		stations = variables["stations"]
		parameter = variables["parameter"]
		start_date = variables["start_date"]
		end_date = variables["end_date"]
		anom_start_date = variables["anom_start_date"]
		anom_end_date = variables["anom_end_date"]
		write_out = variables["write_out"]
		pickles = variables["pickles"]
		anom_bool = variables["anom_bool"]
		state_abbr = variables['state_abbr']
		time_step = variables['time_step']
	#run_prep_training = sys.argv[1].lower() == 'true' 
	#get some of the params needed
	stations_df = pd.read_csv(stations)
	#stations_df = stations_df[stations_df['state']==state_abbr] #this might not be the best way to run this, right now it will require changing the state you want 
	sites = combine.make_site_list(stations_df,'huc_08',8)
	sites_full = sites[0] #this is getting the full df of oregon (right now) snotel sites. Changed 10/28/2020 so its just getting all of the site ids
	sites_ids = sites[1] #this is getting a list of just the snotel site ids. You can grab a list slice to restrict how big results gets below. 
	huc_dict = sites[2] #this gets a dict of format {site_id:huc12 id}
	new_parameter = parameter+'_scaled'
	#state = sites_full['state'].iloc[0] #this is just looking into the df created from the sites and grabbing the state id. This is used to query the specific station
	#print('huc_dict is: ', huc_dict)
	#make a csv for sentinel data
	#sites_full.to_csv(f"/vol/v1/general_files/user_files/ben/excel_files/{state}_snotel_data.csv")
	huc_list = list(set(i for i in huc_dict.values())) 
	#print('the len of sites ids is: ',len(sites_ids))
	#create the input data
	if write_out.lower() == 'true': 
		for param in ['WTEQ','PREC','TAVG','SNWD','PRCP','PRCPSA']: #PRCP
			
			print('current param is: ', param)
			input_data = combine.CollectData(stations,param,anom_start_date,anom_end_date,state,sites_ids, write_out,output_filepath)
			#get new data
			pickle_results=input_data.snotel_compiler() #this generates a list of dataframes of all of the snotel stations that have data for a given state
	
	##########################################################################
	filename = output_filepath+f'master_dict_all_states_all_years_all_params_dict_correctly_combined_{season}'
	if not os.path.exists(filename): 
		states_list = []
		for i in ['OR','WA','ID']: 
			print('the stat is now: ',i)

			state_ds = create_basin_scale_datasets(i,output_filepath,anom_start_date,anom_end_date,season,'true') #these are in the form {param:{station:df}}
			print('the dataset looks like: ', state_ds)
			states_list.append(state_ds)
		master_dict = {}
		for j in ['wteq','tavg','prcp','snwd']: 
			vals0 = states_list[0][j] #get the param dict
			vals1 = states_list[1][j]
			vals2 = states_list[2][j]
			new_dict = {**vals0,**vals1,**vals2} #concat the param dicts
			master_dict.update({j:new_dict})
		#master_dict = {**states_list[0],**states_list[1],**states_list[2]}
		pickle_data=pickle.dump(master_dict, open(filename,'ab'))
	
	else: 
		print('That data file already exists, working from pickled version')

	# ##########################################################################
	#this is working and generates the snow drought years
	year_of_interest = 2018

	if os.path.exists(filename): 
		master_param_dict=combine.pickle_opener(filename)
	else: 
		master_param_dict=master_dict
	#print(len(master_param_dict['wteq']))

	
	#test = 	snow_droughts=combine_dfs(sites_ids,param_dict,anom_start_date,anom_end_date,year_of_interest)

	#uncomment to make plot of anomaly years 
	if time_step.lower() == 'annual': 
		plot_data = 0
		snow_drought_filename = output_filepath+f'_{time_step}'+f'dictionary_{season}'
	elif time_step.lower() == 'weekly': 
		plot_data = 1
		snow_drought_filename = output_filepath+f'_{time_step}_{year_of_interest}'+f'dictionary_{season}_{12}_day_aggregation'
	if not os.path.exists(snow_drought_filename): 
		snow_droughts=combine_dfs(sites_ids,master_param_dict,anom_start_date,anom_end_date,year_of_interest,time_step,12)
		pickle_data=pickle.dump(snow_droughts, open(snow_drought_filename,'ab'))
		print('pickled')
	else: 
		snow_droughts=combine.pickle_opener(snow_drought_filename)
		print('working from pickles')
		#print(snow_droughts)
	#get the plot of counts of snow drought by year
	#print(snow_droughts[plot_data])
	#plot snow drought ratios
	#ratios = snow_drought_ratios(snow_droughts[plot_data],snow_droughts[2])
	#visualize = plot_snow_drought_ratios(ratios,pnw_shapefile,huc_shapefile,us_boundary,stations_df,year_of_interest)
	#print(snow_droughts)
	drought_by_basin = define_hucs(snow_droughts[plot_data],huc_dict) #changed from ratios 11/30/2020
	print(drought_by_basin)
	basin_drought_filename = pickles+f'snow_droughts_by_basin_and_type_{season}_{year_of_interest}_{time_step}_{12}_day_aggregation'

	#plot_anoms(drought_by_basin,anom_start_date,anom_end_date,None,year_of_interest,time_step,huc_list)

	#print(drought_by_basin)
	if not os.path.exists(basin_drought_filename): 
		pickle.dump(drought_by_basin, open(basin_drought_filename, 'ab'))
	else: 
		pass
	
if __name__ == '__main__':
    main()

