from app import db
import random
import string
from app.models.models import Ecoli, Yersinia, Campylobacter, Salmonella, \
    Core_Schemas, Report
import fast_mlst_functions
import datetime
import subprocess
from sqlalchemy import cast, Integer

from config import wg_index_correspondece, core_index_correspondece, \
    core_headers_correspondece, wg_headers_correspondece, \
    allele_classes_to_ignore, core_increment_profile_file_correspondece, \
    wg_increment_profile_file_correspondece, classification_levels

'''
Database Functions:
    - Classify a profile based on Fast-MLST (https://github.com/aplf/fast-mlst) 
    by using the closest strain classifier from the profiles db 
'''

database_correspondece = {"E.coli": Ecoli, "Yersinia": Yersinia}


def tab_profile_from_db(strain_id, database, headers_file_path,
                        profile_tab_file_path):

    count_headers = 0

    strain_to_use = db.session.query(database)\
        .filter(database.name == strain_id).first()

    if strain_to_use:
        allelic_profile = strain_to_use.allelic_profile
        profile_array = []

        with open(profile_tab_file_path, 'w') as w:

            if headers_file_path is not None:
                with open(headers_file_path, 'rtU') as reader:
                    for i, line in enumerate(reader):
                        count_headers += 1
                        if i != 0:
                            profile_array\
                                .append(allelic_profile[line.rstrip()])
                        else:
                            profile_array.append(str(i+1))
                w.write('\t'.join(profile_array))

    return profile_tab_file_path, count_headers


def get_profiles(strain_ids, database_name):

    file_name = ''.join(random.choice(string.ascii_uppercase + string.digits)
                        for _ in range(8))

    core_profle_path = "./chewbbaca_database_profiles/query_files/" + \
                        file_name + "_core.tab"

    wg_profle_path = "./chewbbaca_database_profiles/query_files/" + \
                       file_name + "_wg.tab"

    to_replace = allele_classes_to_ignore
    firstTime = True
    strain_ids = strain_ids.split(",")
    profiles = [[], []]
    headers_profile = []

    for s_id in strain_ids:
        strain_entry = db.session.query(database_correspondece[database_name])\
            .filter(database_correspondece[database_name].name == s_id).first()

        if strain_entry:

            core_profile = []
            core_header = []
            wg_header = []
            wg_profile = []
            count_core = 0

            strain_allele_profile = strain_entry.allelic_profile

            with open(core_headers_correspondece[database_name], 'r') as reader:
                for i, line in enumerate(reader):
                    count_core += 1
                    if line.rstrip() == "FILE":
                        core_header.append(line.rstrip())
                        core_profile.append(strain_entry.name)
                    else:
                        if line.rstrip() in strain_allele_profile:
                            core_header.append(line.rstrip())
                            core_profile.append(
                                strain_allele_profile[line.rstrip()])

            profiles[0].append(core_profile)

            with open(wg_headers_correspondece[database_name], 'r') as reader:
                for i, line in enumerate(reader):
                    if line.rstrip() == "FILE":
                        wg_header.append(line.rstrip())
                        wg_profile.append(strain_entry.name)
                    else:
                        if line.rstrip() in strain_allele_profile:
                            wg_header.append(line.rstrip())
                            wg_profile.append(
                                    strain_allele_profile[line.rstrip()])

            profiles[1].append(wg_profile)

            if firstTime:
                headers_profile.append(core_header)
                headers_profile.append(wg_header)
                firstTime = False

    write_headers = True

    with open(core_profle_path, 'w') as writer:

        for x in profiles[0]:
            if write_headers:
                string_headers_list = "\t".join(headers_profile[0])
                writer.write(string_headers_list + "\n")
                write_headers = False

            string_list = "\t".join(x)
            writer.write(string_list + "\n")

    write_headers = True

    with open(wg_profle_path, 'w') as writer:

        for x in profiles[1]:
            if write_headers:
                string_headers_list = "\t".join(headers_profile[1])
                writer.write(string_headers_list + "\n")
                write_headers = False

            string_list = "\t".join(x)
            writer.write(string_list + "\n")

    file_paths = [core_profle_path, wg_profle_path]
    file_names = ["cg_profile.tab", "wg_profile.tab"]
    json_data = [headers_profile, profiles]

    return {"file_paths": file_paths, "file_names": file_names,
            "json": json_data}


def classify_profile(allcall_results, database_name, sample, job_id):

    file_name = ''.join(random.choice(string.ascii_uppercase + string.digits)
                        for _ in range(8))

    query_profle_path = "./chewbbaca_database_profiles/query_files/" +\
                        file_name + ".tab"

    query_profle_path_wg = "./chewbbaca_database_profiles/query_files/" +\
                           file_name + "_wg.tab"

    headers_profile = []
    headers = []

    strain_allele_profile = {}

    to_replace = allele_classes_to_ignore

    profile_hey = ""
    profile_data = allcall_results["cagao"][0]

    for key in allcall_results["cagao"][0]:
        if key != "header":
            profile_hey = key
            break

    headers = profile_data["header"]
    profile = profile_data[key]

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
                core_profile.append(sample.replace(" ", "_"))
            else:
                include_index = headers.index(line.rstrip())
                if include_index > -1:
                    core_profile.append(profile[include_index])

    with open(wg_headers_correspondece[database_name], 'r') as reader:
        for i, line in enumerate(reader):
            if line.rstrip() == "FILE":
                wg_profile.append(sample.replace(" ", "_"))
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

    # First level classification
    closest_profiles = fast_mlst_functions.get_closest_profiles(
        query_profle_path, core_index_correspondece[database_name],
        classification_levels[database_name][0])

    # First level classification
    closest_profiles_2 = fast_mlst_functions.get_closest_profiles(
        query_profle_path, core_index_correspondece[database_name],
        classification_levels[database_name][1])

    # Total closest ids on first level
    closest_ids = []
    for i, x in enumerate(closest_profiles):
        closest_ids.append(closest_profiles[i].split("\t")[0])

    # Total closest ids on second level
    closest_ids_2 = []
    for i, x in enumerate(closest_profiles_2):
        closest_ids_2.append(closest_profiles_2[i].split("\t")[0])

    # Closest on first level
    if len(closest_profiles) == 0:
        first_closest = [None]
    else:
        # ID\tDIFFERENCES
        first_closest = closest_profiles[0].split("\t")

    # Closest on second level
    if len(closest_profiles_2) == 0:
        first_closest_2 = [None]
    else:
        # ID\tDIFFERENCES
        first_closest_2 = closest_profiles_2[0].split("\t")

    print "Closest first level:" + str(first_closest[0])
    print "Closest second level:" + str(first_closest_2[0])

    if sample.replace(" ", "_") in closest_ids or sample.replace(" ", "_") in\
            closest_ids_2:
        print "ALREADY ON DB AND INDEX"
        return True
    else:
        # Get Id of closest at first level
        database_entry = db.session.query(
            database_correspondece[database_name]).filter(
                database_correspondece[database_name].name == first_closest[0]
            ).first()

        # Get Id of closest at second level
        database_entry_2 = db.session.query(
            database_correspondece[database_name]).filter(
            database_correspondece[database_name].name == first_closest_2[0]
        ).first()

        # Get classification of closets at first level or get the last
        # classifier
        if database_entry:
            classification = database_entry.classifier_l1
        else:
            highest_classifier = db.session.query(
                database_correspondece[database_name]).filter(
                database_correspondece[database_name].classifier_l1 != "undefined")\
                .order_by(cast(database_correspondece[database_name].classifier_l1, Integer)
                .desc()
            ).first()

            if highest_classifier:
                classification = highest_classifier.classifier_l1

                if "New_" in classification:
                    classification = classification.split("_")[1]

                classification = str(int(classification)+1)

            else:
                classification = "P_" + job_id.split("_")[0]

        print classification

        # Get classification of closets at second level or get the last
        # classifier
        if database_entry_2:
            classification_2 = database_entry_2.classifier_l2
        else:
            highest_classifier_2 = db.session.query(
                database_correspondece[database_name]).filter(
                database_correspondece[
                    database_name].classifier_l2 != "undefined") \
                .order_by(
                cast(database_correspondece[database_name].classifier_l2,
                     Integer)
                .desc()
                ).first()

            if highest_classifier_2:
                classification_2 = highest_classifier_2.classifier_l2

                if "New_" in classification_2:
                    classification_2 = classification_2.split("_")[1]

                classification_2 = str(int(classification_2) + 1)

            else:
                classification_2 = "P_" + job_id.split("_")[0]

        print classification_2

        try:
            new_database_entry = database_correspondece[database_name](
                name=sample.replace(" ", "_"),
                classifier_l1=classification,
                classifier_l2=classification_2,
                allelic_profile=strain_allele_profile,
                strain_metadata={},
                platform_tag="FP",
                timestamp=datetime.datetime.utcnow()
            )

            db.session.add(new_database_entry)
            db.session.commit()

        except Exception as e:
            print "ERRO"

        print "ADDED TO DB..."

        # FOR CORE GENOME INDEX
        print "UPGRADING CG INDEX"

        myoutput = open(core_increment_profile_file_correspondece[database_name]
                        + ".out", 'w')

        command = 'cat '+\
                  core_increment_profile_file_correspondece[database_name] + \
                  ' '+query_profle_path

        command = command.split(' ')

        print command

        proc = subprocess.Popen(command, stdout=myoutput,
                                stderr=subprocess.PIPE)

        stdout, stderr = proc.communicate()

        command = 'mv ' + \
                  core_increment_profile_file_correspondece[database_name]\
                  + ".out " + \
                  core_increment_profile_file_correspondece[database_name]

        command = command.split(' ')

        print command

        proc2 = subprocess.Popen(command, stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE)
        stdout, stderr = proc2.communicate()

        status = fast_mlst_functions\
            .update_index(core_increment_profile_file_correspondece[database_name],
                          core_index_correspondece[database_name])

        # FOR WG INDEX
        print "UPGRADING WG INDEX"

        myoutput_wg = open(
            wg_increment_profile_file_correspondece[database_name] + ".out",
            'w')

        command = 'cat '+wg_increment_profile_file_correspondece[database_name]\
                  + ' ' + query_profle_path_wg

        command = command.split(' ')

        print command

        proc3 = subprocess.Popen(command, stdout=myoutput_wg,
                                 stderr=subprocess.PIPE)

        stdout, stderr = proc3.communicate()

        command = 'mv '+wg_increment_profile_file_correspondece[database_name]\
                  + ".out "+\
                  wg_increment_profile_file_correspondece[database_name]

        command = command.split(' ')

        print command

        proc4 = subprocess.Popen(command, stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE)
        stdout, stderr = proc4.communicate()

        status = fast_mlst_functions\
            .update_index(wg_increment_profile_file_correspondece[database_name],
                          wg_index_correspondece[database_name])

        print "INDEX UPDATED"
