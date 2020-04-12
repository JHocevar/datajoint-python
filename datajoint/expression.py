from itertools import count
import logging
import inspect
import re
import copy
from .settings import config
from .errors import DataJointError
from .fetch import Fetch, Fetch1
from .preview import preview, repr_html
from .condition import AndList, Not, make_condition, assert_join_compatibility, get_attribute_names_from_sql_expression

logger = logging.getLogger(__name__)


class QueryExpression:
    """
    QueryExpression implements query operators to derive new entity sets from its inputs.
    A QueryExpression object generates a SELECT statement in SQL.
    QueryExpression operators are restrict, join, proj, aggr, and union.

    A QueryExpression object has a source, a restriction (an AndList), and heading.
    Property `heading` (type dj.Heading) is loaded from the database and updated by proj.

    The restriction is applied first without having access to the attributes generated by the projection.
    Then projection is applied by selecting modifying the heading attribute.

    Application of operators does not always lead to the creation of a subquery.
    A subquery is generated when:
        1. A restriction is applied on any computed or renamed attributes
        2. A projection is applied remapping remapped attributes
        3. Subclasses: Join, GroupBy, and Union have additional specific rules.
    """

    def __init__(self, source):
        self.source = source
        self._restriction = AndList()
        self._projection = dict()
        self._distinct = False

        from .table import Table
        if not isinstance(self, Table):
            self._heading = None
            self._connection = None

    def copy(self):
        result = copy.copy(self)
        result._restriction = AndList(self._restriction)
        result._projection = dict(self._projection)
        return result

    @property
    def connection(self):
        """ a dj.Connection object from source """
        from .table import Table
        if not isinstance(self, Table):
            assert isinstance(self.source, QueryExpression)
            self._connection = self.source.connection
        return self._connection

    @property
    def heading(self):
        """
        :return: a dj.Heading object.
        The proj operator modifies.
        """
        if isinstance(self.source, QueryExpression):
            if self._heading is None:
                self._heading = self.source.heading
        else:
            # in dj.Table's subclasses self._heading is already defined but may need to be initialized
            from .table import Table
            assert isinstance(self, Table)
            self._heading.init_from_database(self.connection, self.database, self.table_name, self.declaration_context)

        return self._heading

    @property
    def distinct(self):
        """ True if the DISTINCT modifier is required to make valid result """
        return self._distinct

    @property
    def restriction(self):
        """ The AndList of restrictions applied to input to produce the result """
        assert isinstance(self._restriction, AndList)
        return self._restriction

    @property
    def primary_key(self):
        return self.heading.primary_key

    __subquery_alias_count = count()    # count for alias names used in from_clause

    def from_clause(self):
        if isinstance(self.source, QueryExpression):
            return '(' + self.source.make_sql() + ') as `_s%x`' % next(self.__subquery_alias_count)
        else:
            assert isinstance(self.source, str)
            return self.source

    @property
    def where_clause(self):
        """
         Translate the input arg into the equivalent SQL condition (a string)
         :param arg: any valid restriction object.
         :return: an SQL condition string or a boolean value.
         """
        cond = make_condition(self, self.restriction)

        return '' if cond is True else ' WHERE %s' % cond

    def get_select_fields(self, select_fields=None):
        """
        :return: string specifying the attributes to return
        """
        return self.heading.as_sql if select_fields is None else self.heading.project(select_fields).as_sql

    # --------- query operators -----------

    def restrict(self, restriction):
        """
        Produces a new expression with the new restriction applied.
        rel.restrict(restriction)  is equivalent to  rel & restriction.
        rel.restrict(Not(restriction))  is equivalent to  rel - restriction
        The primary key of the result is unaffected.
        Successive restrictions are combined as logical AND:   r & a & b  is equivalent to r & AndList((a, b))
        Any QueryExpression, collection, or sequence other than an AndList are treated as OrLists
        (logical disjunction of conditions)
        Inverse restriction is accomplished by either using the subtraction operator or the Not class.

        The expressions in each row equivalent:

        rel & True                          rel
        rel & False                         the empty entity set
        rel & 'TRUE'                        rel
        rel & 'FALSE'                       the empty entity set
        rel - cond                          rel & Not(cond)
        rel - 'TRUE'                        rel & False
        rel - 'FALSE'                       rel
        rel & AndList((cond1,cond2))        rel & cond1 & cond2
        rel & AndList()                     rel
        rel & [cond1, cond2]                rel & OrList((cond1, cond2))
        rel & []                            rel & False
        rel & None                          rel & False
        rel & any_empty_entity_set          rel & False
        rel - AndList((cond1,cond2))        rel & [Not(cond1), Not(cond2)]
        rel - [cond1, cond2]                rel & Not(cond1) & Not(cond2)
        rel - AndList()                     rel & False
        rel - []                            rel
        rel - None                          rel
        rel - any_empty_entity_set          rel

        When arg is another QueryExpression, the restriction  rel & arg  restricts rel to elements that match at least
        one element in arg (hence arg is treated as an OrList).
        Conversely,  rel - arg  restricts rel to elements that do not match any elements in arg.
        Two elements match when their common attributes have equal values or when they have no common attributes.
        All shared attributes must be in the primary key of either rel or arg or both or an error will be raised.

        QueryExpression.restrict is the only access point that modifies restrictions. All other operators must
        ultimately call restrict()

        :param restriction: a sequence or an array (treated as OR list), another QueryExpression, an SQL condition
        string, or an AndList.
        """
        new_condition = make_condition(self, restriction)
        if new_condition is True:
            return self  # restriction has no effect

        # check that all attributes in condition are present in the query
        attributes = get_attribute_names_from_sql_expression(new_condition)
        try:
            raise DataJointError("Attribute `%s` is not found in query." % next(
                attr for attr in attributes if attr not in self.heading.names))
        except StopIteration:
            pass  # all ok

        # If the new condition uses any aliased attributes, a subquery is required
        # However, GroupBy's HAVING statement can work find with aliased attributes.
        need_subquery = not isinstance(self, GroupBy) and any(
            self.heading[attr].sql_expression for attr in attributes)

        if need_subquery:
            result = QueryExpression(self)
        else:
            result = self.copy()

        result.restriction.append(restriction)
        return result

    def __and__(self, restriction):
        """
        Restriction operator
        :return: a restricted copy of the input argument
        See QueryExpression.restrict for more detail.
        """
        return self.restrict(restriction)

    def __sub__(self, restriction):
        """
        inverted restriction:
        :return: a restricted copy of the argument
        See QueryExpression.restrict for more detail.
        """
        return self.restrict(Not(restriction))

    def __mul__(self, other):
        """
        natural join of query expressions `self` and `other`
        """
        return other * self if isinstance(other, U) else Join.create(self, other)

    def __add__(self, other):
        """
        union of two entity sets `self` and `other`
        """
        return Union.create(self, other)

    def proj(self, *attributes, **named_attributes):
        """
        Projection operator.
        :param attributes:  attributes to be included in the result. (The primary key is already included).
        :param named_attributes: new attributes computed or renamed from existing attributes.
        :return: the projected expression.
        Primary key attributes cannot be excluded but may be renamed.
        Thus self.proj() leaves only the primary key attributes of self.
        self.proj(...) -- includes all
        self.proj(a='id') renames the attribute 'id' into 'a' and includes 'a' in the projection.
        self.proj(a='expr') adds a new field a with the value computed with an SQL expression.
        self.proj(a='(id)') adds a new computed field named 'a' that has the same value as id
        Each attribute can only be used once in attributes or named_attributes.
        If the attribute list contains an Ellipsis ..., then all secondary attributes are included
        If an entry of the attribute list starts with a dash, e.g. '-attr', then the secondary attribute
        attr will be excluded, if already present but ignored if not found.
        """

        duplication_pattern = re.compile(r'\s*\(\s*(?P<name>[a-z][a-z_0-9]*)\s*\)\s*')
        rename_pattern = re.compile(r'\s*(?P<name>[a-z][a-z_0-9]*)\s*')

        replicate_map = {k: m.group('name')
                           for k, m in ((k, duplication_pattern.match(v)) for k, v in named_attributes.items()) if m}
        rename_map = {k: m.group('name')
                           for k, m in ((k, rename_pattern.match(v)) for k, v in named_attributes.items()) if m}
        compute_map = {k: v for k, v in named_attributes.items()
                       if not duplication_pattern.match(v) and not rename_pattern.match(v)}

        # include primary key
        attributes = set(attributes)
        attributes.update((k for k in self.primary_key if k not in rename_map.items()))

        # include all secondary attributes with Ellipsis
        if Ellipsis in attributes:
            attributes.discard(Ellipsis)
            attributes.update((a for a in self.heading.secondary_attributes if a not in attributes))

        # exclude attributes
        excluded_attributes = set(a.lstrip('-').strip() for a in attributes if a.startswith('-'))
        try:
            raise DataJointError("Cannot exclude primary key attribute %s", next(
                a for a in excluded_attributes if a in self.primary_key))
        except StopIteration:
            pass  # all ok
        attributes.difference_update(excluded_attributes)

        # check that all mentioned names are present in heading
        mentions = attributes.union(excluded_attributes).union(replicate_map.values()).union(rename_map.values())
        try:
            raise DataJointError("Attribute '%s' not found." % next(a for a in mentions if not self.heading.names))
        except StopIteration:
            pass  # all ok

        # require a subquery if the projection remaps any remapped attributes
        computation_attributes = set(q for v in compute_map.values() for q in get_attribute_names_from_sql_expression(v))
        need_subquery = any(self.heading[name].sql_expression is not None
                               for name in set(rename_map.values()).union(replicate_map.values()))

        if not need_subquery and self.restriction:
            restriction_attributes = get_attribute_names_from_sql_expression(make_condition(self, self.restriction))
            # need a subquery if the restriction applies to attributes that have been renamed
            need_subquery = any(self.heading[name].sql_expression is not None for name in restriction_attributes)
        result = QueryExpression(self) if need_subquery else self.copy()
        result.heading.select(attributes, rename_map=rename_map, replicate_map=replicate_map, compute_map=compute_map)
        return result

    def aggr(self, group, *attributes, keep_all_rows=False, **named_attributes):
        """
        Aggregation/projection operator
        :param group:  an entity set whose entities will be grouped per entity of `self`
        :param attributes: attributes of self to include in the result
        :param keep_all_rows: True = preserve the number of elements in the result (equivalent of LEFT JOIN in SQL)
        :param named_attributes: renamings and computations on attributes of self and group
        :return: an entity set representing the result of the aggregation/projection operator of entities from `group`
        per entity of `self`
        """
        return GroupBy.create(self, group, keep_all_rows=keep_all_rows,
                              attributes=attributes, named_attributes=named_attributes)

    aggregate = aggr  # aliased name for aggr

    def make_sql(self, select_fields=None):
        return 'SELECT {fields} FROM {from_}{where}'.format(
            fields=("DISTINCT " if self.distinct else "") + self.get_select_fields(select_fields),
            from_=self.from_clause,
            where=self.where_clause)

    # ---------- Fetch operators --------------------
    @property
    def fetch1(self):
        return Fetch1(self)

    @property
    def fetch(self):
        return Fetch(self)

    def head(self, limit=25, **fetch_kwargs):
        """
        shortcut to fetch the first few entries from query expression.
        Equivalent to fetch(order_by="KEY", limit=25)
        :param limit:  number of entries
        :param fetch_kwargs: kwargs for fetch
        :return: query result
        """
        return self.fetch(order_by="KEY", limit=limit, **fetch_kwargs)

    def tail(self, limit=25, **fetch_kwargs):
        """
        shortcut to fetch the last few entries from query expression.
        Equivalent to fetch(order_by="KEY DESC", limit=25)[::-1]
        :param limit:  number of entries
        :param fetch_kwargs: kwargs for fetch
        :return: query result
        """
        return self.fetch(order_by="KEY DESC", limit=limit, **fetch_kwargs)[::-1]

    def __len__(self):
        """
        number of elements in the result set.
        """
        return self.connection.query(
            'SELECT count({count}) FROM {from_}{where}'.format(
                count='DISTINCT `{pk}`'.format(pk='`,`'.join(self.primary_key)) if self.distinct and self.primary_key else '*',
                from_=self.from_clause,
                where=self.where_clause)).fetchone()[0]

    def __bool__(self):
        """
        :return:  True if the result is not empty. Equivalent to len(rel)>0 but may be more efficient.
        """
        return len(self) > 0

    def __contains__(self, item):
        """
        returns True if item is found in the .
        :param item: any restriction
        (item in query_expression) is equivalent to bool(query_expression & item) but may be executed more efficiently.
        """
        return bool(self & item)  # May be optimized e.g. using an EXISTS query

    def __iter__(self):
        self._iter_only_key = all(v.in_key for v in self.heading.attributes.values())
        self._iter_keys = self.fetch('KEY')
        return self

    def __next__(self):
        try:
            key = self._iter_keys.pop(0)
        except AttributeError:
            # self._iter_keys is missing because __iter__ has not been called.
            raise TypeError("'QueryExpression' object is not an iterator. Use iter(obj) to create an iterator.")
        except IndexError:
            raise StopIteration
        else:
            if self._iter_only_key:
                return key
            else:
                try:
                    return (self & key).fetch1()
                except DataJointError:
                    # The data may have been deleted since the moment the keys were fetched -- move on to next entry.
                    return next(self)

    def cursor(self, offset=0, limit=None, order_by=None, as_dict=False):
        """
        See expression.fetch() for input description.
        :return: query cursor
        """
        if offset and limit is None:
            raise DataJointError('limit is required when offset is set')
        sql = self.make_sql()
        if order_by is not None:
            sql += ' ORDER BY ' + ', '.join(order_by)
        if limit is not None:
            sql += ' LIMIT %d' % limit + (' OFFSET %d' % offset if offset else "")
        logger.debug(sql)
        return self.connection.query(sql, as_dict=as_dict)

    def __repr__(self):
        return super().__repr__() if config['loglevel'].lower() == 'debug' else self.preview()

    def preview(self, limit=None, width=None):
        """ :return: a string of preview of the contents of the query. """
        return preview(self, limit, width)

    def _repr_html_(self):
        """ :return: HTML to display table in Jupyter notebook. """
        return repr_html(self)


class Join(QueryExpression):
    """
    Join operator.
    Join is a private DataJoint class not exposed to users.  See QueryExpression.__mul__ for details.
    """

    @classmethod
    def create(cls, arg1, arg2, keep_all_rows=False):
        obj = cls()
        if inspect.isclass(arg2) and issubclass(arg2, QueryExpression):
            arg2 = arg2()   # instantiate if joining with a class
        assert_join_compatibility(arg1, arg2)
        if arg1.connection != arg2.connection:
            raise DataJointError("Cannot join query expressions from different connections.")
        obj._connection = arg1.connection
        obj._arg1 = cls.make_argument_subquery(arg1)
        obj._arg2 = cls.make_argument_subquery(arg2)
        obj._distinct = obj._arg1.distinct or obj._arg2.distinct
        obj._left = keep_all_rows
        obj._heading = obj._arg1.heading.join(obj._arg2.heading)
        obj.restrict(obj._arg1.restriction)
        obj.restrict(obj._arg2.restriction)
        return obj

    @staticmethod
    def make_argument_subquery(arg):
        """
        Decide when a Join argument needs to be wrapped in a subquery
        """
        return Subquery.create(arg) if isinstance(arg, (GroupBy, Projection)) or arg.restriction else arg

    @property
    def from_clause(self):
        return '{from1} NATURAL{left} JOIN {from2}'.format(
            from1=self._arg1.from_clause,
            left=" LEFT" if self._left else "",
            from2=self._arg2.from_clause)


class Union(QueryExpression):
    """
    Union is the private DataJoint class that implements the union operator.
    """

    __count = count()

    @classmethod
    def create(cls, arg1, arg2):
        obj = cls()
        if inspect.isclass(arg2) and issubclass(arg2, QueryExpression):
            arg2 = arg2()  # instantiate if a class
        if not isinstance(arg1, QueryExpression) or not isinstance(arg2, QueryExpression):
            raise DataJointError('an QueryExpression can only be unioned with another QueryExpression')
        if arg1.connection != arg2.connection:
            raise DataJointError("Cannot operate on QueryExpressions originating from different connections.")
        if set(arg1.heading.names) != set(arg2.heading.names):
            raise DataJointError('Union requires the same attributes in both arguments')
        if any(not v.in_key for v in arg1.heading.attributes.values()) or \
                all(not v.in_key for v in arg2.heading.attributes.values()):
            raise DataJointError('Union arguments must not have any secondary attributes.')
        obj._connection = arg1.connection
        obj._heading = arg1.heading
        obj._arg1 = arg1
        obj._arg2 = arg2
        return obj

    def make_sql(self, select_fields=None):
        return "SELECT {_fields} FROM {_from}{_where}".format(
            _fields=self.get_select_fields(select_fields),
            _from=self.from_clause,
            _where=self.where_clause)

    @property
    def from_clause(self):
        return ("(SELECT {fields} FROM {from1}{where1} UNION SELECT {fields} FROM {from2}{where2}) as `_u%x`".format(
            fields=self.get_select_fields(None), from1=self._arg1.from_clause,
            where1=self._arg1.where_clause,
            from2=self._arg2.from_clause,
            where2=self._arg2.where_clause)) % next(self.__count)



class GroupBy(QueryExpression):
    """
    GroupBy(rel, comp1='expr1', ..., compn='exprn')  yields an entity set with the primary key specified by rel.heading.
    The computed arguments comp1, ..., compn use aggregation operators on the attributes of rel.
    GroupBy is used QueryExpression.aggr and U.aggr.
    GroupBy is a private class in DataJoint, not exposed to users.
    """

    @classmethod
    def create(cls, arg, group, attributes, named_attributes, keep_all_rows=False):
        if inspect.isclass(group) and issubclass(group, QueryExpression):
            group = group()   # instantiate if a class
        attributes, named_attributes = Projection.prepare_attribute_lists(arg, attributes, named_attributes)
        assert_join_compatibility(arg, group)
        obj = cls()
        obj._keep_all_rows = keep_all_rows
        obj._arg = (Join.make_argument_subquery(group) if isinstance(arg, U)
                    else Join.create(arg, group, keep_all_rows=keep_all_rows))
        obj._connection = obj._arg.connection
        # always include primary key of arg
        attributes = (list(a for a in arg.primary_key if a not in named_attributes.values()) +
                      list(a for a in attributes if a not in arg.primary_key))
        obj._heading = obj._arg.heading.project(
            attributes, named_attributes, force_primary_key=arg.primary_key)
        return obj

    def make_sql(self, select_fields=None):
        return 'SELECT {fields} FROM {from_}{where} GROUP  BY `{group_by}`{having}'.format(
            fields=self.get_select_fields(select_fields),
            from_=self._arg.from_clause,
            where=self._arg.where_clause,
            group_by='`,`'.join(self.primary_key),
            having=re.sub(r'^ WHERE', ' HAVING', self.where_clause))

    def __len__(self):
        return len(Subquery.create(self))


class U:
    """
    dj.U objects are the universal sets representing all possible values of their attributes.
    dj.U objects cannot be queried on their own but are useful for forming some queries.
    dj.U('attr1', ..., 'attrn') represents the universal set with the primary key attributes attr1 ... attrn.
    The universal set is the set of all possible combinations of values of the attributes.
    Without any attributes, dj.U() represents the set with one element that has no attributes.

    Restriction:

    dj.U can be used to enumerate unique combinations of values of attributes from other expressions.

    The following expression yields all unique combinations of contrast and brightness found in the `stimulus` set:

    >>> dj.U('contrast', 'brightness') & stimulus

    Aggregation:

    In aggregation, dj.U is used for summary calculation over an entire set:

    The following expression yields one element with one attribute `s` containing the total number of elements in
    query expression `expr`:

    >>> dj.U().aggr(expr, n='count(*)')

    The following expressions both yield one element containing the number `n` of distinct values of attribute `attr` in
    query expressio `expr`.

    >>> dj.U().aggr(expr, n='count(distinct attr)')
    >>> dj.U().aggr(dj.U('attr').aggr(expr), 'n=count(*)')

    The following expression yields one element and one attribute `s` containing the sum of values of attribute `attr`
    over entire result set of expression `expr`:

    >>> dj.U().aggr(expr, s='sum(attr)')

    The following expression yields the set of all unique combinations of attributes `attr1`, `attr2` and the number of
    their occurrences in the result set of query expression `expr`.

    >>> dj.U(attr1,attr2).aggr(expr, n='count(*)')

    Joins:

    If expression `expr` has attributes 'attr1' and 'attr2', then expr * dj.U('attr1','attr2') yields the same result
    as `expr` but `attr1` and `attr2` are promoted to the the primary key.  This is useful for producing a join on
    non-primary key attributes.
    For example, if `attr` is in both expr1 and expr2 but not in their primary keys, then expr1 * expr2 will throw
    an error because in most cases, it does not make sense to join on non-primary key attributes and users must first
    rename `attr` in one of the operands.  The expression dj.U('attr') * rel1 * rel2 overrides this constraint.
    """

    def __init__(self, *primary_key):
        self._primary_key = primary_key

    @property
    def primary_key(self):
        return self._primary_key

    def __and__(self, query_expression):
        if inspect.isclass(query_expression) and issubclass(query_expression, QueryExpression):
            query_expression = query_expression()   # instantiate if a class
        if not isinstance(query_expression, QueryExpression):
            raise DataJointError('Set U can only be restricted with a QueryExpression.')
        return Projection.create(query_expression, attributes=self.primary_key,
                                 named_attributes=dict(), include_primary_key=False)

    def __mul__(self, query_expression):
        """
        Joining U with a query expression has the effect of promoting the attributes of U to the primary key of
        the other query expression.
        :param query_expression: a query expression to join with.
        :return: a copy of the other query expression with the primary key extended.
        """
        if inspect.isclass(query_expression) and issubclass(query_expression, QueryExpression):
            query_expression = query_expression()   # instantiate if a class
        if not isinstance(query_expression, QueryExpression):
            raise DataJointError('Set U can only be joined with a QueryExpression.')
        result = query_expression.copy()
        result._heading = result.heading.extend_primary_key(self.primary_key)
        return result

    def aggr(self, group, **named_attributes):
        """
        Aggregation of the type U('attr1','attr2').aggr(group, computation="QueryExpression")
        has the primary key ('attr1','attr2') and performs aggregation computations for all matching elements of `group`.
        :param group:  The query expression to be aggregated.
        :param named_attributes: computations of the form new_attribute="sql expression on attributes of group"
        :return: The derived query expression
        """
        if self.primary_key:
            return GroupBy.create(
                self, group=group, keep_all_rows=False, attributes=(), named_attributes=named_attributes)
        return Projection.create(group, attributes=(), named_attributes=named_attributes, include_primary_key=False)

    aggregate = aggr  # alias for aggr
