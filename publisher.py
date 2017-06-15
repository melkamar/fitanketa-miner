from git import Repo
import os
import shutil
from distutils.dir_util import copy_tree
import stat


def del_rw(action, name, exc):
    os.chmod(name, stat.S_IWRITE)
    os.remove(name)


def publish(root, temp_checkout_folder='checkouted_page'):
    if os.path.exists(temp_checkout_folder):
        shutil.rmtree(temp_checkout_folder, onerror=del_rw)

    repo = Repo.clone_from('git@github.com:melkamar/fitanketa-miner.git', temp_checkout_folder, branch='gh-pages')

    # shutil.copy(root, temp_checkout_folder)
    # shutil.copytree()
    copy_tree(root, temp_checkout_folder)

    # os.rmdir(os.path.join(temp_checkout_folder, 'page'))
    # shutil.copy2(root, temp_checkout_folder)

    # repo.index.add([os.path.join(os.getcwd(), temp_checkout_folder, "courses")])
    # repo.index.add()
    repo.git.add('--all')
    repo.index.commit("autocommit")
    repo.remote().push()
