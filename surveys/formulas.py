import esprima, re
from html import unescape

from commcare.xforms.classes import Language, QuestionType


## Calculations ----

def translate_calculation(formula, question_name, other_questions):
    
    parsed_formula = esprima.parseScript(unescape(formula))
    
    if _has_throw_statement(parsed_formula):
        raise CalcIsValError()
    
    return _translate_node(parsed_formula, question_name, other_questions)

def _translate_node(node, question_name, questions):
    
    if node.type in translation_functions:
        translation_function = translation_functions[node.type]
        return translation_function(node, question_name, questions)
    
    raise NotImplementedError()

def _has_throw_statement(node):
    
    if node.type == "ThrowStatement":
        return True
    
    result = False
    for attr in dir(node):
        attr_value = getattr(node, attr)
        
        if isinstance(attr_value, list):
            for element in attr_value:
                result += _has_throw_statement(element)
        
        if isinstance(attr_value, esprima.nodes.Node):
            result += _has_throw_statement(attr_value)
    
    return result


## Validations ----

def translate_validation(formula, question_name, other_questions):
    
    parsed_formula = esprima.parseScript(unescape(formula))
    conditions, messages = _translate_validation_node(parsed_formula, question_name, other_questions)
    
    condition = f"not({' or '.join(conditions)})"

    if len(messages) == 1:
        message = messages[0]
    else:
        message = f'Your response is invalid for one of the following reasons:\n' + '\n'.join(sorted(set(messages)))

    return condition, message

def _translate_validation_node(node, question_name, questions):
    
    conditions, messages = [], []

    if node.type in ("BlockStatement", "Program"):
        if len(node.body) == 1:
            return _translate_validation_node(node.body[0], question_name, questions)
        else:
            raise NotImplementedError
    
    if node.type == "IfStatement":

        conditions.append(_translate_node(node.test, question_name, questions))
        
        consequent_conditions, consequent_messages = _translate_validation_node(node.consequent, question_name, questions)
        conditions.extend(consequent_conditions)
        messages.extend(consequent_messages)

        if node.alternate:
            alternate_conditions, alternate_messages = _translate_validation_node(node.alternate, question_name, questions)
            conditions.extend(alternate_conditions)
            messages.extend(alternate_messages)
        
    if node.type == "ThrowStatement":
        messages.append(node.argument.value)
    
    return conditions, messages


## Exceptions ----

class CalcIsValError(ValueError):
    pass


## Constants ----

binary_expression_operator_translations = {
    "==": "=",
    "===": "=", 
    "!==": "!=",
    "!=": "!=",
    "<": "<",
    ">": ">",
    ">=": ">=",
    "<=": "<=",
    "+": "+",
    "-": "-",
    "*": "*"
}

call_expression_function_translations = {
    'startsWith': 'starts-with({}, {})',
    'endsWith': 'ends-with({}, {})', 
    'toUpperCase': 'upper-case({})', 
    'toLowerCase': 'lower-case({})',
    'includes': 'selected({}, {})',
    'contains': 'selected({}, {})', 
        # ^ nuance above: translation is technically ambiguous bc in formulas that reference multi-select questions, 
        # we should translate to `selected` and in formulas that reference js lists, `contains`. but since the translation
        # will fail for formulas with js lists anyway, I am only handling the first case.
}


## Functions ----

def _translate_binary_expression(node, question_name, questions):
    """Anything structured as `{left_value} {operator} {right_value}`, such as: `3 + 4` or `tw.section.question.value == 'value'`"""

    translated_left = _translate_node(node.left, question_name, questions)
    translated_right = _translate_node(node.right, question_name, questions)
    
    if node.operator == "/":
        return f"{translated_left} div {translated_right}"
    
    if node.operator == "%":
        return f"mod({translated_left}, {translated_right})"
    
    if node.operator in binary_expression_operator_translations:

        translated_operator = binary_expression_operator_translations[node.operator]
        
        # Comparisons with null
        if translated_right is None:
            return _comparison_with_null(object = translated_left, operator = translated_operator)
        if translated_left is None:
            return _comparison_with_null(object = translated_right, operator = translated_operator)
        
        # Comparisons between picklist questions and their options
        if _is_comparison_with_picklist(translated_left, node.right, question_name, questions):
            return _comparison_with_picklist(translated_left, translated_operator, node.right, question_name, questions)
        if _is_comparison_with_picklist(translated_right, node.left, question_name, questions):
            return _comparison_with_picklist(translated_right, translated_operator, node.left, question_name, questions)
        
        # Concatenation of strings
        if translated_operator == "+" and (_is_string(translated_left, questions) or _is_string(translated_right, questions)):
            return f"concat({translated_left}, {translated_right})"

        # All other comparisons
        return f"{translated_left} {translated_operator} {translated_right}"
    
    raise NotImplementedError()

def _comparison_with_null(object, operator):
    if operator == "!=":
        return f"boolean({object})"
    if operator == "=":
        return f"not({object})"
    raise NotImplementedError()

def _is_comparison_with_picklist(potential_question, potential_option_node, question_name, questions):

    question_name_match = re.match(r'#form/survey/\w+/(\w+)$', potential_question)
    if not question_name_match and potential_question != ".":
        return False
    
    other_question_name = question_name if potential_question == "." else question_name_match.group(1)
    other_question = _get_question_by_name(other_question_name, questions)
    if not other_question or other_question.type not in (QuestionType.single_select, QuestionType.multi_select):
        return False
    
    if potential_option_node.type != "Literal":
        return False

    return True

def _get_question_by_name(question_name, questions):
    for question in questions:
        if question.name == question_name:
            return question

def _comparison_with_picklist(question, operator, value_node, question_name, questions):
    
    if operator in ("!=", "="):

        if question == ".":
            other_question = _get_question_by_name(question_name, questions)
            print(other_question)
        else:
            question_name_match = re.match(r'#form/survey/\w+/(\w+)$', question)
            other_question_name = question_name_match.group(1)
            other_question = _get_question_by_name(other_question_name, questions)

        language = next(lang for lang in other_question.label if lang != Language.artificial)
        for option in other_question.options:
            if option.label[language] == value_node.value:
                if other_question.type == QuestionType.multi_select:
                    if operator == "=":
                        return f"selected({question}, '{option.name}')"
                    elif operator == "!=":
                        return f"not(selected({question}, '{option.name}'))"
                    else:
                        raise NotImplementedError()
                return f"{question} {operator} '{option.name}'"
    
    raise NotImplementedError()

def _is_string(object, questions):
    if re.match(r"^'.+'$", object) or re.match(r'^".+"$', object):
        return True
    question_name_match = re.match(r'#form/survey/\w+/(\w+)$', object)
    if question_name_match:
        other_question_name = question_name_match.group(1)
        other_question = _get_question_by_name(other_question_name, questions)
        if other_question and other_question.type in (QuestionType.text, QuestionType.single_select, QuestionType.multi_select):
            return True
    return False
                        

def _translate_block_statement(node, question_name, questions):
    """
    Any number of lines of code inside braces, such as in an if-statement or for-loop:
    if (3 == 4) {
        // this is a block
        var value = 3;
        tw.section.question.value = value + 1;
    }
    """

    if len(node.body) == 1:
        return _translate_node(node.body[0], question_name, questions)
    
    raise NotImplementedError()


def _translate_call_expression(node, question_name, questions):
    """A function call, such as `'string'.startsWith('substring')`"""
    
    if node.callee.type == "MemberExpression":
        
        translated_property = _translate_node(node.callee.property, question_name, questions)
        
        if translated_property in call_expression_function_translations:
            translated_object = _translate_node(node.callee.object, question_name, questions)
            translated_arguments = [_translate_node(arg, question_name, questions) for arg in node.arguments]
            translated_function = call_expression_function_translations[translated_property]
            return translated_function.format(translated_object, *translated_arguments)
        
        if translated_property == 'test': # regex test
            if node.callee.object.type == 'Literal' and node.callee.object.regex:
                translated_object = _translate_node(node.callee.object, question_name, questions)
                if len(node.arguments) > 1:
                    raise NotImplementedError()
                translated_argument = _translate_node(node.arguments[0], question_name, questions)
                return f"regex({translated_argument}, {translated_object})"
    
    raise NotImplementedError()


def _translate_conditional_expression(node, question_name, questions):
    """A one-line conditional expression, such as `var x = (3 < 4) ? 'value1' : 'value2'`"""
    return _translate_if_statement(node, question_name, questions)


def _translate_expression_statement(node, question_name, questions):
    """An expression that sets or returns a value, such as `var value = 3` or simply `3`"""

    if node.expression.type == "AssignmentExpression":
        return _translate_assignment_expression(node.expression, question_name, questions)
    
    raise NotImplementedError()

def _translate_assignment_expression(node, question_name, questions):
    """An expression that sets a variable's value, such as `tw.section.question.value = 3`"""

    if node.operator == "=":
        translated_left = _translate_node(node.left, question_name, questions)
        if translated_left == ".": #translated_left.split('/')[-1] == question_name:
            return _translate_node(node.right, question_name, questions)
    
    raise NotImplementedError()


def _translate_identifier(node, question_name, questions):
    """Any reference to a named object. For example, in `tw.section.question.hasAnswer`, there are four identifiers: `tw`, `section`, `question` and `hasAnswer`"""
    return node.name


def _translate_if_statement(node, question_name, questions):
    """An if or if-else block, such as `if (3 == 4) { expression } else {expression}"""

    translated_test = _translate_node(node.test, question_name, questions)
    translated_consequent = _translate_node(node.consequent, question_name, questions)

    if node.alternate:
        translated_alternate = _translate_node(node.alternate, question_name, questions)
        return f"if({translated_test}, {translated_consequent}, {translated_alternate})"
    
    return f"if({translated_test}, {translated_consequent}, '')"


def _translate_literal(node, question_name, questions):
    r"""A directly-referenced value, such as `true`, `"hello"`, `3` or `/^\w+/` (a regex)"""

    if node.regex:
        if "'" in node.regex.pattern and '"' in node.regex.pattern:
            raise NotImplementedError()
        if "'" in node.regex.pattern:
            return f'"{node.regex.pattern}"'
        return f"'{node.regex.pattern}'"
    
    if isinstance(node.raw, bool):
        return "true()" if node.value else "false()"
    
    if isinstance(node.value, (str, int, float)):
        return node.raw
    
    if node.raw == "null" and not node.value:
        return None
    
    raise NotImplementedError()


def _translate_logical_expression(node, question_name, questions):
    """An `and` or `or` expression, such as `(3 == 4) && (1 < 2)"""
    
    translated_left = _translate_node(node.left, question_name, questions)
    translated_right = _translate_node(node.right, question_name, questions)

    if node.operator == "||":
        return f"{translated_left} or {translated_right}"
    
    if node.operator == "&&":
        return f"{translated_left} and {translated_right}"
    
    raise NotImplementedError()


def _translate_member_expression(node, question_name, questions):
    """An expression that retrieves a member of an object, denoted by `.` in javascript, such as `"string".length`"""
    
    translated_object = _translate_node(node.object, question_name, questions)
    translated_property = _translate_node(node.property, question_name, questions)
    
    if translated_object == "tw":
        return f"#form/survey/{translated_property}"
    
    section_match = re.match(r"#form/survey/\w+$", translated_object)
    if section_match:

        if translated_property == "current":
            return translated_object
        
        return f"{translated_object}/{translated_property}"
    
    question_match = re.match(r"#form/survey/\w+/(\w+)$", translated_object)
    if question_match:

        if translated_property in ("value", "valu", "hasAnswer"): # "valu" for confirmed typos
        
            if question_match.group(1) == question_name:
                translated_object = "."
            
            if translated_property == "hasAnswer":
                return f"boolean({translated_object})"
            
            return translated_object
        
        if translated_property == "length":
            if re.match(r"#form/survey/\w+/\w+$", translated_object):
                return f"string-length({translated_object})"

    raise NotImplementedError()


def _translate_new_expression(node, question_name, questions):
    """An expression such as `new Date()`"""
    
    if node.callee.type == "Identifier" and node.callee.name == "Date":
        
        if len(node.arguments) > 1:
            raise NotImplementedError()
        
        if node.arguments:
            translated_argument = _translate_node(node.arguments[0], question_name, questions)
            return f'date({translated_argument})'
        
        return 'now()'
    
    raise NotImplementedError()


def _translate_program(node, question_name, questions):
    """A whole script of javascript"""
    if node.sourceType == 'script' and len(node.body) == 1:
        return _translate_node(node.body[0], question_name, questions)
    raise NotImplementedError()


def _translate_unary_expression(node, question_name, questions):
    """An expression that modifies a varible or value such as `-3` (modifies 3) or `!(3 == 2)` (modifies (3==2))"""

    translated_argument = _translate_node(node.argument, question_name, questions)
    
    if node.operator == "-":
        return f"-{translated_argument}"
    
    if node.operator == "!":
        return f"not({translated_argument})"
    
    raise NotImplementedError()


## List ----

translation_functions = {
    "BinaryExpression": _translate_binary_expression,
    "BlockStatement": _translate_block_statement,
    "CallExpression": _translate_call_expression,
    "ConditionalExpression": _translate_conditional_expression,
    "ExpressionStatement": _translate_expression_statement,
    "Identifier": _translate_identifier,
    "IfStatement": _translate_if_statement,
    "Literal": _translate_literal,
    "LogicalExpression": _translate_logical_expression,
    "MemberExpression": _translate_member_expression,
    "NewExpression": _translate_new_expression,
    "Program": _translate_program,
    "UnaryExpression": _translate_unary_expression,
}