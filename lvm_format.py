END_OF_HEADER = "***End_of_Header***"
DATE_FORMAT = "%Y/%m/%d"
TIME_FORMAT = "%H:%M:%S"

SPECIFICATION_REF = "https://www.ni.com/en/support/documentation/supplemental/06/specification-for-the-labview-measurement-file---lvm-.html"

# Identifies the file as a LabVIEW measurement file (.lvm).
# This tag always appears in column 0, row 0
# (the first characters in the file).
FILE_MAGIC_IDENTIFIER = "LabVIEW Measurement"

# File Headers appear at the beginning of the LVM before the first
# END_OF_HEADER is reached
FILE_HEADERS = {
    # Date when the data collection started.
    "Date": {
        "required": True,
        "type": "date"  # YYYY/MM/DD
    },
    # Description of the data in the file.
    "Description": {
        "required": False,
        "default": '',
        "type": "text"
    },
    # Specifies whether each packet has a header.
    "Multi_Headings": {
        "required": False,
        "default": False,
        "type": "bool"
    },
    "Operator": {
        "required": False,
        "default": '',
        "type": "text"
    },
    # Name of the project associated with the data in the file
    "Project": {
        "required": False,
        "default": '',
        "type": 'text'
    },
    # Version number of reader needed to parse the file correctly the file
    # type.
    # For example, a 1.0 version of a reader can parse the file until the file
    # format changes so much that it is no longer backwards compatible.
    # The Writer_Version supplies the actual file type version.
    "Reader_Version": {
        "required": False,
        "default": "Writer_Version",
        "type": "float"  # Major.Minor
    },
    # Character(s) used to separate each field in the file. You can use any
    # character as a separator except the new line character. However,
    # base-level readers usually use tabs or commas as delimiters. Escape
    # other text fields in the file to prevent the separator character(s) from
    # appearing as text rather than delimiters. To use the character(s)
    # specified as a delimiter requires that you know what that character(s)
    # is. To find out what the separator character(s) is, read the entire
    # header block and search for the keyword Separator. The character(s) that
    # follows the keyword is the separator. To parse the file faster, place
    # this field in the header after the LabVIEW Measurement ID field. To read
    # in the entire header block, read until you find the ***End_of_Header***
    # tag.
    "Separator": {
        "required": False,
        "default": '\t',
        "type": "text"
    },
    # The default is the decimal separator of the system.
    # Symbol used to separate the integral part of a number from the
    # fractional part. A decimal separator usually is a dot or a comma.
    "Decimal_Separator": {
        "required": False,
        "default": ',',
        "type": "text"
    },
    # Time at which the start of a data series occurred.
    "Time": {
        "required": True,
        "type": "time"
        # HH:MM:SS.XXX - The format is the same, regardless of the system time
        # configuration. The SS.XXX is the number of seconds since the last
        # minute as a floating-point number. The number of digits in the
        # fractional seconds is arbitrary and can be zero. If there are no
        # fractional seconds, the decimal point is optional.
    },
    # Format of the x-axis values. This tag is valid only if the X_Dimension
    # tag value is Time
    # Options:
    # Absolute - x-value is number of seconds since midnight, January 1, 1904
    # GMT
    # Relative - x-value is number of seconds since the date and time stamps
    "Time_Pref": {
        "required": False,
        "default": "Relative",
        "type": "options",
                "options": ["Absolute", "Relative"]
    },
    # Version number of the file type written by the software.
    "Writer_Version": {
        "required": True,
        "type": "float"  # Major.Minor
    },
    # Specifies which x-values are saved.
    # Options:
    # No - save no x-values. The first data column is blank. The x-values can
    #      be generated from the X0 and Delta_X values.
    # One - saves one column of x-values. This column corresponds to the
    #       first column of data that contains the most number of samples.
    # Multi - saves a column of x data for every column of y data.
    "X_Columns": {
        "required": False,
        "default": "One",
        "type": "options",
        "options": ["No", "One", "Multi"]
    }
}

# Segment Headers are found after the file headers and immediately preceding
# data.
SEGMENT_HEADERS = {
    # Number of channels in the packet. This field must occur before any
    # fields that depend on it. For example, the Samples field has entries
    # for each channel, so the reader must know the number of channels to
    # properly parse it.
    "Channels": {
        "required": True,
        "type": "integer"
    },
    # Date the data set in the segment started. There are separate dates for
    # each data set. The dates are placed in the same column as the y data
    # of the data set.
    "Date": {
        "required": True,
        "type": "date"  # YYYY/MM/DD
    },
    # The increment between points on the x-axis. The .lvm format assumes
    # all data is equally spaced in the x-dimension. There is one value for
    # each data set in the packet. The value appears in the same column as
    # the y-values for the data.
    "Delta_X": {
        "required": True,
        "type": "number"
    },
    # Comments the user adds to the segment header. A segment header does not
    # necessarily exist for every packet. Use the Comment field at the far
    # right of the data for specific notes about each segment.
    "Notes": {
        "required": False,
        "default": "",
        "type": "text"
    },
    # Number of samples in each waveform in the packet.
    # There is one entry for every data set.
    # The entry appears in the same column as the y data of the data set.
    "Samples": {
        "required": True,
        "type": "integer"
    },
    # Name of the test that acquired the segment of data.
    "Test_Name": {
        "required": False,
        "default": "",
        "type": "text"
    },
    # Test numbers in the Test_Series that acquired the data in this segment.
    # Semicolons separate the test numbers. If the file separator is a
    # semicolon, commas separate the numbers.
    "Test_Numbers": {
        "required": False,
        "default": "",
        "type": "text"
    },
    # Series of the test performed to get the data in this packet.
    "Test_Series": {
        "required": False,
        "default": "",
        "type": "text"
    },
    # Time of day when you started acquiring the data set in the segment.
    # Each data set includes a different time.
    # The times are placed in the same column as the y data of the data set.
    "Time": {
        "required": True,
        "type": "time"
        # HH:MM:SS.XXX - The format is the same, regardless of the computer
        # locale. The HH is the number of hours since midnight. The MM field
        # is the number of minutes since the last hour. The SS.XXX is the
        # number of seconds since the last minute as a floating-point number.
        # The number of digits in the fractional seconds is arbitrary and can
        # be zero. If there are not fractional seconds, the decimal point is
        # optional.
    },
    # Model number of the unit under test
    "UUT_M/N": {
        "required": False,
        "default": "",
        "type": "text"
    },
    # Name or instrument class of the unit under test.
    "UUT_Name": {
        "required": False,
        "default": "",
        "type": "text"
    },
    # Serial number of the unit under test.
    "UUT_S/N": {
        "required": False,
        "default": "",
        "type": "text"
    },
    # The initial value for the x-axis. Each data set in the packet has a 
    # single X0 value. The value appears in the same column as the y-values
    # for the data.
    "X0": {
        "required": True,
        "type": "number"
    },
    # Unit type of the x-axis. The actual data does not need to be in SI units.
    # The X_Unit_Label field indicates the actual units of the data.
    "X_Dimension": {
        "required": False,
        "default": "Time",
        "type": "text"
    },
    # Labels for the units used in plotting the x data.
    # The label appears in the same column as the y data to which it corresponds.
    # You do not have to fill in all unit labels.
    "X_Unit_Label": {
        "required": False,
        "default": "Default SI Unit",
        "type": "text"
    },
    # Unit type of the y-axis. The actual data does not need to be in SI units.
    # The Y_Unit_Label field indicates the actual units of the data.
    "Y_Dimension": {
        "required": False,
        "default": "Electric Potential",
        "type": "text"
    },
    # Labels for the units used in plotting the y data.
    # The label appears in the same column as the y data to which it corresponds.
    # You do not have to fill in all unit labels.
    "Y_Unit_Label": {
        "required": False,
        "default": "Default SI Unit",
        "type": "text"
    }
}

SPECIAL_BLOCK_START = "***Start_Special***"
SPECIAL_BLOCK_END = "***End_Special***"
