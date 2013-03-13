import sys;

sys.path.append('..')
sys.path.append('../mq/')

import taskmanager

import gcswift

import os.path, fnmatch

import combine

from subprocess import call


#lists the files in a directory and subdirectories
#this code comes from the Python Cookbook
def listFiles(root, patterns='*', recurse=1, return_folders=0):
    """Lists the files/directories meeting specific requirement
    
    Searches a directory structure along the specified path, looking
    for files that matches the glob pattern. If specified, the search will
    continue into sub-directories.  A list of matching names is returned.
     
    Args:
        | root (string): root directory from where the search must take place
        | patterns (string): glob pattern for filename matching
        | recurse (unt): should the search extend to subdirs of root?
        | return_folders (int): should foldernames also be returned?
        
    Returns:
        | A list with matching file/directory names
        
    Raises:
        | No exception is raised.
    """
    # Expand patterns from semicolon-separated string to list
    pattern_list = patterns.split(';')
    # Collect input and output arguments into one bunch
    class Bunch:
        def __init__(self, **kwds): self.__dict__.update(kwds)
    arg = Bunch(recurse=recurse, pattern_list=pattern_list,
        return_folders=return_folders, results=[])

    def visit(arg, dirname, files):
        # Append to arg.results all relevant files (and perhaps folders)
        for name in files:
            fullname = os.path.normpath(os.path.join(dirname, name))
            if arg.return_folders or os.path.isfile(fullname):
                for pattern in arg.pattern_list:
                    if fnmatch.fnmatch(name, pattern):
                        arg.results.append(fullname)
                        print fullname
                        break
        # Block recursion if recursion was disallowed
        if not arg.recurse: files[:]=[]
    os.path.walk(root, visit, arg)
    return arg.results

print "Scanning Files"
image_files = listFiles('/Users/cmatthew/tmp/WRS2/', patterns='*.b0[743].tif.gz')

for i,f in enumerate(image_files[::-1]):
    percent = (float(i)/len(image_files))*100
    filename = os.path.basename(f)
    dirname = os.path.dirname(f)
    os.chdir(dirname)

    print "[%3.3f]Processing:"%(percent), filename
    sys.stdout.flush()
    pathrow = filename.split('_')[0]
    md5file = filename + '.md5'

    gcswift.swift('upload', pathrow, filename)
    #call('md5sum -b %s > %s'%(filename,md5file), shell=True)
    #assert os.path.exists(md5file), "Output file was not created!"
    #gcswift.swift('upload', pathrow, md5file)

