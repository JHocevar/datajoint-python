from .datajoint_core_lib import dj_core
from ._datajoint_core import ffi

OptionalBool_encode = {
    None: dj_core.OptionalBool_None,
    True: dj_core.OptionalBool_True,
    False: dj_core.OptionalBool_False,
}

OptionalBool_decode = {
    dj_core.OptionalBool_None: None,
    dj_core.OptionalBool_True: True,
    dj_core.OptionalBool_False: False
}

DatabaseType = {
    "mysql": dj_core.DatabaseType_MySql,
    "postgres": dj_core.DatabaseType_Postgres,
    dj_core.DatabaseType_MySql: "MySQL",
    dj_core.DatabaseType_Postgres: "Postgres",
}


def free_and_decode_string(value):
    ret = ffi.string(value).decode("utf-8")
    dj_core.datajoint_core_cstring_free(value)
    return ret


def encode_string(value):
    return value.encode("utf-8")


def encode_bool(value):
    return OptionalBool_encode[value]


def decode_bool(value):
    return OptionalBool_decode[value]


def map_database_type(value):
    return DatabaseType[value]


encode_methods = {
    int: int,
    str: encode_string,
    "OptionalBool": encode_bool,
    "DatabaseType": map_database_type
}

decode_methods = {
    int: int,
    str: free_and_decode_string,
    "OptionalBool": decode_bool,
    "DatabaseType": map_database_type
}


class ConnectionSetting:
    def __init__(self, getter, setter, ffi_type):
        self.getter = getter
        self.setter = setter
        self.ffi_type = ffi_type

    def set_value(self, native, value):
        self.setter(native, encode_methods[self.ffi_type](value))

    def get_value(self, native):
        return decode_methods[self.ffi_type](self.getter(native))


class Config:
    _fields = {
        "database_type": ConnectionSetting(
            getter=dj_core.connection_settings_get_database_type,
            setter=dj_core.connection_settings_set_database_type,
            ffi_type="DatabaseType"
        ),
        "host": ConnectionSetting(
            getter=dj_core.connection_settings_get_hostname,
            setter=dj_core.connection_settings_set_hostname,
            ffi_type=str
        ),
        "user": ConnectionSetting(
            getter=dj_core.connection_settings_get_username,
            setter=dj_core.connection_settings_set_username,
            ffi_type=str
        ),
        "passwd": ConnectionSetting(
            getter=dj_core.connection_settings_get_password,
            setter=dj_core.connection_settings_set_password,
            ffi_type=str
        ),
        "port": ConnectionSetting(
            getter=dj_core.connection_settings_get_port,
            setter=dj_core.connection_settings_set_port,
            ffi_type=int
        ),
        "use_tls": ConnectionSetting(
            getter=dj_core.connection_settings_get_use_tls,
            setter=dj_core.connection_settings_set_use_tls,
            ffi_type="OptionalBool"
        )
    }

    def __init__(self, native=None, owning=True):
        self.native = ffi.new("ConnectionSettings**")
        if native is None:
            self.native[0] = ffi.NULL
            self.owning = True
        elif ffi.typeof(native) is ffi.typeof("ConnectionSettings*"):
            self.native[0] = native
            self.owning = owning
        else:
            raise ValueError("invalid type for native pointer")

    def __del__(self):
        if self.owning:
            dj_core.connection_settings_free(self.native[0])

    def __setitem__(self, setting, value):
        field = self._fields.get(setting)
        # TODO: BANDAGE SOLUTION! currently ignoring bad keys (for use_tls/ssl error)
        if field:
            field.set_value(self.native[0], value)

    def __getitem__(self, setting):
        field = self._fields[setting]
        return field.get_value(self.native[0])

    def get_settings(self):
        settings = dict()
        for name, setting in self._fields.items():
            settings[name] = setting.get_value(self.native[0])
        return settings

    def __repr__(self):
        rep = "Database Settings:\n"
        for setting, value in self.get_settings().items():
            rep += f"{setting}: {value}\n"
        return rep

    def update(self, mapping):
        for key in mapping:
            self[key] = mapping[key]
