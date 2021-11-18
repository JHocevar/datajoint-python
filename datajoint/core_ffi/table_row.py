from ._datajoint_core import ffi
from .datajoint_core_lib import dj_core
from .errors import datajoint_core_assert_success
from .table_column_ref import TableColumnRef

    

class TableRow():
    """
    TableRow class
    """

    def __init__(self, native=None, owning=True):
        self.native = ffi.new("TableRow**")
        self.cache = {}
        if native is None:
            self.native[0] = ffi.NULL
            self.owning = True
        elif ffi.typeof(native) is ffi.typeof("TableRow*"):
            self.native[0] = native
            self.owning = owning
        else:
            raise ValueError("invalid type for native pointer")

    def __del__(self):
        if self.owning:
            dj_core.table_row_free(self.native[0])

    def is_empty(self):
        """
        Check if TableRow is empty
        """
        res = dj_core.table_row_is_empty(self.native[0])
        return bool(res)

    def column_count(self):
        """
        Get number of columns in TableRow
        """
        return dj_core.table_row_column_count(self.native[0])

    def columns(self):
        """
        Get a list of all columns
        """
        # Not implemented due to a bug in cffi.
        # Variable-length arrays are not handled properly and result
        # in lost values.
        # Thus, all columns cannot be fetched at once at the moment.
        raise NotImplementedError()

    def column(self, index):
        """
        Get the column specified by name or ordinal
        """
        out_column = TableColumnRef()
        if type(index) == str:
            err = dj_core.table_row_get_column_with_name(
                self.native[0], index.encode('utf-8'), out_column.native)
            datajoint_core_assert_success(err)
        elif type(index) == int:
            err = dj_core.table_row_get_column_with_ordinal(
                self.native[0], index, out_column.native)
            datajoint_core_assert_success(err)
        else:
            raise TypeError("index must be a string or integer")
        return out_column

    def decode_col(self, index):

        if index in self.cache:
            print("hitting cached value")
            return index, self.cache[index]

        try:
            value = dj_core.allocated_decoded_value_new()

            # Because we can't use columns(), we have to work on
            # the assumption that all columns are numbered properly via
            # their ordinal.

            # TODO(Edward-garmon) handle out of bound errors better
            if type(index) == int and index >= self.column_count():
                return None, None

            col = self.column(index)
            col_name = col.name()
            err = dj_core.table_row_decode_to_allocation(
                self.native[0], col.native[0], value)
            if err != dj_core.ErrorCode_Success:
                # TODO(Jackson-nestelroad) clean up DECODE FAILED
                result = "DECODE FAILED"
                return col_name, result

            # `raw_data` is a void* of length `data_size` bytes.
            raw_data = dj_core.allocated_decoded_value_data(value)
            data_size = dj_core.allocated_decoded_value_size(value)

            col_name = col.name()
            # Decode the value to a Python value.
            dj_type = dj_core.allocated_decoded_value_type(value)
            if dj_type == dj_core.NativeTypeEnum_None or dj_type == dj_core.NativeTypeEnum_Null:
                result = None
            elif dj_type == dj_core.NativeTypeEnum_Bool:
                result = ffi.cast(
                    "int8_t*", raw_data)[0]
            elif dj_type == dj_core.NativeTypeEnum_Int8:
                result = ffi.cast(
                    "int8_t*", raw_data)[0]
            elif dj_type == dj_core.NativeTypeEnum_UInt8:
                result = ffi.cast(
                    "uint8_t*", raw_data)[0]
            elif dj_type == dj_core.NativeTypeEnum_Int16:
                result = ffi.cast(
                    "int16_t*", raw_data)[0]
            elif dj_type == dj_core.NativeTypeEnum_UInt16:
                result = ffi.cast(
                    "uint16_t*", raw_data)[0]
            elif dj_type == dj_core.NativeTypeEnum_Int32:
                result = ffi.cast(
                    "int32_t*", raw_data)[0]
            elif dj_type == dj_core.NativeTypeEnum_UInt32:
                result = ffi.cast(
                    "uint32_t*", raw_data)[0]
            elif dj_type == dj_core.NativeTypeEnum_Int64:
                result = ffi.cast(
                    "int64_t*", raw_data)[0]
            elif dj_type == dj_core.NativeTypeEnum_UInt64:
                result = ffi.cast(
                    "uint64_t*", raw_data)[0]
            elif dj_type == dj_core.NativeTypeEnum_String:
                result = ffi.string(
                    ffi.cast("char*", raw_data), data_size).decode('utf-8')
            elif dj_type == dj_core.NativeTypeEnum_Float32:
                result = ffi.cast(
                    "float*", raw_data)[0]
            elif dj_type == dj_core.NativeTypeEnum_Float64:
                result = ffi.cast(
                    "double*", raw_data)[0]
            elif dj_type == dj_core.NativeTypeEnum_Bytes:
                result = ffi.unpack(
                    ffi.cast("unsigned char*", raw_data), data_size)
            else:
                raise AssertionError("decoded value has invalid type name")

        finally:
            dj_core.allocated_decoded_value_free(value)

        self.cache[col_name] = result
        return col_name, result

    def __getitem__(self, index):
        col_name, val = self.decode_col(index)
        return val

    def __str__(self):
        return self.to_dict().__str__()

    def to_dict(self):
        result = dict()
        for i in range(self.column_count()):
            col_name, val = self.decode_col(i)
            result[col_name] = val
        return result

    def __iter__(self):
        return iter(self.values())

    def keys(self):
        result = []
        for i in range(self.column_count()):
            col_name, val = self.decode_col(i)
            result.append(col_name)
        return result
    
    def values(self):
        result = []
        for i in range(self.column_count()):
            col_name, val = self.decode_col(i)
            result.append(val)
        return result

    def items(self):
        result = []
        for i in range(self.column_count()):
            col_name, val = self.decode_col(i)
            result.append((col_name, val))
        return result

