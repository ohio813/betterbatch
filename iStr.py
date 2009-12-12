# A Case insensitive string taken from the Python Cookbook
# http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/194371
#
# Updated Version taken from Book - Python Cookbook
#
#
#


class iStr(unicode):
    """
    Case insensitive string class.
    Behaves just like str, except that all comparisons and lookups
    are case insensitive.
    """

    def __init__(self, *args):
        
        unicode.__init__(self)
        self._lowered = unicode.lower(self)

    def __repr__(self):
        return '%s(%s)' % (type(self).__name__, unicode.__repr__(self))

    def __hash__(self):
        return hash(self._lowered)

    def lower(self):
        return self._lowered

    def replace(self, old, new, maxsplit = -1):
        # note - method isn't case sensitive!!
        return iStr(unicode.replace(self, old, new, maxsplit))

    def __cmp__(self, other):
        try:
            other = other.lower()
        except: pass

        return cmp(self._lowered, other)


def _OverrideMethods(method_name):
    '''Wrap the base string methods to make them case-insensitive '''

    # get the method from the string class
    original_method = getattr(unicode, method_name)

    # This is a function wrapper that takes:
    #   the self object
    #   some other 'possibly string' object
    #   any other arguments
    # it a) tries to lower case the other object
    #    b) returns the value of the str version of this function
    def comp_method_lower_override(self, other, *args):
        '''try lowercasing 'other', which is typically a string, but
            be prepared to use it as-is if lowering gives problems,
            since strings CAN be correctly compared with non-strings.
        '''
        try:
            other = other.lower()
        except AttributeError: 
            pass

        return original_method (self._lowered, other, *args)

    # set the attribute of this particular class to the wrapper function
    setattr(iStr, method_name, comp_method_lower_override)
    
    # in Python 2.4+, only, add the statement: x.func_name = name
    comp_method_lower_override.func_name = method_name

# apply the _make_case_insensitive function to specified methods
for name in 'eq lt le gt gt ne contains'.split():
    _OverrideMethods('__%s__' % name)
    
for name in 'count endswith find index rfind rindex startswith'.split():
    _OverrideMethods(name)
    
# note that we don't modify methods:
#    partition, rpartition, rsplit, rstrip, split, lstrip 
# of course, you can add modifications to them, too, if you prefer that.



