"""
This module is used for the reading LabView Measurement File

Author: Janko Slavič et al. (janko.slavic@fs.uni-lj.si)
"""
from os import path
from datetime import datetime
import pickle
import numpy as np

import lvm_format as lvm

__version__ = '1.40'


class LVMFormatError(Exception):
    pass

def _lvm_float(value, decsep):
    if value == '':
        return None
    try:
        return float(value.replace(decsep, '.'))
    except ValueError:
        return None

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
    :return separator, buffer: separator for this lvm, lines read in search
    """

    buffer = []
    # Search for separator header
    for line in lines:
        # Look for Separator header
        if line.startswith('Separator'):
            # Return the character after the 'Separator' word
            return line[len('Separator')], buffer
        # If we hit the end of the header without
        # finding header assume default (tab)
        elif line.startswith(lvm.END_OF_HEADER):
            return lvm.FILE_HEADERS['Separator']['default'], buffer
        # Otherwise save the line to read in header parser
        else:
            buffer.append(line)
    # EOF
    raise LVMFormatError("Unable to find Separator header")

def skip_special_block(lines):
    line = next(lines, None)
    while line != None and not line.startswith(lvm.SPECIAL_BLOCK_END):
        line = next(lines, None)

def validate_header(headers, spec):
    """ Validates the header contains all required fields.
        Throws LVMFormatError on invalid header.

    :param headers: headers to validate
    :param spec: format to check for
    """

    for h in spec:
        # Header is required but not filled
        if spec[h]['required'] and headers[h] is None:
            raise LVMFormatError(f"Header {h} not found")
        # Header has set options but something else is filled
        elif spec[h]['type'] == 'options' and headers[h] not in spec[h]['options']:
            raise LVMFormatError(f"Header {h} has no option {headers[h]}")

def parse_value(value, vtype, sep, decsep):
    """ Parsers a value based off the expected vtype.
        Returns None on error

    :param value: raw value to parse
    :param vtype: type of value
    :param   sep: separator for file. Used to unescape text
    :param decsep: decimal separator for file. Used to parse time
    :return data: parsed data. None on error
    """

    # Number: either a float or an integer
    if vtype == "number":
        # first convert to float
        data = _lvm_float(value, decsep)
        # then convert to int if able
        if data.is_integer():
            data = int(data)
        return data
    # Integer: Must be an int
    elif vtype == "integer":
        try:
           return int(value)
        except ValueError:
            return None
    # Float: must be a float
    elif vtype == "float":
        return _lvm_float(value, decsep)
    # Options: options will be validated in validate_header
    elif vtype == "options":
        return value
    # Text: text should have escaped separator (e.g., \2C for ',') replaced
    elif vtype == "text":
        sepHex = '\\' + hex(ord(sep))[2:]
        return value.replace(sepHex.upper(), sep).replace(sepHex.lower(), sep)
    # Date: date should be of the format YYYY/MM/DD
    elif vtype == 'date':
        return datetime.strptime(value, lvm.DATE_FORMAT).date()
    # Time: time should be of the format HH:MM:SS.XXX
    elif vtype == 'time':
        # check for microseconds 
        if decsep in value:
            # limit value to only 6 digits of msec as is max of datetime
            t, msec = value.split(decsep)
            if len(msec) > 6:
                msec = msec[:6]
            return datetime.strptime(f"{t}.{msec}", f"{lvm.TIME_FORMAT}.%f").time()
        else:
            return datetime.strptime(value, lvm.TIME_FORMAT).time()
    # Bool: bool should contain either "Yes" or "No" which should map to 
    # True or False
    elif vtype == 'bool':
        if value == "Yes":
            return True
        elif value == "No":
            return False
        else:
            raise None
    # None: Header has no value
    elif vtype == None:
        return ''
    
def read_segment_data(lines, file_header, seg_header, x0=None):
    """ Reads the data portion of the segment. The returned list will contain
    an array for each X column and its related Y columns. E.g., 
        [[[x1,x2,...], [y1,y2,...]], [[x1,x2,...], [y1,y2,...]], comments] 
    The X values will be infered from the seg_header when X_Columns is "No"

    :param lines: lines of file
    :param file_header: header for file
    :param seg_header: header for segment
    :param x0: list of starting X values. Used for same-header segments
    :return seg_data, comments: list of data arrays, list of comments
    """

    samples = seg_header['Samples']
    x_columns = file_header['X_Columns']
    decsep = file_header['Decimal_Separator']

    # Create number of empty lists equal to channels 
    # Each of the channels should contain an x and y list
    seg_data = [[[], []] for _ in range(seg_header['Channels'])]
    comments = []

    # Fill in x0 from segment header
    if x0 is None:
        x0 = seg_header['X0']

    # Check if a new segment exists
    line = next(lines, None)
    if line is None:
        return None, None

    sample = 0
    max_samples = max(samples)

    # Read data into channels
    while sample < max_samples \
            and line is not None \
            and line not in ['\n', '\r\n', '']:

        line = line.replace('\r', '').replace('\n', '')
        values = line.split(file_header['Separator'])
        
        # One X Column means all x_values are the same
        if x_columns == "One":
            x_value = _lvm_float(values[0], decsep)
        
        # Multi will have X column for every Y Column
        if x_columns == "Multi": 
            columns = seg_header['Channels'] * 2
        else: # One or No will have a X Column at the front
            columns = seg_header['Channels'] + 1

        for i in range(seg_header['Channels']):
            ch = seg_data[i]
            if x_columns == "One":
                y_value = _lvm_float(values[i + 1], decsep)
            elif x_columns == "Multi":
                x_value = _lvm_float(values[i * 2], decsep)
                y_value = _lvm_float(values[i * 2 + 1], decsep)
            elif x_columns == "No":
                x_value = x0[i] + seg_header['Delta_X'][i] *\
                          sample
                y_value = _lvm_float(values[i + 1], decsep)

            # Check if data set has ended
            if y_value == None:
                continue

            ch[0].append(x_value)
            ch[1].append(y_value)
        
        # Add comments
        comments.append(values[columns] if len(values) > columns else '')

        # Get next line
        line = next(lines, None)
        sample += 1

    if line is None and sample != max_samples:
        raise LVMFormatError("EOF before finished segment")
    
    for ch in seg_data:
        ch = [np.asarray(ch[0]),np.asarray(ch[1])]

    return seg_data, comments

def read_segment_header(lines, file_header):
    """ Reads the segment header

    :param lines: lines of lvm file
    :param file_header: header for file
    :return seg_header: header for segment. None if no new segment to be read
    """
    # Setup headers with default values
    seg_header = {h: lvm.SEGMENT_HEADERS[h]['default']
                   for h in lvm.SEGMENT_HEADERS if not lvm.SEGMENT_HEADERS[h]['required']}
    
    seg_started = False

    for line in lines:
        # Strip new line
        line = line.replace('\r', '').replace('\n', '')

        # Reached end of segment header -> return header
        if line.startswith(lvm.END_OF_HEADER):
            validate_header(seg_header, lvm.SEGMENT_HEADERS)
            # First line after headers should be column names
            # Will begin with 'X_Value'
            columnNames = next(lines).replace('\r', '').replace('\n', '')
            if not columnNames.startswith('X_Value'):
                raise LVMFormatError("Failed to read column names")

            seg_header['Columns'] = columnNames.split(file_header['Separator'])
            seg_header['Y_Labels'] = [c for c in seg_header['Columns']
                                         if c not in ['X_Value', 'Comment']]
            return seg_header

        # Skip blank lines
        if line.startswith(file_header['Separator']) or line == '':
            continue

        # Enter Special block
        elif line.startswith(lvm.SPECIAL_BLOCK_START):
            skip_special_block(lines)
            # will return upon reaching line containing SPECIAL_BLOCK_END
            continue

        key, *values = line.split(file_header['Separator'])
        if key not in lvm.SEGMENT_HEADERS:
            raise LVMFormatError(f"Invalid File Header: {key}")

        vtype = lvm.SEGMENT_HEADERS[key]['type']

        data = []

        for v in values:
            if v != '':
                data.append(parse_value(v, vtype, file_header['Separator'], file_header['Decimal_Separator']))

        if not data:
            raise LVMFormatError(f"Error parsing value at:\n{line}")
        elif len(data) == 1:
            seg_header[key] = data[0]
        elif 'Channels' in seg_header and len(data) == seg_header['Channels']:
            seg_header[key] = data
        else:
            raise LVMFormatError(
                "Mismatch between number of Channels ("
                f"{seg_header['Channels'] if 'Channels' in seg_header else 'Not Found'}"
                f") and header {key} data {data} ({len(data)})"
            )

    # If the segment wasn't started (i.e., reached EOF before new data)
    # this is expected as this function will be run after the last segment 
    # is read. Return None to signify EOF
    if not seg_started:
        return None
    # Otherwise if we started reading segment header data but never reached
    # END_OF_HEADER a format error has occured. Raise accordingly
    raise LVMFormatError("Failed to parse segment header")

def read_segment(lines, file_header, seg_header=None, x0=None):
    """ Reads a data segment
    :param lines: lines of lvm file
    :param file_header: header for file
    :param seg_header: used for passing previous seg_header
    :return lvm_segment: Segment of parsed data 
    """

    # Parse Segment Header
    if seg_header is None or file_header['Multi_Headings']:
        seg_header = read_segment_header(lines, file_header)

    # if segment header is still None this means EOF and no more segments
    # so return None
    if seg_header is None:
        return None

    data, comments = read_segment_data(lines, file_header, seg_header, x0)
    if data is None:
        return None
    return {
        'header': seg_header,
        'data': data,
        'comments': comments
    }

def read_file_header(lines):
    """ Reads the LVM file header and return relevant information

    :param lines: lines of lvm file
    :return file_header: information on lvm file
    """

    # Scan the file for the Separator header
    separator, buffer = get_separator(lines)

    # Setup headers with default values
    file_header = {h: lvm.FILE_HEADERS[h]['default']
                   for h in lvm.FILE_HEADERS if not lvm.FILE_HEADERS[h]['required']}

    # Create a generator to go through buffer first and then consume lines
    def next_line(lines, buf):
        for L in buffer:
            yield L
        for L in lines:
            yield L
    
    lines = next_line(lines, buffer)

    # Check for magic identifier
    identifier = next(lines)
    if not identifier.startswith(lvm.FILE_MAGIC_IDENTIFIER):
        raise LVMFormatError("Did not find magic identifier"
                            f" {lvm.FILE_MAGIC_IDENTIFIER} at start of file")

    for line in lines:
        # Strip new line
        line = line.replace('\r', '').replace('\n', '')

        # Reached end of file header -> return header
        if line.startswith(lvm.END_OF_HEADER):
            validate_header(file_header, lvm.FILE_HEADERS)
            # Replace Separator header with character instead of word
            file_header['Separator'] = separator
            return file_header

        # Skip blank lines
        elif line.startswith(separator):
            continue

        # Enter Special block
        elif line.startswith(lvm.SPECIAL_BLOCK_START):
            skip_special_block(lines)
            # will return upon reaching line containing SPECIAL_BLOCK_END
            continue

        line_sp = line.split(separator)
        if len(line_sp) != 2:
            raise LVMFormatError(f"Error parsing key,value pair from '{line_sp}'")
        key, value = line_sp
        if key not in lvm.FILE_HEADERS:
            raise LVMFormatError(f"Invalid File Header: {key}")

        vtype = lvm.FILE_HEADERS[key]['type']

        data = parse_value(value, vtype, separator, file_header['Decimal_Separator'])

        if data is None:
            raise LVMFormatError(f"Error parsing value at:\n{line}")

        file_header[key] = data

    # Should return from inside for loop
    raise LVMFormatError("Failed to parse file header")

def read_lines(lines):
    """ Read lines of strings.

    :param lines: lines of the lvm file
    :return lvm_data: lvm dict
    """
    lvm_data = dict()

    # Read header data
    file_header = read_file_header(lines)
    lvm_data['file_header'] = file_header

    lvm_data['segments'] = []

    segment = read_segment(lines, file_header)

    while segment != None:
        lvm_data['segments'].append(segment)
        x_final = [ch[0][-1] if ch[0] else x0 
                   for ch, x0 in zip(segment['data'],
                                     segment['header']['X0'])] 
        segment = read_segment(lines, file_header, segment['header'], x_final)

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
    return read_lines(iter(str.splitlines(keepends=True)))


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
    dict_keys(['file_header','segments'])
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
    print('Number of segments:', len(da['segments']))

    for seg in da['Segments']:
        labels = [f"{l} ({u})" for l,u in zip(seg['header']['Y_Labels'],
                                              seg['header']['Y_Unit_Label'])]
        for ch, l in zip(seg['Data'], labels):
            plt.plot(*ch, label=l)

        plt.legend()
        plt.xlabel(seg['header']['X_Dimension'][0])
        plt.ylabel(seg['header']['Y_Dimension'])
        plt.show()
