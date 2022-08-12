import os.path
import toml

from mwr_raw2l1.utils.file_utils import abs_file_path


def main(deps_out_file, file_in=None, file_out=None):
    """generate a secondary pyproject.toml for supporting legacy versions of python

    output file will inherit the metadata from file_in and just have modified dependencies according to deps_out_file

    Args:
        deps_out_file: configuration file (.toml) with the dependencies and their versions to match a legacy python
        file_in: the main pyprojet.toml from which the data are inherited. Defalts to the main pyproject.toml
        file_out: filename of the generated secondary pyproject.toml. Defaults to pyproject_pyxxx.toml where xxx is the
            target python version
    """
    if file_in is None:
        file_in = abs_file_path('pyproject.toml')

    # get contents of file_in into x and target dependencies into deps_out
    with open(file_in) as f:
        x = toml.load(f)
    with open(deps_out_file) as f:
        deps_out = toml.load(f)

    # define output filename
    if file_out is None:
        try:
            pyver_str = deps_out['python'].replace('.', '')
        except KeyError:
            raise KeyError("The python version must be specified in '{}'".format(deps_out_file))
        if not pyver_str[0].isdigit():
            if pyver_str[0] == '=':
                pyver_str = pyver_str[1:]
            raise NotImplementedError("'This function is only intended for fixed python versions but got range '{}'"
                                      .format(deps_out['python']))
        bn, ext = os.path.splitext(file_in)
        file_out = bn + '_py' + pyver_str + ext

    # update x with versions of dependencies as specified in dep_ver
    for deptype in ['dependencies', 'dev-dependencies']:
        for dep, info in x['tool']['poetry'][deptype].items():
            if dep not in deps_out:
                raise KeyError("dependency '{}' found in '{}' has no version specified in the '{}' input. "
                               "Please update the dependencies in '{}'".format(dep, file_in, deps_out_file, __file__))
            if type(info) is str:
                x['tool']['poetry'][deptype][dep] = deps_out[dep]
            elif 'version' in info:
                x['tool']['poetry'][deptype][dep]['version'] = deps_out[dep]
            else:
                raise ValueError("unexpected format of dependency '{}' in '{}'".format(dep, file_in))

    # output updated x to file_out
    with open(file_out, 'w') as f:
        toml.dump(x, f)


if __name__ == '__main__':
    main('dependencies_py368.toml')
