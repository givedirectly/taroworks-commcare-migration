import pytest
from html import escape

from commcare.xforms.classes import (
    Language,
    Option, 
    Question, 
    QuestionType
)
from commcare.migration.surveys.formulas import (
    CalcIsValError,
    translate_calculation, 
    translate_validation
)


@pytest.mark.parametrize(
    "formula,expectation",
    [
        (
            "tw.section.question.value = 'string';",
            "'string'"
        ),
        (
            "tw.section.question.value = 5;",
            "5"
        )
    ]
)
def test_simple_assignment(formula, expectation):
    actual = translate_calculation(formula, question_name = "question", other_questions = [])
    assert actual == expectation


@pytest.mark.parametrize(
    "formula,expectation",
    [
        (
            "tw.section.question.value = (tw.section.other_question.value > 3) ? 'string' : 'other string';",
            "if(#form/survey/section/other_question > 3, 'string', 'other string')"
        ),
        (
            "tw.section.question.value = tw.section.other_question.value > 3 ? 'string' : 'other string';",
            "if(#form/survey/section/other_question > 3, 'string', 'other string')"
        ),
    ]
)
def test_one_line_if(formula, expectation):
    actual = translate_calculation(formula, question_name = "question", other_questions = [])
    assert actual == expectation


@pytest.mark.parametrize(
    "formula,expectation",
    [
        (
            "if (tw.section.other_question.value > 3) { tw.section.question.value = 'string'; }",
            "if(#form/survey/section/other_question > 3, 'string', '')"
        ),
        (
            "if (tw.section.other_question.value > 3) { tw.section.question.value = 'string'; } else { tw.section.question.value = 'other string'; }",
            "if(#form/survey/section/other_question > 3, 'string', 'other string')"
        ),
        (
            "if (tw.section.other_question.value > 3) tw.section.question.value = 'string'; else tw.section.question.value = 'other string';",
            "if(#form/survey/section/other_question > 3, 'string', 'other string')"
        ),
        (
            "if (tw.section.other_question.value > 3) tw.section.question.value = 'string'; else if (tw.section.other_question.value == 2) tw.section.question.value = 'other string'; else tw.section.question.value = 'yet another string'; ",
            "if(#form/survey/section/other_question > 3, 'string', if(#form/survey/section/other_question = 2, 'other string', 'yet another string'))"
        ),
    ]
)
def test_if_else(formula, expectation):
    actual = translate_calculation(formula, question_name = "question", other_questions = [])
    assert actual == expectation


@pytest.mark.parametrize(
    "formula,expectation",
    [
        (
            "if (tw.section.other_question.value > 3) { if (tw.section.yet_other_question.value == 2) tw.section.question.value = 'string'; else tw.section.question.value = 'other string'; }",
            "if(#form/survey/section/other_question > 3, if(#form/survey/section/yet_other_question = 2, 'string', 'other string'), '')"
        ),
        (
            "if (tw.section.other_question.value > 3) { if (tw.section.yet_other_question.value == 2) tw.section.question.value = 'string'; else tw.section.question.value = 'other string'; } else tw.section.question.value = 'yet another string';",
            "if(#form/survey/section/other_question > 3, if(#form/survey/section/yet_other_question = 2, 'string', 'other string'), 'yet another string')"
        ),
        (
            "if (tw.section.other_question.value > 3) { if (tw.section.yet_other_question.value == 2) tw.section.question.value = 'string'; else if (tw.section.yet_other_question.value == 1) tw.section.question.value = 'other string'; } else tw.section.question.value = 'yet another string';",
            "if(#form/survey/section/other_question > 3, if(#form/survey/section/yet_other_question = 2, 'string', if(#form/survey/section/yet_other_question = 1, 'other string', '')), 'yet another string')"
        ),
    ]
)
def test_nested_if_else(formula, expectation):
    actual = translate_calculation(formula, question_name = "question", other_questions = [])
    assert actual == expectation


@pytest.mark.parametrize(
    "formula,expectation",
    [
        (
            "tw.section.question.value = 'string'; // a comment here",
            "'string'"
        ),
        (
            "tw.section.question.value = 'string'; /* a multi-line comment here */",
            "'string'"
        ),
        (
            "tw.section.question.value = /* a multi-line comment here */ 'string';",
            "'string'"
        ),
    ]
)
def test_comments_ignored(formula, expectation):
    actual = translate_calculation(formula, question_name = "question", other_questions = [])
    assert actual == expectation


@pytest.mark.parametrize(
    "formula,expectation",
    [
        (
            "tw.section.question.value = tw.section.other_question.value == 2;",
            "#form/survey/section/other_question = 2"
        ),
        (
            "tw.section.question.value = tw.section.other_question.value === 2;",
            "#form/survey/section/other_question = 2"
        ),
        (
            "tw.section.question.value = tw.section.other_question.value != 2;",
            "#form/survey/section/other_question != 2"
        ),
        (
            "tw.section.question.value = tw.section.other_question.value !== 2;",
            "#form/survey/section/other_question != 2"
        ),
        (
            "tw.section.question.value = tw.section.other_question.value > 2;",
            "#form/survey/section/other_question > 2"
        ),
        (
            "tw.section.question.value = tw.section.other_question.value >= 2;",
            "#form/survey/section/other_question >= 2"
        ),
        (
            "tw.section.question.value = tw.section.other_question.value < 2;",
            "#form/survey/section/other_question < 2"
        ),
        (
            "tw.section.question.value = tw.section.other_question.value <= 2;",
            "#form/survey/section/other_question <= 2"
        ),
        (
            "tw.section.question.value = tw.section.other_question.value && tw.section.yet_another_question.value;",
            "#form/survey/section/other_question and #form/survey/section/yet_another_question"
        ),
        (
            "tw.section.question.value = tw.section.other_question.value || tw.section.yet_another_question.value;",
            "#form/survey/section/other_question or #form/survey/section/yet_another_question"
        ),
    ]
)
def test_operators(formula, expectation):
    actual = translate_calculation(escape(formula), question_name = "question", other_questions = [])
    assert actual == expectation


@pytest.mark.parametrize(
    "formula,expectation",
    [
        (
            "tw.section.question.value = tw.section.other_question.value == null;",
            "not(#form/survey/section/other_question)"
        ),
        (
            "tw.section.question.value = tw.section.other_question.value != null;",
            "boolean(#form/survey/section/other_question)"
        ),
    ]
)
def test_comparison_with_null(formula, expectation):
    actual = translate_calculation(formula, question_name = "question", other_questions = [])
    assert actual == expectation


@pytest.mark.parametrize(
    "formula,expectation",
    [
        (
            "tw.section.question.value = tw.section.other_question.hasAnswer;",
            "boolean(#form/survey/section/other_question)"
        ),
        (
            "tw.section.question.value = !tw.section.other_question.hasAnswer;",
            "not(boolean(#form/survey/section/other_question))"
        ),
    ]
)
def test_hasAnswer(formula, expectation):
    actual = translate_calculation(formula, question_name = "question", other_questions = [])
    assert actual == expectation


@pytest.mark.parametrize(
    "formula,expectation",
    [
        (
            "tw.section.question.value = tw.section.other_question.value.length;",
            "string-length(#form/survey/section/other_question)"
        ),
        (
            "tw.section.question.value = tw.section.other_question.value.startsWith('substring');",
            "starts-with(#form/survey/section/other_question, 'substring')"
        ),
        (
            "tw.section.question.value = tw.section.other_question.value.endsWith('substring');",
            "ends-with(#form/survey/section/other_question, 'substring')"
        ),
        (
            "tw.section.question.value = tw.section.other_question.value.toUpperCase();",
            "upper-case(#form/survey/section/other_question)"
        ),
        (
            "tw.section.question.value = tw.section.other_question.value.toLowerCase();",
            "lower-case(#form/survey/section/other_question)"
        ),
        (
            "tw.section.question.value = tw.section.other_question.value.includes('substring');",
            "selected(#form/survey/section/other_question, 'substring')"
        ),
        (
            "tw.section.question.value = tw.section.other_question.value.contains('substring');",
            "selected(#form/survey/section/other_question, 'substring')"
        ),
    ]
)
def test_methods(formula, expectation):
    actual = translate_calculation(formula, question_name = "question", other_questions = [])
    assert actual == expectation


@pytest.mark.parametrize(
    "formula,expectation",
    [
        (
            "tw.section.question.value = new Date();",
            "now()"
        ),
        (
            "tw.section.question.value = new Date(tw.section.other_question.value);",
            "date(#form/survey/section/other_question)"
        ),
    ]
)
def test_new_date(formula, expectation):
    actual = translate_calculation(formula, question_name = "question", other_questions = [])
    assert actual == expectation


def test_regex():
    formula = "tw.section.question.value = /regex/.test(tw.section.other_question.value);"
    expectation = "regex(#form/survey/section/other_question, 'regex')"
    actual = translate_calculation(formula, question_name = "question", other_questions = [])
    assert actual == expectation


@pytest.mark.parametrize(
    "formula,expectation",
    [
        (
            "if (tw.section.question.value > 2) throw 'error';",
            (
                "not(. > 2)", 
                "error"
            )
        ),
        (
            "if (tw.section.question.value > 2) throw 'error'; else if (tw.section.question.value > tw.section.other_question.value) throw 'other error';",
            (
                "not(. > 2 or . > #form/survey/section/other_question)", 
                "Your response is invalid for one of the following reasons:\nerror\nother error"
            )
        ),
    ]
)
def test_validation(formula, expectation):
    actual = translate_validation(formula, question_name = "question", other_questions = [])
    assert actual == expectation


def test_validation_single_select_picklist():
    formula = "if (tw.section.question.value == 'True') throw 'error';"
    other_questions = [
        Question(
            name = 'question',
            type = QuestionType.single_select,
            label = {Language.english: 'Single-select picklist question'},
            options = [
                Option(
                    name = 'true',
                    label = {
                        Language.english: 'True'
                    }
                )
            ]
        )
    ]
    actual = translate_validation(formula, question_name = "question", other_questions = other_questions)
    expectation = (
        "not(. = 'true')",
        "error"
    )
    assert actual == expectation


def test_validation_multi_select_picklist():
    formula = "if (tw.section.question.value == 'True') throw 'error';"
    other_questions = [
        Question(
            name = 'question',
            type = QuestionType.multi_select,
            label = {Language.english: 'Multi-select picklist question'},
            options = [
                Option(
                    name = 'true',
                    label = {
                        Language.english: 'True'
                    }
                )
            ]
        )
    ]
    actual = translate_validation(formula, question_name = "question", other_questions = other_questions)
    expectation = (
        "not(selected(., 'true'))",
        "error"
    )
    assert actual == expectation


def test_calc_is_val_error():
    formula = "if (tw.section.question.value > 2) throw 'error';"
    try:
        translate_calculation(formula, question_name = "question", other_questions = [])
    except CalcIsValError:
        pass
    else:
        raise AssertionError()


def test_not_implemented_error_calculation():
    formula = "var x = 3; tw.section.question.value = x;"
    try:
        translate_calculation(formula, question_name = "question", other_questions = [])
    except NotImplementedError:
        pass
    else:
        raise AssertionError()
    

def test_not_implemented_error_validation():
    formula = "var x = 3; if (tw.section.question.value > 2) throw 'error';"
    try:
        actual = translate_validation(formula, question_name = "question", other_questions = [])
    except NotImplementedError:
        pass
    else:
        print(actual)
        raise AssertionError()


@pytest.mark.parametrize(
    "formula,expectation",
    [
        (
            "tw.section.question.value = tw.section.single_select_picklist_question.value == 'Option value' ? 'string' : 'other string';",
            "if(#form/survey/section/single_select_picklist_question = 'option_value', 'string', 'other string')"
        ),
        (
            "tw.section.question.value = tw.section.single_select_picklist_question.value != 'Option value' ? 'string' : 'other string';",
            "if(#form/survey/section/single_select_picklist_question != 'option_value', 'string', 'other string')"
        ),
        (
            "tw.section.question.value = tw.section.text_question.value == 'Option value' ? 'string' : 'other string';",
            "if(#form/survey/section/text_question = 'Option value', 'string', 'other string')"
        ),
    ]
)
def test_comparison_with_single_select_picklist(formula, expectation):
    other_questions = [
        Question(
            name = 'text_question',
            type = QuestionType.text,
            label = {Language.english: 'Text question'}
        ),
        Question(
            name = 'single_select_picklist_question',
            type = QuestionType.single_select,
            label = {Language.english: 'Single-select picklist question'},
            options = [
                Option(
                    name = 'option_value',
                    label = {
                        Language.english: 'Option value',
                        Language.artificial: 'art option value'
                    }
                )
            ]
        )
    ]
    actual = translate_calculation(formula, question_name = "question", other_questions = other_questions)
    assert actual == expectation


@pytest.mark.parametrize(
    "formula,expectation",
    [
        (
            "tw.section.question.value = tw.section.multi_select_picklist_question.value == 'Option value' ? 'string' : 'other string';",
            "if(selected(#form/survey/section/multi_select_picklist_question, 'option_value'), 'string', 'other string')"
        ),
        (
            "tw.section.question.value = tw.section.multi_select_picklist_question.value != 'Option value' ? 'string' : 'other string';",
            "if(not(selected(#form/survey/section/multi_select_picklist_question, 'option_value')), 'string', 'other string')"
        ),
        (
            "tw.section.question.value = tw.section.text_question.value == 'Option value' ? 'string' : 'other string';",
            "if(#form/survey/section/text_question = 'Option value', 'string', 'other string')"
        ),
    ]
)
def test_comparison_with_multi_select_picklist(formula, expectation):
    other_questions = [
        Question(
            name = 'text_question',
            type = QuestionType.text,
            label = {Language.english: 'Text question'}
        ),
        Question(
            name = 'multi_select_picklist_question',
            type = QuestionType.multi_select,
            label = {Language.english: 'Multi-select picklist question'},
            options = [
                Option(
                    name = 'option_value',
                    label = {
                        Language.english: 'Option value',
                        Language.artificial: 'art option value'
                    }
                )
            ]
        )
    ]
    actual = translate_calculation(formula, question_name = "question", other_questions = other_questions)
    assert actual == expectation


@pytest.mark.parametrize(
    "formula,expectation",
    [
        (
            "tw.section.question.value = 'string' + 'other string';",
            "concat('string', 'other string')"
        ),
        (
            "tw.section.question.value = tw.section.text_question.value + 'string';",
            "concat(#form/survey/section/text_question, 'string')"
        ),
        (
            "tw.section.question.value = tw.section.random_question.value + tw.section.text_question.value;",
            "concat(#form/survey/section/random_question, #form/survey/section/text_question)"
        ),
    ]
)
def test_addition_of_strings(formula, expectation):
    other_questions = [
        Question(
            name = 'text_question',
            type = QuestionType.text,
            label = {Language.english: 'Text question'}
        )
    ]
    actual = translate_calculation(formula, question_name = "question", other_questions = other_questions)
    assert actual == expectation