"""
This module is used for the reading LabView Measurement File

Author: Janko Slavič et al. (janko.slavic@fs.uni-lj.si)
"""
from os import path
import pickle
import numpy as np

__version__ = '1.30'


class LVMFormatError(Exception):
    pass


def _lvm_pickle(filename):
    """ Reads pickle file (for local use)

    :param filename: filename of lvm file
    :return lvm_data: dict with lvm data
    """
    p_file = '{}.pkl'.format(filename)
    pickle_file_exist = path.exists(p_file)
    original_file_exist = path.exists(filename)
    if pickle_file_exist and original_file_exist:
        read_pickle = path.getctime(p_file) > path.getctime(filename)
    if not original_file_exist:
        read_pickle = True
    lvm_data = False
    if pickle_file_exist and read_pickle:
        f = open(p_file, 'rb')
        lvm_data = pickle.load(f)
        f.close()
    return lvm_data


def _lvm_dump(lvm_data, filename, protocol=-1):
    """ Dump lvm_data dict to disc

    :param lvm_data: lvm data dict
    :param filename: filename of the lvm file
    :param protocol: pickle protocol
    """
    p_file = '{}.pkl'.format(filename)
    output = open(p_file, 'wb')
    pickle.dump(lvm_data, output, protocol=protocol)
    output.close()


def _read_lvm_base(filename):
    """ Base lvm reader. Should be called from ``read``, only

    :param filename: filename of the lvm file
    :return lvm_data: lvm dict
    """
    with open(filename, 'r', encoding="utf8", errors='ignore') as f:
        lvm_data = read_lines(f)
    return lvm_data


def get_separator(lines):
    """ Search the LVM header for the separator header

    :param lines: lines of lvm file
    :return separator: separator for this lvm
    """
    # Search for separator header
    for line in lines:
        # Strip new line
        line = line.replace('\r', '').replace('\n', '')
        if line == 'Separator\tTab':
            lines.seek(0)
            return '\t'
        elif line == 'Separator,Comma':
            lines.seek(0)
            return ','

    raise LVMFormatError("Unable to find Separator header")


def read_header(lines):
    """ Read the LVM header and return relevant information

    :param lines: lines of lvm file
    :return lvm_header, data_header: information on lvm data
    """

    separator = get_separator(lines)

    lvm_header = dict()
    data_header = dict()

    # First header is the LVM header
    header = lvm_header

    for line in lines:
        # Strip new line
        line = line.replace('\r', '').replace('\n', '')
        # Reached end of lvm header -> switch to data header
        if header is lvm_header and line.startswith('***End_of_Header***'):
            header = data_header
            continue
        # Reached end of data header -> return both headers
        elif line.startswith('***End_of_Header***'):
            return lvm_header, data_header

        # Skip blank lines
        if line.startswith(separator):
            continue

        key, *data = line.split(separator)

        if key == 'Separator':
            header[key] = {'Comma': ',', 'Tab': '\t'}[data[0]]
        else:
            if len(data) == 1:
                data = data[0]
            header[key] = data

    # Should return from inside for loop
    raise LVMFormatError("Failed to parse header")


def read_lines(lines):
    """ Read lines of strings.

    :param lines: lines of the lvm file
    :return lvm_data: lvm dict
    """
    lvm_data = dict()

    # Read header data
    lvm_header, data_header = read_header(lines)
    lvm_data['lvm_header'] = lvm_header
    lvm_data['data_header'] = data_header

    # Check if Decimal Separator header exists
    if 'Decimal_Separator' not in lvm_header:
        lvm_header['Decimal_Separator'] = '.'

    def to_float(a):
        try:
            return float(a.replace(lvm_header['Decimal_Separator'], '.'))
        except:
            return np.nan

    # First line after headers should be column names
    # Will begin with 'X_Value'
    columnNames = next(lines).replace('\r', '').replace('\n', '')
    if not columnNames.startswith('X_Value'):
        raise LVMFormatError("Failed to read column names")

    data_header['Columns'] = columnNames.split(lvm_header['Separator'])

    # Create the channels from the data header
    X_channel = None

    lvm_data['Channels'] = []
    channel_no = 0

    for i in range(len(data_header['Columns'])):
        if data_header['Columns'][i] == 'X_Value':
            channel = {
                'Name': data_header['X_Dimension'][channel_no],
                'Data': [],
                'X Channel': None
            }
            # Set this channel as the X channel for the next channels
            X_channel = channel
        elif data_header['Columns'][i] == 'Comment':
            channel = {
                'Name': 'Comment',
                'Data': [],
            }
        else:
            channel = {
                'Name': data_header['Columns'][i],
                'Samples': data_header['Samples'][channel_no],
                'Date': data_header['Date'][channel_no],
                'Time': data_header['Time'][channel_no],
                'Y Unit': (data_header['Y_Unit_Label'][channel_no]
                           if 'Y_Unit_Label' in data_header else None),
                'X Dimension': data_header['X_Dimension'][channel_no],
                'X0': data_header['X0'][channel_no],
                'Delta X': data_header['Delta_X'][channel_no],
                'Data': [],
                'X Channel': X_channel
            }
            channel_no += 1

        lvm_data['Channels'].append(channel)

    # Read data into channels
    for line in lines:
        line = line.replace('\r', '').replace('\n', '')
        line_sp = line.split(lvm_header['Separator'])
        for i in range(len(lvm_data['Channels'])):
            ch = lvm_data['Channels'][i]
            dp = line_sp[i] if len(line_sp) > i else ''  # fill in blank values
            if ch['Name'] == 'Comment':
                ch['Data'].append(dp if dp else '')
            else:
                ch['Data'].append(to_float(dp))

    for ch in lvm_data['Channels']:
        ch['Data'] = np.asarray(ch['Data'])

    lvm_data['data'] = np.column_stack(
        [ch['Data'] for ch in lvm_data['Channels'] if ch['Name'] != 'Comment'])

    return lvm_data


def read_str(str):
    """
    Parse the string as the content of lvm file.

    :param str:   input string
    :return:      dictionary with lvm data

    Examples
    --------
    >>> import numpy as np
    >>> import urllib
    >>> filename = 'short.lvm' #download a sample file from github
    >>> sample_file = urllib.request.urlopen('https://github.com/ladisk/lvm_read/blob/master/data/'+filename).read()
    >>> str = sample_file.decode('utf-8') # convert to string
    >>> lvm = lvm_read.read_str(str) #read the string as lvm file content
    >>> lvm.keys() #explore the dictionary
    dict_keys(['', 'Date', 'X_Columns', 'Time_Pref', 'Time', 'Writer_Version',...
    """
    return read_lines(str.splitlines(keepends=True))


def read(filename, read_from_pickle=True, dump_file=True):
    """Read from .lvm file and by default for faster reading save to pickle.

    See also specifications: http://www.ni.com/tutorial/4139/en/

    :param filename:            file which should be read
    :param read_from_pickle:    if True, it tries to read from pickle
    :param dump_file:           dump file to pickle (significantly increases performance)
    :return:                    dictionary with lvm data

    Examples
    --------
    >>> import numpy as np
    >>> import urllib
    >>> filename = 'short.lvm' #download a sample file from github
    >>> sample_file = urllib.request.urlopen('https://github.com/ladisk/lvm_read/blob/master/data/'+filename).read()
    >>> with open(filename, 'wb') as f: # save the file locally
            f.write(sample_file)
    >>> lvm = lvm_read.read('short.lvm') #read the file
    >>> lvm.keys() #explore the dictionary
    dict_keys(['', 'Date', 'X_Columns', 'Time_Pref', 'Time', 'Writer_Version',...
    """
    lvm_data = _lvm_pickle(filename)
    if read_from_pickle and lvm_data:
        return lvm_data
    else:
        lvm_data = _read_lvm_base(filename)
        if dump_file:
            _lvm_dump(lvm_data, filename)
        return lvm_data


if __name__ == '__main__':
    import matplotlib.pyplot as plt

    da = read('data/with_comments.lvm', read_from_pickle=False)
    #da = read('data\with_empty_fields.lvm',read_from_pickle=False)
    print(da.keys())
    print('Number of segments:', da['Segments'])

    plt.plot(da[0]['data'])
    plt.show()
