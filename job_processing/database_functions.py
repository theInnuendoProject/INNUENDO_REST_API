from app import app, db
import random
import os
import string
import json
from app.models.models import Ecoli, Yersinia, Campylobacter, Salmonella, Core_Schemas, Report
import fast_mlst_functions
import datetime
import subprocess

from config import wg_index_correspondece, core_index_correspondece, core_headers_correspondece, wg_headers_correspondece, allele_classes_to_ignore, core_increment_profile_file_correspondece, wg_increment_profile_file_correspondece

'''
Database Functions:
	- Classify a profile based on Fast-MLST (https://github.com/aplf/fast-mlst) by using the closest strain classifier from the profiles db 
'''

database_correspondece = {"E.coli":Ecoli}


def tab_profile_from_db(strain_id, database, headers_file_path, profile_tab_file_path):

	count_headers = 0
	
	strain_to_use = db.session.query(database).filter(database.name == strain_id).first()

	if strain_to_use:
		allelic_profile = strain_to_use.allelic_profile
		profile_array = []

		with open(profile_tab_file_path, 'w') as w:

			if headers_file_path != None:
				with open(headers_file_path, 'rtU') as reader:
					for i, line in enumerate(reader):
						count_headers += 1
						if i != 0:
							profile_array.append(allelic_profile[line.rstrip()])
						else:
							profile_array.append(str(i+1))
				w.write('\t'.join(profile_array))

	return profile_tab_file_path, count_headers



def classify_profile(job_id, database_name):

	report = db.session.query(Report).filter(Report.job_id == job_id).first()

	file_name = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(8))
	query_profle_path = "./chewbbaca_database_profiles/query_files/" + file_name + ".tab"
	query_profle_path_wg = "./chewbbaca_database_profiles/query_files/" + file_name + "_wg.tab"

	if not report:
		print "REPORT DOES NOT EXIST"
	else:
		headers_profile = []
		headers = []

		strain_allele_profile = {}

		to_replace = allele_classes_to_ignore

		#to_replace = {"LNF": "0", "INF-": "", "NIPHEM": "0", "NIPH": "0", "LOTSC": "0", "PLOT3": "0", "PLOT5": "0", "ALM": "0", "ASM": "0"}
		headers = headers_profile + report.report_data["run_output"]["header"]
		profile = report.report_data["run_output"]["run_output.fasta"]

		core_profile = []
		wg_profile = []
		count_core = 0
		count_entrou = 0

		for i, header in enumerate(headers):
			strain_allele_profile[header] = profile[i]
		
		with open(core_headers_correspondece[database_name], 'r') as reader:
			for i, line in enumerate(reader):
				count_core+=1
				if line.rstrip() == "FILE":
					core_profile.append(report.sample_name.replace(" ", "_"))
				else:
					include_index = headers.index(line.rstrip())
					if include_index > -1:
						core_profile.append(profile[include_index])


		with open(wg_headers_correspondece[database_name], 'r') as reader:
			for i, line in enumerate(reader):
				if line.rstrip() == "FILE":
					wg_profile.append(report.sample_name.replace(" ", "_"))
				else:
					include_index = headers.index(line.rstrip())
					if include_index > -1:
						wg_profile.append(profile[include_index])

		string_list = "\t".join(core_profile)

		string_list_wg = "\t".join(wg_profile)


		for k,v in to_replace.iteritems():
			string_list = string_list.replace(k,v)
			string_list_wg = string_list_wg.replace(k,v)


		with open(query_profle_path, 'w') as writer:
			writer.write(string_list+"\n")

		with open(query_profle_path_wg, 'w') as writer:
			writer.write(string_list_wg+"\n")


		closest_profiles = fast_mlst_functions.get_closest_profiles(query_profle_path, core_index_correspondece[database_name], count_core/2)


		closest_ids = []
		for i, x in enumerate(closest_profiles):
			closest_ids.append(closest_profiles[i].split("\t")[0])
		
		if len(closest_profiles) == 0:
			classification = "undefined"
			print "HERE"
			first_closest = [None]
		else:
			#ID\tDIFFERENCES
			first_closest = closest_profiles[0].split("\t")

		print "Closest:" + first_closest[0]

		if report.sample_name.replace(" ", "_") in closest_ids:
			print "ALREADY ON DB AND INDEX"
			return True
		else:		
			database_entry = db.session.query(database_correspondece[database_name]).filter(database_correspondece[database_name].name == first_closest[0]).first()

			if database_entry:
				classification = database_entry.classifier
			else:
				classification = "New_" + report.job_id.split("_")[0]

			print classification

			try:
				new_database_entry = database_correspondece[database_name](name = report.sample_name.replace(" ", "_"), classifier = classification, allelic_profile = strain_allele_profile, strain_metadata = {}, platform_tag = "FP", timestamp = datetime.datetime.utcnow())
				
				db.session.add(new_database_entry)
				db.session.commit()
			except Exception as e:
				print "ERRO"

			print "ADDED TO DB..."

			#FOR CORE GENOME INDEX
			print "UPGRADING CG INDEX"

			myoutput = open(core_increment_profile_file_correspondece[database_name] + ".out", 'w')

			command = 'cat '+core_increment_profile_file_correspondece[database_name]+' '+query_profle_path;
			command = command.split(' ')
			print command
			proc = subprocess.Popen(command, stdout=myoutput, stderr=subprocess.PIPE)
			stdout, stderr = proc.communicate()

			command = 'mv '+core_increment_profile_file_correspondece[database_name] + ".out "+core_increment_profile_file_correspondece[database_name];
			command = command.split(' ')
			print command

			proc2 = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
			stdout, stderr = proc2.communicate()

			status = fast_mlst_functions.update_index(core_increment_profile_file_correspondece[database_name], core_index_correspondece[database_name])

			#FOR WG INDEX
			print "UPGRADING WG INDEX"

			myoutput_wg = open(wg_increment_profile_file_correspondece[database_name] + ".out", 'w')

			command = 'cat '+wg_increment_profile_file_correspondece[database_name]+' '+query_profle_path_wg;
			command = command.split(' ')
			print command
			proc3 = subprocess.Popen(command, stdout=myoutput_wg, stderr=subprocess.PIPE)
			stdout, stderr = proc3.communicate()

			command = 'mv '+wg_increment_profile_file_correspondece[database_name] + ".out "+wg_increment_profile_file_correspondece[database_name];
			command = command.split(' ')
			print command

			proc4 = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
			stdout, stderr = proc4.communicate()

			status = fast_mlst_functions.update_index(wg_increment_profile_file_correspondece[database_name], wg_index_correspondece[database_name])

			print "INDEX UPDATED"
			

	##ADD TO DB AND UPDATE INDEX




