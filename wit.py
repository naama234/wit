from distutils.dir_util import copy_tree
from datetime import datetime
import pytz
import os
import sys
import random
import time
import filecmp
import shutil
from graphviz import Digraph
import fileinput

class witFolderNotFound(Exception):
    pass

class Wit:
    def __init__(self):
        self.current_path = os.getcwd()
        self.images_folder = os.path.join(os.getcwd(), '.wit', 'images')
        self.staging_area_folder = os.path.join(os.getcwd(), '.wit', 'staging_area')
        self.references_file_path = os.path.join(os.getcwd(), '.wit', 'references.txt')
        self.activated_file_path = os.path.join(os.getcwd(), '.wit', 'activated.txt')
        self.chars_list = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '0', 'a', 'b', 'c', 'd', 'e', 'f']

    def set_activated_file(self, branch_name):
        with open(self.activated_file_path, 'w') as activated_file:
            activated_file.write(branch_name)

    def init(self):
        wit_folder = os.path.join(self.current_path, '.wit')
        if os.path.isdir(wit_folder):
            return
        os.mkdir(wit_folder)
        folders_to_make = ['images', 'staging_area']
        for folder in folders_to_make:
            new_folder = os.path.join(wit_folder, folder)
            os.mkdir(new_folder)
        self.set_activated_file('master')

    def check_if_wit_dict_exist(self):
        folders_list = self.current_path.split(os.sep)
        for i in range(len(folders_list)):
            cur_path = folders_list[0: i + 1]
            cur_path.append('.wit')
            wit_folder = os.sep.join(cur_path)
            if os.path.isdir(wit_folder):
                return wit_folder
        return None

    def add(self, path):
        try:
            if self.check_if_wit_dict_exist():
                target =  os.path.join(self.staging_area_folder, os.path.basename(path))
                if os.path.isdir(path):
                    os.makedirs(target)
                    copy_tree(path, target)
                elif os.path.isfile(path):
                    shutil.copyfile(path, target)
            else:
                raise witFolderNotFound
        except witFolderNotFound:
            print("Error: can\'t find .wit folder")

    def make_name_for_commit(self):
        new_name = ''
        i = 0
        while i < 40:
            new_name += random.choice(self.chars_list)
            i = i +1
        return new_name

    def make_time_for_commit_file(self):
        format_gmt = str(datetime.now(pytz.timezone('Asia/Kolkata')))
        format_gmt_split = format_gmt.split('+')
        return time.ctime() + " +" + format_gmt_split[1]

    def get_commit_from_ref(self, name):
        if os.path.isfile(self.references_file_path):
            with open(self.references_file_path, 'r') as references_file:
                for line in references_file.readlines():
                    if name in line:
                        split_line = line.split('=')
                        return split_line[1].replace('\n', ' ').strip()
        return None

    def find_parents_in_merge_commit(self, commit_message):
        answer = []
        answer.append(self.get_commit_from_ref('head'))
        splited_commit_message = commit_message.split(' ')
        branch_name = splited_commit_message[2]
        branch_commit = self.get_commit_from_ref(branch_name)
        answer.append(branch_commit)
        return answer

    def set_parents_for_commit_file(self, commit_message):
        answer = []
        if 'merge' in commit_message:
            return self.find_parents_in_merge_commit(commit_message)
        else:
            if not self.get_commit_from_ref('head'):
                return None
            else:
                answer.append(self.get_commit_from_ref('head'))
                return answer

    def make_commit_file(self, commit_id, message):
        cur_time = self.make_time_for_commit_file()
        file_name = os.path.join(self.images_folder, commit_id + ".txt")
        parents = self.set_parents_for_commit_file(message)
        if not parents:
            parents = ['None']
        txt_in_file = "parents=" + ', '.join(parents) + "\ndate=" + cur_time + " \nmessage=" + message
        with open(file_name, "w+") as commit_file:
            commit_file.write(txt_in_file)

    def add_plus_sign(self, item1, item2):
        return item1 + "=" + item2

    def update_line_in_ref(self, name, old_commit_id, new_commit_id):
        new_line = self.add_plus_sign(name, new_commit_id)
        line_to_search = self.add_plus_sign(name, old_commit_id)
        with fileinput.FileInput(self.references_file_path, inplace=True, backup='.bak') as file:
            for line in file:
                print(line.replace(line_to_search, new_line), end='')

    def get_activated_branch(self):
        with open(self.activated_file_path, 'r') as activated_file:
            return activated_file.read()

    def write_to_ref_file_if_empty(self, commit_id):
        with open(self.references_file_path, 'w') as references_file:
            references_file.write("head=" + commit_id + "\n")
            references_file.write("master=" + commit_id + "\n")

    def update_references_in_commit(self, commit_id):
        head_commit_id = self.get_commit_from_ref('head')
        activated_branch = self.get_activated_branch()
        master_commit_id = self.get_commit_from_ref('master')
        if master_commit_id == head_commit_id and activated_branch == 'master':
            self.update_line_in_ref('head', head_commit_id, commit_id)
            self.update_line_in_ref('master', master_commit_id, commit_id)
        else:
            current_id_from_branch = self.get_commit_from_ref(activated_branch)
            if current_id_from_branch == head_commit_id:
                self.update_line_in_ref(activated_branch, current_id_from_branch, commit_id)
            self.update_line_in_ref('head', head_commit_id, commit_id)

    def update_references_in_merge(self, commit_id):
        head_commit_id = self.get_commit_from_ref('head')
        self.update_line_in_ref('head', head_commit_id, commit_id)
        activated_branch = self.get_activated_branch()
        current_id_from_branch = self.get_commit_from_ref(activated_branch)
        self.update_line_in_ref(activated_branch, current_id_from_branch, commit_id)

    def update_references(self, commit_id, message):
        if not os.path.isfile(self.references_file_path):
            self.write_to_ref_file_if_empty(commit_id)
        else:
            if 'merge' in message:
                self.update_references_in_merge(commit_id)
            else:
                self.update_references_in_commit(commit_id)

    def commit(self, message):
        if self.check_if_wit_dict_exist():
            commit_id = self.make_name_for_commit()
            commit_folder = os.path.join(self.images_folder, commit_id)
            os.mkdir(commit_folder)
            self.make_commit_file(commit_id, message)
            copy_tree(self.staging_area_folder, commit_folder)
            self.update_references(commit_id, message)

    def get_list_of_subdirectories(self, path):
        info_from_path = next(os.walk(path))
        return info_from_path[1]

    def found_file_in_commit_folders(self, file_name):
        commit_ids = self.get_list_of_subdirectories(self.images_folder)
        for commit_folder in commit_ids:
            path_to_found = os.path.join(self.images_folder, commit_folder, file_name)
            if os.path.isfile(path_to_found):
                return path_to_found
            if os.path.isdir(path_to_found):
                return path_to_found
        return None

    def files_to_commit(self):
        answer = []
        files_from_staging = os.listdir(self.staging_area_folder)
        for file_from_staging in files_from_staging:
            answer_from_search = self.found_file_in_commit_folders(file_from_staging)
            if answer_from_search:
                if not filecmp.cmp(answer_from_search, os.path.join(self.staging_area_folder, file_from_staging)):
                    answer.append(file_from_staging)
            else:
                answer.append(file_from_staging)
        return answer

    def changes_not_staged_for_commit(self):
        answer = []
        files_from_staging = os.listdir(self.staging_area_folder)
        for file_from_staging in files_from_staging:
            path_in_staging = os.path.join(self.staging_area_folder, file_from_staging)
            if not filecmp.cmp(os.path.join(self.current_path, file_from_staging), path_in_staging):
                answer.append(file_from_staging)
        return answer

    def untracked_files(self):
        commit_ids = self.get_list_of_subdirectories(self.images_folder)
        answer = []
        for commit_folder in commit_ids:
            files_in_commit_folder = os.listdir(os.path.join(self.images_folder, commit_folder))
            for file_in_commit_folder in files_in_commit_folder:
                path_to_found = os.path.join(self.staging_area_folder, file_in_commit_folder)
                if not os.path.isfile(path_to_found):
                    answer.append(os.path.join(self.images_folder, commit_folder, file_in_commit_folder))
        return answer

    def status(self):
        if self.check_if_wit_dict_exist():
            if self.get_commit_from_ref('head'):
                print('Last commit id: ' + self.get_commit_from_ref('head'))
            print('Changes to be committed: ' + ', '.join(self.files_to_commit()))
            print('Changes not staged for commit: ' + ', '.join(self.changes_not_staged_for_commit()))
            print('Untracked files: ' + ', '.join(self.untracked_files()))

    def check_status_for_checkout(self):
        return self.files_to_commit() or self.changes_not_staged_for_commit()

    def check_if_branch_name_exist(self, input_string):
        if not os.path.isfile(self.references_file_path):
            print('no references file path file')
        else:
            with open(self.references_file_path, 'r') as references_file:
                for line in references_file.readlines():
                    splited_line = line.split("=")
                    if splited_line[0] == input_string:
                        return True
        return False

    def reset_folder(self, src, dst):
        shutil.rmtree(dst)
        copy_tree(src, dst)

    def checkout_commit(self, answer_if_wit_exist, input_of_checkout):
        untracked_files = self.untracked_files()
        folder_contains_wit = answer_if_wit_exist.replace(os.sep + '.wit', '')
        commit_folder = os.path.join(self.images_folder, input_of_checkout)
        for filename in os.listdir(commit_folder):
            long_filename = os.path.join(commit_folder, filename)
            if long_filename not in untracked_files:
                source = os.path.join(commit_folder, filename)
                target = os.path.join(folder_contains_wit, filename)
                shutil.copyfile(source, target)
        self.update_line_in_ref('head', self.get_commit_from_ref('head'), input_of_checkout)
        self.reset_folder(commit_folder, self.staging_area_folder)

    def checkout(self, input_of_checkout):
        answer_if_wit_exist = self.check_if_wit_dict_exist()
        if answer_if_wit_exist:
            if self.check_if_branch_name_exist(input_of_checkout):
                self.set_activated_file(input_of_checkout)
                self.update_line_in_ref('head', self.get_commit_from_ref('head'), self.get_commit_from_ref(input_of_checkout))
            else:
                self.set_activated_file('')
                if not self.check_status_for_checkout():
                    self.checkout_commit(answer_if_wit_exist, input_of_checkout)
                else:
                    print('There are files to commit or flies that are not staged for commit, run wit status for details')

    def get_parents(self, commit_id):
        commit_file_name = os.path.join(self.images_folder, commit_id + ".txt")
        if os.path.isfile(commit_file_name):
            with open(commit_file_name, 'r') as commit_file:
                parent_line = commit_file.readline()
                split_parent_line = parent_line.split('=')
                parents_value = split_parent_line[1].replace('\n', ' ').strip()
                if parents_value != "None":
                    return parents_value.split(', ')
        return None

    def reverse_dict(self, input_dict):
        reversed_dict = {}
        for key, val in input_dict.items():
            reversed_dict[val] = reversed_dict.get(val, []) + [key]
        return reversed_dict

    def names_and_commits_from_ref(self):
        names_and_commits = {}
        with open(self.references_file_path) as f:
            for line in f:
                (key, val) = line.split("=")
                names_and_commits[key] = val.rstrip("\n")
        return self.reverse_dict(names_and_commits)

    def parents_dict(self):
        answer = {}
        files = os.listdir(self.images_folder)
        for i in range(len(files)):
            filename = os.fsdecode(files[i])
            if not filename.endswith(".txt"):
                answer[filename] = []
        for commit_id in answer:
            if self.get_parents(commit_id):
                answer[commit_id].extend(self.get_parents(commit_id))
        return answer

    def graph_nodes(self, parents_dict):
        nodes = []
        for commit_id, parents in parents_dict.items():
            for parent in parents:
                if parent:
                    nodes.append((commit_id[:6], parent[:6]))
        return nodes

    def draw_graph(self, nodes):
        g = Digraph('G', filename='graph.gv')
        g.graph_attr['rankdir'] = 'RL'
        names_and_commits_from_ref = self.names_and_commits_from_ref()
        for commit_id, arrow_names in names_and_commits_from_ref.items():
            for arrow_name in arrow_names:
                g.edge(arrow_name, commit_id[:6])
        g.edges(nodes)
        g.view()

    def graph(self):
        if self.check_if_wit_dict_exist():
            parents_dict = self.parents_dict()
            nodes = self.graph_nodes(parents_dict)
            self.draw_graph(nodes)

    def write_branch_in_references(self, branch_name):
        head_commit = self.get_commit_from_ref('head')
        with open(self.references_file_path, 'a') as references_file:
            references_file.write(branch_name + "=" + head_commit + '\n')

    def branch(self, branch_name):
        if self.check_if_wit_dict_exist():
            self.write_branch_in_references(branch_name)

    def shared_base(self, branch_commit):
        head_commit = self.get_commit_from_ref('head')
        parents_dict = self.parents_dict()
        if parents_dict[head_commit][0] == parents_dict[branch_commit][0]:
            return parents_dict[head_commit][0]
        elif parents_dict[head_commit][0] == branch_commit:
            return branch_commit
        elif parents_dict[branch_commit][0] == head_commit:
            return head_commit
        else:
            while head_commit != branch_commit:
                branch_commit = parents_dict[branch_commit][0]
            return branch_commit
        return None

    def branch_to_shared_base_path(self, branch_commit, shared_base):
        parents_dict = self.parents_dict()
        path = []
        path.append(branch_commit)
        while shared_base != branch_commit:
            if parents_dict[branch_commit][0]:
                branch_commit = parents_dict[branch_commit][0]
            path.append(branch_commit)
        return path

    def update_staging(self, branch_to_shared_base_path):
        for file in os.listdir(self.staging_area_folder):
            for commit_id in branch_to_shared_base_path:
                commit_folder_path = os.path.join(self.images_folder, commit_id)
                path_in_commit = os.path.join(commit_folder_path, file)
                if os.path.isfile(path_in_commit):
                    path_in_staging = os.path.join(self.staging_area_folder, file)
                    if not filecmp.cmp(path_in_staging, path_in_commit):
                        shutil.copyfile(path_in_commit, path_in_staging)

    def merge(self, branch_name):
        if self.check_if_wit_dict_exist():
            if not self.changes_not_staged_for_commit():
                branch_commit = self.get_commit_from_ref(branch_name)
                shared_base = self.shared_base(branch_commit)
                branch_to_shared_base_path = self.branch_to_shared_base_path(branch_commit, shared_base)
                self.update_staging(reversed(branch_to_shared_base_path))
                self.commit('merge branch ' + branch_name)
            else:
                print('staging folder not the same as last commit folder')


if len(sys.argv) == 1:
    exit()
else:
    wit_p = Wit()

    if sys.argv[1] == 'init':
        wit_p.init()

    elif sys.argv[1] == 'add':
        wit_p.add(sys.argv[2])

    elif sys.argv[1] == 'commit':
        wit_p.commit(sys.argv[2])

    elif sys.argv[1] == 'status':
        wit_p.status()

    elif sys.argv[1] == 'checkout':
        wit_p.checkout(sys.argv[2])

    elif sys.argv[1] == 'graph':
        wit_p.graph()

    elif sys.argv[1] == 'branch':
        wit_p.branch(sys.argv[2])

    elif sys.argv[1] == 'merge':
        wit_p.merge(sys.argv[2])

    else:
        print('command not found')