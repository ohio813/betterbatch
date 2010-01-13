import sys
import operator
import re

def RegularExpressionTest(string, pattern):
    return re.match(pattern, string)

def ParseComparisonOperator(op_text):
    op = None

    if op_text.startswith(">="):
        op = operator.ge

    elif op_text.startswith("<="):
        op = operator.le

    elif op_text.startswith(">"):
        op = operator.gt

    elif op_text.startswith("<"):
        op = operator.lt

    elif op_text.startswith("="):
        op = operator.eq
    
    elif op_text.lower() == "startswith":
        op = unicode.startswith
        
    elif  op_text.lower() == "endsswith":
        op = unicode.endswith
    
    elif  op_text.lower() == "contains":
        op = unicode.__contains__
    
    elif op_text.lower() == "matches_regex":
        op = RegularExpressionTest
    
    else:
        raise RuntimeError("Unknown comparison type '%s'"% op_text)
    
    return op

def RunComparison(str1, operator, str2):
    return operator(str1, str2)
    
if __name__ == "__main__":
    str1 = unicode(sys.argv[1])
    op_text = sys.argv[2]
    str2 = unicode(sys.argv[3])
        
    qualifiers = [q.lower() for q in sys.argv[4:]]

    #print "---------------", (str1, op_text, str2, qualifiers)
    
    if "nocase" in qualifiers:
        str1 = str1.lower()
        str2 = str2.lower()
    
    if "asint" in qualifiers:
        str1 = int(str1)
        str2 = int(str2)
    
    op = ParseComparisonOperator(op_text)
    
    ret = RunComparison(str1, op, str2)
    
    # convert True or False to 0/1 for error return
    if ret:
        ret = 0
    else:
        ret = 1
    sys.exit(ret)
    
    