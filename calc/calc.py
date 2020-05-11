import re
import time

# delay in operation / to emit long cpu calculations
DELAY = 30

# only integer values is supported, float delimiter , or . aren't supported
# all supported operations
operations = [{'(', ')'},
              {'/', '*'},
              {'+', '-'}
              ]
all_supported_operations = set()
for op_set in operations:
    all_supported_operations.update(op_set)


def get_operation_priority(operation):
    for i in range(len(operations)):
        if operation in operations[i]:
            return i
    return -1  # not supported operation


class ErrorLvls:
    INFO = 0
    WARN = 1
    ERR = 2
    OFF = 3


USED_MIN_ERR_LEVEL = ErrorLvls.OFF
err_texts = ['INFO', 'WARN', 'ERR', 'OFF']


class Logger:
    def __init__(self):
        self._log_fd = None

    def init(self, log_file_name='log.txt'):
        if USED_MIN_ERR_LEVEL == ErrorLvls.OFF:
            return
        self._log_fd = open(log_file_name, 'w+')

    def log(self, message_str='', error_lvl=ErrorLvls.INFO, context=''):
        if USED_MIN_ERR_LEVEL == ErrorLvls.OFF:
            return
        if USED_MIN_ERR_LEVEL <= error_lvl:
            log_info = '\n[%s] %s: %s\n' % (err_texts[error_lvl], ('in %s ' % context) if context else '', message_str)
            if self._log_fd:
                self._log_fd.write(log_info)
            else:
                print(log_info)

    def stop(self):
        if USED_MIN_ERR_LEVEL == ErrorLvls.OFF:
            return
        if self._log_fd:
            self._log_fd.close()
            self._log_fd = None

    def __del__(self):
        if USED_MIN_ERR_LEVEL == ErrorLvls.OFF:
            return
        self.stop()


logger = Logger()


def log(message_str='', error_lvl=ErrorLvls.INFO, context=''):
    logger.log(message_str, error_lvl, context)


class Node:
    '''
    class Node,
    Note: used in class Tree
    each Node contains complex or simple math expression,
    if expression is complex, split it to childs and etc(recursive)
    res contains result of math expression or processing status or error
    Args:
        _level = deep level in Tree
        _expression_str = expression for this Node
        _operation = operation for this Node to aplly res to parent result
        children = elements of subtree
        is_simple = if Node contains only number in _expression_str
        is_valid = flag, set during parsing _expression_str & calculation, default True
        res = calculated result of _expression_str( depend recursive on all children's res and _operation)
    Attributes:
        max_level - maximum deep level for all created Node objects
    '''
    max_level = 0

    def __init__(self, expression_str, operation=None, level=0):
        self._level = level
        self._expression_str = expression_str
        self._operation = operation
        self.children = []
        self.is_simple = False
        self.is_valid = True
        self.res = None
        self._pre_parse()

    def get_expression_str(self):
        return self._expression_str

    def _pre_parse(self):
        '''
        check if expression is simple or not,
        check simple validation
        '''
        for op_set in operations:
            for op in op_set:
                if op in self._expression_str:
                    self.is_simple = False
                    return
        self.is_simple = True
        self.is_valid = bool(re.match('^[0-9]+$', self._expression_str) != None)
        if not self.is_valid:
            log('invalid node = %s in expression, node should contain only digits in 0..9!' %
                self._expression_str, ErrorLvls.ERR, 'Node:_pre_parse()')

    def remove_senseless_brackets(self):
        '''
        remove repetable brackets at begin and end
        :return: expression without senseless brackets
        '''
        pattern = '^\(+'
        double_brackets = re.search(pattern, self._expression_str)
        if not double_brackets:
            return
        double_brackets_str = double_brackets.group(0)
        close_double_brackets_str = ')' * len(double_brackets_str)
        if self._expression_str.endswith(close_double_brackets_str):
            self._expression_str = self._expression_str.replace(close_double_brackets_str, ')', 1)
            self._expression_str = self._expression_str.replace(double_brackets_str, '(', 1)

        # remove last brackets at begin and end if it's possible
        if self._expression_str[-1] == ')' and \
                self._expression_str[0] == '(':
            # check if this brackets is a pair
            candidate = self._expression_str[1:-1]
            if self._expression_str.count(')') == 1:
                self._expression_str = candidate
            else:
                close_index = candidate.find(')')
                open_index = candidate.find('(')
                close_index_end = candidate.rfind(')')
                open_index_end = candidate.rfind('(')

                if close_index == -1 or open_index == -1:
                    return
                if close_index > open_index and \
                        close_index_end > open_index_end:
                    self._expression_str = candidate

    def parse(self, node_creation, is_first_run=True):
        '''
        :input: node_creation - functor for create new Node;
        is_first_run - first or second run of parse func( depend on operation priority in expression)
        parse node expression and create subtree for this Node
        :return: -1 if parsing errors or nothing
        '''
        if not self.is_valid:
            return -1
        if self.is_simple:  # no need to parse simple nodes
            return

        # if expression like (((some expression))) - do remove brackets at begin & end
        self.remove_senseless_brackets()
        self._pre_parse()
        if self.is_simple:
            return

        node_expression = ''
        open_bracket_counter = 0
        close_bracket_counter = 0
        node_operation = None

        def add_node(expression, operation):
            node = node_creation(expression, operation, self._level + 1)
            if not node.is_valid:
                self.is_valid = False
                return -1
            self.add_child(node)
            if node.parse(node_creation) == -1:
                self.is_valid = False
                return -1

        for symbol in self._expression_str:
            if symbol in all_supported_operations:
                if symbol in operations[0]:                              # brakets
                    node_expression += str(symbol)
                    if symbol == ')':
                        if open_bracket_counter == 0 or open_bracket_counter <= close_bracket_counter:
                            log('close braket without open braket', ErrorLvls.ERR, 'Node:parse()')
                            self.res = 'error in expression'
                            self.is_valid = False
                            return -1
                        else:
                            close_bracket_counter += 1
                    else:
                        open_bracket_counter += 1
                else:                                               # *, /, +, -
                    if is_first_run and symbol in operations[2] or\
                            not is_first_run and symbol in operations[1]:  # first run - only +, - processed, second * /
                        if open_bracket_counter == 0 or\
                                close_bracket_counter == open_bracket_counter:  # properly brackets
                            if add_node(node_expression, node_operation) == -1:
                                return -1
                            node_operation = symbol
                            # reset
                            close_bracket_counter = 0
                            open_bracket_counter = 0
                            node_expression = ''
                    if node_expression != '':       # node doesn't created
                        node_expression += str(symbol)   # will be parsed after removing brackets
            else:                                           # number
                if re.match('^[0-9]$', symbol):
                    node_expression += str(symbol)
                else:                                       # invalid symbol
                    self.is_valid = False
                    return -1

        if node_expression != '' and node_expression != self._expression_str:
            if add_node(node_expression, node_operation) == -1:
                return -1

        # all operations +- processed,
        # parse second time for operations * /
        if not self.is_simple and len(self.children) == 0 and is_first_run:
            if self.parse(node_creation, not is_first_run) == -1:
                self.is_valid = False
                return -1

    def add_child(self, child):
        if not isinstance(child, Node):
            log('err in Node::add_child(): invalid child type\n')
            return
        self.children.append(child)
        if Node.max_level < child._level:
            Node.max_level = child._level

    def print_node(self):
        log('|', ErrorLvls.INFO)
        log('%s--> (%s) %s [%s] res = %s' %
            ('-' * 8 * self._level, self._operation, self._expression_str, self.is_simple, self.res),
            ErrorLvls.INFO)
        for child in self.children:
            child.print_node()

    def do_operation(self, res=0, val=0):
        if not res:
            res = 0
        if not self._operation and res == 0:
            res = val
            return res
        if self._operation == '-':
            return res - float(val)
        if self._operation == '+':
            return res + float(val)
        if self._operation == '*':
            return res * float(val)
        if self._operation == '/':
            # add delay to emit long cpu calculations
            time.sleep(DELAY)
            if val != 0:
                return float(res) / float(val)
            else:
                log('division by zero!', ErrorLvls.ERR, 'Node::calculate()')
                raise
        return res

    def calculate(self, parent=None):
        '''
        :input: parent - parent Node
        calculate math expression result for all childs recursive
        and apply calculated node result with self operation to parent result
        fill res for all Nodes in subtree and change parent Node res
        :return: -1 if calculating errors or nothing
        '''
        if not self.is_valid:
            self.res = None
            return -1
        if self.is_simple:
            self.res = int(self._expression_str)
            if not parent:                          # is root
                return
            try:
                parent.res = self.do_operation(parent.res, int(self._expression_str))
            except:
                self.is_valid = False
                self.res = None
                return -1
        else:
            for child in self.children:
                child.calculate(self)
                if not child.is_valid:
                    self.res = None
                    return -1
                if not child.is_simple:
                    try:
                        self.res = child.do_operation(self.res, child.res)
                    except:
                        log('error in operation %s expr = %s=%s res = %s' %
                            (child._operation, child._expression_str, child.res, self.res),
                            ErrorLvls.ERR, 'Node:calculate()')
                        self.is_valid = False
                        self.res = None
                        return -1


class Tree:
    '''
    :class: Tree,
    use to parse math expression
    root contains the whole math expression,
    if expression is complex, split it to childs and etc
    :return: result of math expression or processing status or error
    '''

    def __init__(self, expression_str):
        self._root = Node(expression_str)
        self.is_valid = True
        self.max_height = 0
        self._res = None
        if not self._root.is_valid:
            self.is_valid = False
        else:
            self.max_height = 1
            self._res = 0
            if self._root.is_simple:
                self._res = int(expression_str)
            else:
                self.parse()

    def parse(self):
        if not self.is_valid:
            return -1

        def create_node(val, s, lvl):
            return Node(val, s, lvl)

        if self._root.parse(create_node) == -1:
            self.is_valid = False
            return -1
        self.max_height = Node.max_level

    def print_tree(self):
        if not self.is_valid:
            return -1
        self._root.print_node()

    def calculate(self):
        if not self.is_valid:
            log('invalid expression = %s' % self._root.get_expression_str(), ErrorLvls.ERR, 'Tree:calculate')
            return None
        self._root.calculate()
        self._res = self._root.res
        return self._res


def is_expression_valid(expression_s):
    if expression_s == '':
        return False, 'expression is empty string!'
    open_brackets_count = expression_s.count('(')
    close_brackets_count = expression_s.count(')')
    is_valid = open_brackets_count == close_brackets_count
    err_text = ''
    if not is_valid:
        err_text = "count of '(' != count of ')'!"
    return is_valid, err_text


def parse_expression(expression_s, pid, delay=30):
    global DELAY
    DELAY = delay
    logger.init('./log_%s.txt' % pid)
    expression_s = expression_s.replace(' ', '')  # remove whitespaces
    log('expression = %s' % expression_s, ErrorLvls.INFO, 'parse_expression()')
    is_valid, err_text = is_expression_valid(expression_s)
    res = None
    err = None
    if not is_valid:
        log('invalid expression %s\n' % err_text, ErrorLvls.ERR, 'parse_expression()')
        err = err_text
    else:
        tree = Tree(expression_s)
        if not tree.is_valid:
            err = 'error in parsing'
        else:
            # tree.print_tree()
            res = tree.calculate()
            if not res:
                err = 'error in calculating'
            # tree.print_tree()
            log('res=%s tree_heigh = %s' % (res, tree.max_height), ErrorLvls.INFO, 'Tree:parse_expression()')
    logger.stop()
    return [res, err]
