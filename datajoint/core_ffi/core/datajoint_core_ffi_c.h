/**
 * Generalized types supported by DataJoint.
 */
enum DataJointType {
  DataJointType_Unknown,
  DataJointType_Boolean,
  DataJointType_TinyInt,
  DataJointType_TinyIntUnsigned,
  DataJointType_SmallInt,
  DataJointType_SmallIntUnsigned,
  DataJointType_MediumInt,
  DataJointType_MediumIntUnsigned,
  DataJointType_Int,
  DataJointType_IntUnsigned,
  DataJointType_BigInt,
  DataJointType_BigIntUnsigned,
  DataJointType_Enum,
  DataJointType_Date,
  DataJointType_Time,
  DataJointType_DateTime,
  DataJointType_Timestamp,
  DataJointType_CharN,
  DataJointType_VarCharN,
  DataJointType_Float,
  DataJointType_Double,
  DataJointType_Decimal,
  DataJointType_TinyBlob,
  DataJointType_MediumBlob,
  DataJointType_Blob,
  DataJointType_LongBlob,
  DataJointType_Binary,
};
typedef int32_t DataJointType;

/**
 * Enum type for representing the type of SQL database to connect to.
 */
enum DatabaseType {
  DatabaseType_MySql,
  DatabaseType_Postgres,
};
typedef int32_t DatabaseType;

/**
 * Error codes for library-related errors. All internal errors are
 * converted to one of these error codes so that the source of an error
 * can be easily identified by users of the C FFI.
 *
 * At the moment, these error codes are not standardized. In other words,
 * the actual numeric value of the error may change at any time until
 * a numbering system is standardized.
 */
enum ErrorCode {
  ErrorCode_Success = 0,
  ErrorCode_ConfigurationError,
  ErrorCode_UnknownDatabaseError,
  ErrorCode_IoError,
  ErrorCode_TlsError,
  ErrorCode_ProtocolError,
  ErrorCode_RowNotFound,
  ErrorCode_TypeNotFound,
  ErrorCode_ColumnIndexOutOfBounds,
  ErrorCode_ColumnNotFound,
  ErrorCode_ColumnDecodeError,
  ErrorCode_ValueDecodeError,
  ErrorCode_PoolTimedOut,
  ErrorCode_PoolClosed,
  ErrorCode_WorkerCrashed,
  ErrorCode_UnknownSqlxError,
  ErrorCode_NotConnected,
  ErrorCode_NoMoreRows,
  ErrorCode_UnsupportedNativeType,
  ErrorCode_WrongDatabaseType,
  ErrorCode_UnexpectedNullValue,
  ErrorCode_UnexpectedNoneType,
  ErrorCode_NullNotAllowed,
  ErrorCode_BufferNotEnough,
  ErrorCode_InvalidNativeType,
  ErrorCode_InvalidUtf8String,
  ErrorCode_RowIndexOutOfBounds,
  ErrorCode_BadPrimitiveEnumValue,
};
typedef int32_t ErrorCode;

/**
 * Native types that can be decoded from a database or encoded to a query,
 * possibly for a placeholder argument.
 *
 * Should be parallel to [`datajoint_core::types::NativeType`], aside from the
 * additional variant to represent null.
 */
enum NativeTypeEnum {
  /**
   * Represents the complete absence of any value.
   */
  NativeTypeEnum_None,
  /**
   * Represents a null value.
   */
  NativeTypeEnum_Null,
  NativeTypeEnum_Bool,
  NativeTypeEnum_Int8,
  NativeTypeEnum_UInt8,
  NativeTypeEnum_Int16,
  NativeTypeEnum_UInt16,
  NativeTypeEnum_Int32,
  NativeTypeEnum_UInt32,
  NativeTypeEnum_Int64,
  NativeTypeEnum_UInt64,
  NativeTypeEnum_String,
  NativeTypeEnum_Float32,
  NativeTypeEnum_Float64,
  NativeTypeEnum_Bytes,
};
typedef int32_t NativeTypeEnum;

/**
 * Three-state boolean for representing [`Option<bool>`] in an FFI-compatible manner.
 */
enum OptionalBool {
  OptionalBool_None = -1,
  OptionalBool_False = 0,
  OptionalBool_True = 1,
};
typedef int32_t OptionalBool;

/**
 * A single decoded value that has been allocated by the core library.
 *
 * This struct wraps a value allocated to be transmitted to C. It allows
 * the value to be decoded to a native type by the caller.
 */
typedef struct AllocatedDecodedValue AllocatedDecodedValue;

/**
 * A single connection instance to an arbitrary SQL database.
 */
typedef struct Connection Connection;

/**
 * Settings for connecting to an arbitrary SQL database.
 */
typedef struct ConnectionSettings ConnectionSettings;

/**
 * An object used to iterate over a set of rows.
 */
typedef struct Cursor Cursor;

/**
 * An object used to interact with a database by executing queries.
 *
 * Instances of `Executor` should not be created manually but by calling
 * [`executor()`][crate::connection::Connection::executor] on a
 * [`Connection`][crate::connection::Connection] instance.
 */
typedef struct Executor Executor;

/**
 * Enum for a native type and its corresponding value that can be decoded
 * from a database or encoded into a query.
 */
typedef struct NativeType NativeType;

/**
 * A reference to a table column object.
 *
 * [`TableRow`][`crate::results::TableRow`] objects share table columns when they are
 * created from the same query, which is why columns are accessed by reference.
 */
typedef struct TableColumnRef TableColumnRef;

/**
 * A single row in a database table or query result that is used to
 * read values out of.
 *
 * Wraps a SQLx row.
 */
typedef struct TableRow TableRow;

/**
 * A vector of table rows, which is used to communicate the results of returning
 * queries that return more than one row at a time.
 */
typedef struct TableRowVector TableRowVector;

typedef struct Vec_PlaceholderArgument Vec_PlaceholderArgument;

/**
 * A basic placeholder argument vector, which wraps several values of a supported native type.
 */
typedef struct Vec_PlaceholderArgument PlaceholderArgumentVector;

/**
 * A single placeholder argument.
 */
typedef struct NativeType PlaceholderArgument;

/**
 * Allocates a new connection.
 *
 * The new connection instance takes ownership of the settings object passed in.
 * The settings object will be deallocated when the settings object is deallocated.
 * Library users should not manually free a [`ConnectionSettings`] object after it
 * is passed into this function.
 */
struct Connection *connection_new(struct ConnectionSettings *settings);

/**
 * Frees a connection.
 */
void connection_free(struct Connection *this_);

/**
 * Checks if the connection is still connected.
 */
int32_t connection_is_connected(struct Connection *this_);

/**
 * Starts the connection to the SQL database according to the settings the connection
 * was initialized with.
 */
int32_t connection_connect(struct Connection *this_);

/**
 * Disconnects from the SQL database.
 *
 * If the database connection has already been disconnected, this method
 * is a no-op.
 *
 * The connection can be restarted if desired.
 */
int32_t connection_disconnect(struct Connection *this_);

/**
 * Restarts the connection to the SQL database according to the internal settings object.
 */
int32_t connection_reconnect(struct Connection *this_);

/**
 * Gets the pointer to the connection's internal settings object..
 *
 * This pointer should not be freed.
 */
struct ConnectionSettings *connection_get_settings(struct Connection *this_);

/**
 * Creates an executor to interact with the database over this connection.
 */
int32_t connection_executor(struct Connection *this_, struct Executor **out);

/**
 * Executes the given non-returning query, returning the number of rows affected.
 *
 * The third parameter can be `NULL` or a collection of placeholder arguments to
 * bind to the query. Once the query is executed, the [`PlaceholderArgumentVector`]
 * is owned and deallocated by the library. In other words, the caller does not
 * need to manually free the placeholder arguments after they are bound to a query.
 */
int32_t connection_execute_query(struct Connection *this_,
                                 const char *query,
                                 PlaceholderArgumentVector *args,
                                 uint64_t *out);

/**
 * Creates a cursor for iterating over the results of the given returning query.
 *
 * The third parameter can be `NULL` or a collection of placeholder arguments to
 * bind to the query. Once the query is executed, the [`PlaceholderArgumentVector`]
 * is owned and deallocated by the library. In other words, the caller does not
 * need to manually free the placeholder arguments after they are bound to a query.
 */
int32_t connection_fetch_query(struct Connection *this_,
                               const char *query,
                               PlaceholderArgumentVector *args,
                               struct Cursor **out);

/**
 * Frees a cursor.
 */
void cursor_free(struct Cursor *this_);

/**
 * Fetches the next row.
 */
int32_t cursor_next(struct Cursor *this_, struct TableRow **out);

/**
 * Fetches all remaining rows.
 */
int32_t cursor_rest(struct Cursor *this_, struct TableRowVector **out);

/**
 * Frees an executor.
 */
void executor_free(struct Executor *this_);

/**
 * Executes the given query over the connection.
 */
int32_t executor_execute(struct Executor *this_, const char *query, uint64_t *out_size);

/**
 * Fetches one row using the given query.
 */
int32_t executor_fetch_one(struct Executor *this_, const char *query, struct TableRow **out);

/**
 * Fetches multiple rows using the given query.
 */
int32_t executor_fetch_all(struct Executor *this_, const char *query, struct TableRowVector **out);

/**
 * Creates a cursor for the given query.
 *
 * The third parameter can be `NULL` or a collection of placeholder arguments to
 * bind to the query. Once the query is executed, the [`PlaceholderArgumentVector`]
 * is owned and deallocated by the library. In other words, the caller does not
 * need to manually free the placeholder arguments after they are bound to a query.
 */
int32_t executor_cursor(struct Executor *this_,
                        const char *query,
                        PlaceholderArgumentVector *args,
                        struct Cursor **out);

/**
 * Creates a new settings object.
 */
struct ConnectionSettings *connection_settings_new(void);

/**
 * Frees a settings object.
 */
void connection_settings_free(struct ConnectionSettings *this_);

/**
 * Sets the database type, which represents the SQL flavor to use for the connection.
 */
int32_t connection_settings_set_database_type(struct ConnectionSettings *this_,
                                              DatabaseType dbtype);

/**
 * Sets the username for a database connection.
 */
int32_t connection_settings_set_username(struct ConnectionSettings *this_, const char *username);

/**
 * Sets the password for a database connection.
 */
int32_t connection_settings_set_password(struct ConnectionSettings *this_, const char *password);

/**
 * Sets the hostname for a database connection.
 */
int32_t connection_settings_set_hostname(struct ConnectionSettings *this_, const char *hostname);

/**
 * Sets the port for a database connection.
 */
int32_t connection_settings_set_port(struct ConnectionSettings *this_, uint16_t port);

/**
 * Sets the database name for a database connection.
 */
int32_t connection_settings_set_database_name(struct ConnectionSettings *this_,
                                              const char *database_name);

/**
 * Specifies how a connection should use TLS.
 *
 * Receives an [`OptionalBool`], which represents three-state logic.
 * - [`OptionalBool::True`] - Enforce TLS.
 * - [`OptionalBool::False`] - Do not use TLS.
 * - [`OptionalBool::None`] - Let database decide.
 */
int32_t connection_settings_set_use_tls(struct ConnectionSettings *this_, OptionalBool use_tls);

/**
 * Gets the database type entry on the settings object.
 */
DatabaseType connection_settings_get_database_type(struct ConnectionSettings *this_);

/**
 * Gets the username entry on the settings object.
 *
 * [`datajoint_core_cstring_free`][crate::util::datajoint_core_cstring_free] must be called
 * on the string returned from this function to avoid memory leaks.
 */
const char *connection_settings_get_username(const struct ConnectionSettings *this_);

/**
 * Gets the password entry on the settings object.
 *
 * [`datajoint_core_cstring_free`][crate::util::datajoint_core_cstring_free] must be called
 * on the string returned from this function to avoid memory leaks.
 */
const char *connection_settings_get_password(const struct ConnectionSettings *this_);

/**
 * Gets the hostname entry on the settings object.
 *
 * [`datajoint_core_cstring_free`][crate::util::datajoint_core_cstring_free] must be called
 * on the string returned from this function to avoid memory leaks.
 */
const char *connection_settings_get_hostname(const struct ConnectionSettings *this_);

/**
 * Gets the port entry on the settings object.
 *
 * [`datajoint_core_cstring_free`][crate::util::datajoint_core_cstring_free] must be called
 * on the string returned from this function to avoid memory leaks.
 */
uint16_t connection_settings_get_port(const struct ConnectionSettings *this_);

/**
 * Gets the database name entry on the settings object.
 *
 * [`datajoint_core_cstring_free`][crate::util::datajoint_core_cstring_free] must be called
 * on the string returned from this function to avoid memory leaks.
 */
const char *connection_settings_get_database_name(const struct ConnectionSettings *this_);

/**
 * Gets the TLS setting entry on the settings object.
 *
 * [`datajoint_core_cstring_free`][crate::util::datajoint_core_cstring_free] must be called
 * on the string returned from this function to avoid memory leaks.
 */
OptionalBool connection_settings_get_use_tls(const struct ConnectionSettings *this_);

/**
 * Returns the last error message as a C string. Returns null if there has been no error.
 *
 * [`datajoint_core_cstring_free`][crate::util::datajoint_core_cstring_free] must be called
 * on the string returned from this function to avoid memory leaks.
 */
const char *datajoint_core_get_last_error_message(void);

/**
 * Returns the last error code. Returns [`ErrorCode::Success`] if there has been no error.
 */
int32_t datajoint_core_get_last_error_code(void);

/**
 * Creates a new placeholder argument vector to send to a query method.
 */
PlaceholderArgumentVector *placeholder_argument_vector_new(void);

/**
 * Frees an entire placeholder argument vector, including all arguments inside.
 */
void placeholder_argument_vector_free(PlaceholderArgumentVector *ptr);

/**
 * Adds a new placeholder argument to the vector.
 *
 * Data is referenced by the `void* data` and is `data_size` bytes.
 * The data is NOT owned and must remain alive until the placeholder arguments are bound to the query.
 * Data is decoded in the library of type `data_type`, which is a supported column type for decoding.
 *
 * Gives the created argument object through an output parameter for further modification if desired.
 */
int32_t placeholder_argument_vector_add(PlaceholderArgumentVector *this_,
                                        void *data,
                                        uintptr_t data_size,
                                        NativeTypeEnum data_type,
                                        PlaceholderArgument **out);

/**
 * Frees a table column reference.
 */
void table_column_ref_free(struct TableColumnRef *this_);

/**
 * Gives the integer ordinal of the column, which can be used to
 * fetch the column in a row.
 */
size_t table_column_ref_ordinal(const struct TableColumnRef *this_);

/**
 * Gives the name of the column, which can be used to fetch the
 * column in a row.
 */
const char *table_column_ref_name(const struct TableColumnRef *this_);

/**
 * The DataJoint type for the column.
 */
DataJointType table_column_ref_type(const struct TableColumnRef *this_);

/**
 * Frees a table row.
 */
void table_row_free(struct TableRow *this_);

/**
 * Checks if the row is empty.
 */
int32_t table_row_is_empty(const struct TableRow *this_);

/**
 * Utility method for returning the number of columns in the row
 * without constructing an intermediate vector.
 */
size_t table_row_column_count(const struct TableRow *this_);

/**
 * Creates an array of table columns in memory that can be used to read values
 * inside of this table row.
 *
 * On success, `out_columns` will point to the beginning of the array of columns,
 * and `columns_size` will be the number of columns in the array.
 *
 * [`table_row_columns_advance`] can be used to advance the pointer by index.
 *
 * [`table_row_columns_free`] must be called on the created array to avoid memory
 * leaks.
 */
int32_t table_row_columns(const struct TableRow *this_,
                          struct TableColumnRef **out_columns,
                          size_t *columns_size);

/**
 * Performs pointer arithmetic. Equivalent to `columns + index` in C.
 */
struct TableColumnRef *table_row_columns_advance(struct TableColumnRef *columns, size_t index);

/**
 * Frees a series of table columns in memory that were created from
 * [`table_row_columns_advance`].
 */
void table_row_columns_free(struct TableColumnRef *out_columns, size_t columns_size);

/**
 * Gets a column by name.
 */
int32_t table_row_get_column_with_name(const struct TableRow *this_,
                                       const char *column_name,
                                       struct TableColumnRef **out);

/**
 * Gets a column by ordinal index.
 */
int32_t table_row_get_column_with_ordinal(const struct TableRow *this_,
                                          size_t ordinal,
                                          struct TableColumnRef **out);

/**
 * Frees a table row vector, including all table rows inside.
 */
void table_row_vector_free(struct TableRowVector *this_);

/**
 * Gives the number of rows.
 */
size_t table_row_vector_size(const struct TableRowVector *this_);

/**
 * Gives an internal pointer to a [`TableRow`] at the given index.
 *
 * This pointer should not be freed by the user. Instead, call [`table_row_vector_free`]
 * to free an entire table row vector.
 */
const struct TableRow *table_row_vector_get(const struct TableRowVector *this_, size_t index);

/**
 * Decodes a single table row value to a caller-allocated buffer.
 *
 * The caller is responsible for moving data out of the buffer and handling
 * the deallocation of the buffer itself.
 */
int32_t table_row_decode_to_buffer(const struct TableRow *this_,
                                   const struct TableColumnRef *column,
                                   void *buffer,
                                   size_t buffer_size,
                                   size_t *output_size,
                                   NativeTypeEnum *output_type);

/**
 * Creates instance of AllocatedDecodedValue.
 */
struct AllocatedDecodedValue *allocated_decoded_value_new(void);

/**
 * Frees instance of AllocatedDecodedValue
 */
void allocated_decoded_value_free(struct AllocatedDecodedValue *this_);

/**
 * Returns the data of the AllocatedDecodedValue.
 */
const void *allocated_decoded_value_data(const struct AllocatedDecodedValue *this_);

/**
 * Returns the size of the AllocatedDecodedValue.
 */
size_t allocated_decoded_value_size(const struct AllocatedDecodedValue *this_);

/**
 * Returns the type_name of the AllocatedDecodedValue.
 */
NativeTypeEnum allocated_decoded_value_type(const struct AllocatedDecodedValue *this_);

/**
 * Checks if the allocated decoded value contains a `null` value, which
 * means `null` was successfully decoded.
 */
int32_t allocated_decoded_value_is_null_value(const struct AllocatedDecodedValue *this_);

/**
 * Decodes a single table row value to a Rust-allocated buffer stored in a
 * caller-allocated wrapper value.
 *
 * The caller is responsible for moving data out of the buffer and handling
 * the deallocation of the wrapper. When the wrapper is deallocated, the
 * data inside is properly deallocated depending on the type.
 */
int32_t table_row_decode_to_allocation(const struct TableRow *this_,
                                       const struct TableColumnRef *column,
                                       struct AllocatedDecodedValue *value);

/**
 * Frees a [`CString`] that was allocated on the Rust-side of the core library.
 */
void datajoint_core_cstring_free(char *string);
