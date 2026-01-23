import pytest, re
from xml.dom import minidom

from commcare.xforms.classes import (
    Calculation,
    Group,
    Language,
    QuestionType,
    Question,
    Language,
    Option,
    Survey,
    ShowLogic,
    Validation
)

EXPECTATIONS_DIR = 'commcare/xforms/tests/expectations/'
XMLNS = 'http://openrosa.org/formdesigner/3B5D2FA0-D3BE-4DFC-A2F4-87DE19E788D0'


def normalise_xml(model: minidom.Document) -> str:
    pretty_xml = model.toprettyxml(indent="\t").strip()
    return re.sub(r'\n\s+\n', '\n', pretty_xml)


@pytest.mark.parametrize(
    "question_type", 
    [
        QuestionType.text,
        QuestionType.integer,
        QuestionType.decimal,
        QuestionType.date,
        QuestionType.datetime,
        QuestionType.photo,
        QuestionType.signature,
        QuestionType.label,
        QuestionType.gps,
        QuestionType.barcode
    ])
def test_question_types_without_options(question_type):
    question = Question(
        name = question_type,
        type = question_type,
        label = {
            Language.english: question_type,
            Language.artificial: question_type
        }
    )
    survey = Survey(
        title = 'Survey',
        xmlns = XMLNS,
        version = 1,
        languages = [Language.english, Language.artificial],
        contents = [question]
    )
    actual = normalise_xml(minidom.parseString(survey.as_xml()))
    expectation = normalise_xml(minidom.parse(f'{EXPECTATIONS_DIR}/{question_type}.xml'))
    assert actual == expectation, f"xml mismatch\nactual:\n{actual}\nvs.\nexpectation:\n{expectation}"


@pytest.mark.parametrize(
    "question_type", 
    [
        QuestionType.single_select,
        QuestionType.multi_select,
    ])
def test_question_types_with_options(question_type):
    option_1 = Option(
        name = 'option_1',
        label = {
            Language.english: 'option 1',
            Language.artificial: 'option 1',
        }
    )
    option_2 = Option(
        name = 'option_2',
        label = {
            Language.english: 'option 2',
            Language.artificial: 'option 2',
        }
    )
    question = Question(
        name = question_type,
        type = question_type,
        label = {
            Language.english: question_type.replace('_', ' '),
            Language.artificial: question_type.replace('_', ' ')
        },
        options = [option_1, option_2]
    )
    survey = Survey(
        title = 'Survey',
        xmlns = XMLNS,
        version = 1,
        languages = [Language.english, Language.artificial],
        contents = [question]
    )
    actual = normalise_xml(minidom.parseString(survey.as_xml()))
    expectation = normalise_xml(minidom.parse(f'{EXPECTATIONS_DIR}/{question_type}.xml'))
    assert actual == expectation, f"xml mismatch\nactual:\n{actual}\nvs.\nexpectation:\n{expectation}"


def test_question_required():
    question = Question(
        name = 'text',
        type = QuestionType.text,
        label = {
            Language.english: 'text',
            Language.artificial: 'text'
        },
        required = True
    )
    survey = Survey(
        title = 'Survey',
        xmlns = XMLNS,
        version = 1,
        languages = [Language.english, Language.artificial],
        contents = [question]
    )
    actual = normalise_xml(minidom.parseString(survey.as_xml()))
    expectation = normalise_xml(minidom.parse(f'{EXPECTATIONS_DIR}/question_required.xml'))
    assert actual == expectation, f"xml mismatch\nactual:\n{actual}\nvs.\nexpectation:\n{expectation}"


def test_question_with_hint_help():
    question = Question(
        name = 'text',
        type = QuestionType.text,
        label = {
            Language.english: 'text',
            Language.artificial: 'text'
        },
        hint = {
            Language.english: 'hint message',
            Language.artificial: 'hint message'
        },
        help = {
            Language.english: 'help message',
            Language.artificial: 'help message'
        }
    )
    survey = Survey(
        title = 'Survey',
        xmlns = XMLNS,
        version = 1,
        languages = [Language.english, Language.artificial],
        contents = [question]
    )
    actual = normalise_xml(minidom.parseString(survey.as_xml()))
    expectation = normalise_xml(minidom.parse(f'{EXPECTATIONS_DIR}/question_with_hint_help.xml'))
    assert actual == expectation, f"xml mismatch\nactual:\n{actual}\nvs.\nexpectation:\n{expectation}"


def test_question_with_comment():
    question = Question(
        name = 'text',
        type = QuestionType.text,
        label = {
            Language.english: 'text',
            Language.artificial: 'text'
        },
        comment = 'comment\nwith newline'
    )
    survey = Survey(
        title = 'Survey',
        xmlns = XMLNS,
        version = 1,
        languages = [Language.english, Language.artificial],
        contents = [question]
    )
    actual = normalise_xml(minidom.parseString(survey.as_xml()))
    expectation = normalise_xml(minidom.parse(f'{EXPECTATIONS_DIR}/question_with_comment.xml'))
    assert actual == expectation, f"xml mismatch\nactual:\n{actual}\nvs.\nexpectation:\n{expectation}"


def test_question_with_validation():
    question = Question(
        name = 'text',
        type = QuestionType.text,
        label = {
            Language.english: 'text',
            Language.artificial: 'text'
        },
        validation = Validation(
            message = {
                Language.english: 'Your answer must start with "test".',
                Language.artificial: 'Your answer must start with "test".'
            },
            validation = "starts-with(., 'test')"
        )
    )
    survey = Survey(
        title = 'Survey',
        xmlns = XMLNS,
        version = 1,
        languages = [Language.english, Language.artificial],
        contents = [question]
    )
    actual = normalise_xml(minidom.parseString(survey.as_xml()))
    expectation = normalise_xml(minidom.parse(f'{EXPECTATIONS_DIR}/question_with_validation.xml'))
    assert actual == expectation, f"xml mismatch\nactual:\n{actual}\nvs.\nexpectation:\n{expectation}"


def test_question_with_reference():
    referenced_question = Question(
        name = 'text',
        type = QuestionType.text,
        label = {
            Language.english: 'text',
            Language.artificial: 'text'
        }
    )
    question_with_reference = Question(
        name = 'label_with_reference',
        type = QuestionType.label,
        label = {
            Language.english: 'text was: {}',
            Language.artificial: 'text was: {}'
        },
        references = [referenced_question]
    )
    survey = Survey(
        title = 'Survey',
        xmlns = XMLNS,
        version = 1,
        languages = [Language.english, Language.artificial],
        contents = [referenced_question, question_with_reference]
    )
    actual = normalise_xml(minidom.parseString(survey.as_xml()))
    expectation = normalise_xml(minidom.parse(f'{EXPECTATIONS_DIR}/question_with_reference.xml'))
    assert actual == expectation, f"xml mismatch\nactual:\n{actual}\nvs.\nexpectation:\n{expectation}"


def test_question_with_show_logic():
    option_1 = Option(
        name = 'option_1',
        label = {
            Language.english: 'option 1',
            Language.artificial: 'option 1',
        }
    )
    option_2 = Option(
        name = 'option_2',
        label = {
            Language.english: 'option 2',
            Language.artificial: 'option 2',
        }
    )
    referenced_question = Question(
        name = 'single_select',
        type = QuestionType.single_select,
        label = {
            Language.english: 'single select',
            Language.artificial: 'single select'
        },
        options = [option_1, option_2]
    )
    question_with_show_logic = Question(
        name = 'text',
        type = QuestionType.text,
        label = {
            Language.english: 'text',
            Language.artificial: 'text'
        },
        show_logic = ShowLogic(
            logic = '{} = {}',
            references = [referenced_question, option_1]
        )
    )
    survey = Survey(
        title = 'Survey',
        xmlns = XMLNS,
        version = 1,
        languages = [Language.english, Language.artificial],
        contents = [referenced_question, question_with_show_logic]
    )
    actual = normalise_xml(minidom.parseString(survey.as_xml()))
    expectation = normalise_xml(minidom.parse(f'{EXPECTATIONS_DIR}/question_with_show_logic.xml'))
    assert actual == expectation, f"xml mismatch\nactual:\n{actual}\nvs.\nexpectation:\n{expectation}"


def test_calculation():
    question = Question(
        name = 'calculation',
        type = QuestionType.calculation,
        calculation = Calculation("if(true(), 'value', 'other')")
    )
    survey = Survey(
        title = 'Survey',
        xmlns = XMLNS,
        version = 1,
        languages = [Language.english, Language.artificial],
        contents = [question]
    )
    actual = normalise_xml(minidom.parseString(survey.as_xml()))
    expectation = normalise_xml(minidom.parse(f'{EXPECTATIONS_DIR}/calculation.xml'))
    assert actual == expectation, f"xml mismatch\nactual:\n{actual}\nvs.\nexpectation:\n{expectation}"


def test_calculation_with_references():
    option_1 = Option(
        name = 'option_1',
        label = {
            Language.english: 'option 1',
            Language.artificial: 'option 1',
        }
    )
    option_2 = Option(
        name = 'option_2',
        label = {
            Language.english: 'option 2',
            Language.artificial: 'option 2',
        }
    )
    referenced_question = Question(
        name = 'single_select',
        type = QuestionType.single_select,
        label = {
            Language.english: 'single select',
            Language.artificial: 'single select'
        },
        options = [option_1, option_2]
    )
    calculation_with_references = Question(
        name = 'calculation',
        type = QuestionType.calculation,
        calculation = Calculation(
            calculation = "if({} = {}, 'value', 'other')",
            references = [referenced_question, option_1]
        )
    )
    survey = Survey(
        title = 'Survey',
        xmlns = XMLNS,
        version = 1,
        languages = [Language.english, Language.artificial],
        contents = [referenced_question, calculation_with_references]
    )
    actual = normalise_xml(minidom.parseString(survey.as_xml()))
    expectation = normalise_xml(minidom.parse(f'{EXPECTATIONS_DIR}/calculation_with_references.xml'))
    assert actual == expectation, f"xml mismatch\nactual:\n{actual}\nvs.\nexpectation:\n{expectation}"


def test_group():
    question = Question(
        name = 'text',
        type = QuestionType.text,
        label = {
            Language.english: 'text',
            Language.artificial: 'text'
        },
    )
    group = Group(
        name = 'group',
        label = {
            Language.english: 'group',
            Language.artificial: 'group'
        },
        contents = [question]
    )
    survey = Survey(
        title = 'Survey',
        xmlns = XMLNS,
        version = 1,
        languages = [Language.english, Language.artificial],
        contents = [group]
    )
    actual = normalise_xml(minidom.parseString(survey.as_xml()))
    expectation = normalise_xml(minidom.parse(f'{EXPECTATIONS_DIR}/group.xml'))
    assert actual == expectation, f"xml mismatch\nactual:\n{actual}\nvs.\nexpectation:\n{expectation}"


def test_repeat_group():
    integer_question = Question(
        name = 'integer',
        type = QuestionType.integer,
        label = {
            Language.english: 'integer',
            Language.artificial: 'integer'
        }
    )
    question_in_group = Question(
        name = 'text',
        type = QuestionType.text,
        label = {
            Language.english: 'text',
            Language.artificial: 'text'
        },
    )
    group = Group(
        name = 'repeat_group',
        label = {
            Language.english: 'repeat group',
            Language.artificial: 'repeat group'
        },
        repeat = integer_question,
        contents = [question_in_group]
    )
    survey = Survey(
        title = 'Survey',
        xmlns = XMLNS,
        version = 1,
        languages = [Language.english, Language.artificial],
        contents = [integer_question, group]
    )
    actual = normalise_xml(minidom.parseString(survey.as_xml()))
    expectation = normalise_xml(minidom.parse(f'{EXPECTATIONS_DIR}/repeat_group.xml'))
    assert actual == expectation, f"xml mismatch\nactual:\n{actual}\nvs.\nexpectation:\n{expectation}"


def test_question_with_translation():
    question = Question(
        name = 'text',
        type = QuestionType.text,
        label = {
            Language.english: 'text',
            Language.artificial: 'text',
            Language.portuguese: 'translation'
        },
    )
    survey = Survey(
        title = 'Survey',
        xmlns = XMLNS,
        version = 1,
        languages = [Language.english, Language.artificial, Language.portuguese],
        contents = [question]
    )
    actual = normalise_xml(minidom.parseString(survey.as_xml()))
    expectation = normalise_xml(minidom.parse(f'{EXPECTATIONS_DIR}/question_with_translation.xml'))
    assert actual == expectation, f"xml mismatch\nactual:\n{actual}\nvs.\nexpectation:\n{expectation}"