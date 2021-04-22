" Project info related endpoints "

import os
import uuid
import subprocess
import shutil

from flask import (Blueprint, render_template, request, current_app,
                   abort, session, redirect, url_for, g, jsonify,
                   make_response)

from code_dds import db, timestamp
from code_dds.db_code import models
from code_dds.db_code import db_utils
from code_dds.db_code import marshmallows as marmal
from code_dds.crypt.key_gen import project_keygen
from code_dds.utils import login_required, working_directory
from werkzeug.utils import secure_filename
project_blueprint = Blueprint("project", __name__)


@project_blueprint.route("/add_project", methods=["GET", "POST"])
@login_required
def add_project():
    """ Add new project to the database """
    if request.method == "GET":
        return render_template("project/add_project.html")
    if request.method == "POST":
        # Check no empty field from form
        for k in ['title', 'owner', 'description']:
            if not request.form.get(k):
                return render_template("project/add_project.html",
                                       error_message="Field '{}' should not be empty".format(k))

        # Check if the user actually exists
        if request.form.get('owner') not in db_utils.get_full_column_from_table(table='User', column='username'):
            return render_template("project/add_project.html",
                                   error_message="Given username '{}' does not exist".format(request.form.get('owner')))

        project_inst = create_project_instance(request.form)
        # TO DO : This part should be moved elsewhere to dedicated DB handling script
        new_project = models.Project(**project_inst.project_info)
        db.session.add(new_project)
        db.session.commit()
        return redirect(url_for('project.project_info', project_id=new_project.id))


@project_blueprint.route("/<project_id>", methods=["GET"])
@login_required
def project_info(project_id=None):
    """Get the given project's info"""
    project_info = models.Project.query.filter_by(id=project_id).first()
    if not project_info:
        return abort(404)
    proj_facility_name = db_utils.get_facility_column(fid=project_info.facility, column='name')
    files_list = models.File.query.filter_by(project_id=project_id).all()
    if files_list:
        uploaded_data = folder(files_list).generate_html_string()
    else:
        uploaded_data = None
    return render_template("project/project.html", project=project_info, uploaded_data=uploaded_data, proj_facility_name=proj_facility_name)


@project_blueprint.route("upload", methods=["POST"])
@login_required
def data_upload():   
    project_id = request.form.get('project_id', None)
    in_files = validate_file_list(request.files.getlist('files')) or validate_file_list(request.files.getlist('folder'))
    upload_space = os.path.join(current_app.config['UPLOAD_FOLDER'], "{}_T{}".format(project_id, timestamp(ts_format="%y%m%d%H%M%S")))
    if project_id is None:
        status, message = (433, "Project ID not found in request")
    elif not in_files:
        status, message = (434, "No files/folder were selected")
    else:
        os.mkdir(upload_space)
        with working_directory(upload_space):
            upload_file_dest = os.path.join(upload_space, "data")
            os.mkdir(upload_file_dest)
            for in_file in in_files:
                file_target_path = upload_file_dest
                path_splitted = in_file.filename.split("/")
                filename = path_splitted[-1] #TO DO: look into secure naming
                if len(path_splitted) > 1:
                    for p in path_splitted[:-1]:
                        file_target_path = os.path.join(file_target_path, p)
                        if not os.path.exists(file_target_path):
                            os.mkdir(file_target_path)
                in_file.save(os.path.join(file_target_path, filename))
            
            with open("data_to_upload.txt", "w") as dfl:
                dfl.write("\n".join([os.path.join(upload_file_dest, i) for i in os.listdir(upload_file_dest)]))
            
            proc = subprocess.Popen(['dds', 'put', '-c', current_app.config['DDS_CLI_CONFIG'], '-p', project_id, '-spf', "data_to_upload.txt", '--overwrite'],
                                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            out, err = proc.communicate(input=None)
        
        if proc.returncode == 0:
            status, message = (200, "Data susseccfully uploaded to S3")
            try:
                shutil.rmtree(upload_space)
            except:
                print("Couldn't remove upload space '{}'".format(upload_space))
        else:
            status, message = (515, "Couldn't send data to S3")
    
    return make_response(jsonify({'status': status, 'message': message}), status)


########## HELPER CLASSES AND FUNCTIONS ##########


class create_project_instance(object):
    """ Creates a project instance to add in DB"""

    def __init__(self, project_info):
        self.project_info = {
            'id': self.get_new_id(),
            'title': project_info['title'],
            'description': project_info['description'],
            'owner': db_utils.get_user_column_by_username(project_info['owner'], "public_id"),
            'category': 'testing',
            'facility': g.current_user_id,
            'status': 'Ongoing',
            'date_created': timestamp(ts_format="%Y-%m-%d"),
            'pi': 'NA',
            'size': 0
        }
        self.project_info['bucket']="{}_bucket".format(self.project_info['id'])
        pkg = project_keygen(self.project_info['id'])
        prj_keys = pkg.get_key_info_dict()
        self.project_info['public_key'] = prj_keys['public_key']
        self.project_info['private_key'] = prj_keys['private_key']

    def get_new_id(self, id=None):
        facility_ref = db_utils.get_facility_column(fid=session.get('current_user_id'), column='internal_ref')
        facility_prjs = db_utils.get_facilty_projects(fid=session.get('current_user_id'), only_id=True)
        return "{}{:03d}".format(facility_ref, len(facility_prjs)+1)

    def __is_column_value_uniq(self, table, column, value):
        """ See that the value is unique in DB """
        all_column_values = db_utils.get_full_column_from_table(table=table, column=column)
        return value not in all_column_values


class folder(object):
    """ A class to parse the file list and do appropriate ops """

    def __init__(self, file_list):
        self.files = file_list
        self.files_arranged = {}

    def arrange_files(self):
        """ Method to arrange files that reflects folder structure """
        for _file in self.files:
            self.__parse_and_put_file(
                _file.name, _file.size, self.files_arranged)

    def generate_html_string(self, arrange=True):
        """ Generates html string for the files to pass in template """
        if arrange and not self.files_arranged:
            self.arrange_files()

        return self.__make_html_string_from_file_dict(self.files_arranged)

    def __parse_and_put_file(self, file_name, file_size, target_dict):
        """ Private method that actually """
        file_name_splitted = file_name.split('/', 1)
        if len(file_name_splitted) == 2:
            parent_dir, remaining_file_path = file_name_splitted
            if parent_dir not in target_dict:
                target_dict[parent_dir] = {}
            self.__parse_and_put_file(
                remaining_file_path, file_size, target_dict[parent_dir])
        else:
            target_dict[file_name] = file_size

    def __make_html_string_from_file_dict(self, file_dict):
        """ Takes a dict with files and creates html string with <ol> tag """
        _html_string = ""
        for _key, _value in file_dict.items():
            if isinstance(_value, dict):
                div_id = "d{}".format(timestamp(ts_format="%y%m%d%H%M%S%f"))
                _html_string += ("<li> <a class='folder' data-toggle='collapse' href='#{did}' aria-expanded='false' aria-controls='{did}'>{_k}</a> "
                                 "<div class='collapse' id='{did}'>{_v}</div> "
                                 "</li>").format(did=div_id, _k=_key, 
                                 _v=self.__make_html_string_from_file_dict(_value))
            else:
                _html_string += "<li><div class='hovertip'>{_k} <span class='hovertiptext'> {_v}Kb </span></div></li>".format(_k=_key, _v=_value)
        return '<ul style="list-style: none;"> {} </ul>'.format(_html_string)


def validate_file_list(flist):
    """ Helper function to check if the file list from upload have files """
    return False if (len(flist) == 1 and flist[0].filename == "") else flist
