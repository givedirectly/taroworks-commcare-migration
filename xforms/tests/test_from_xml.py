import pytest
import xml.etree.ElementTree as ET

from migration.xforms.classes import (
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

from migration.xforms import build_survey_from_xform

EXPECTATIONS_DIR = 'migration/xforms/tests/expectations/'
LANGUAGES = {Language.english, Language.artificial}
XMLNS = 'http://openrosa.org/formdesigner/3B5D2FA0-D3BE-4DFC-A2F4-87DE19E788D0'


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
    xml = ET.parse(f'{EXPECTATIONS_DIR}/{question_type}.xml').getroot()
    actual = build_survey_from_xform(xml, xmlns = XMLNS, version = 1)
    question = Question(
        name = question_type,
        type = question_type,
        label = {
            Language.english: question_type,
            Language.artificial: question_type
        }
    )
    expectation = Survey(
        title = 'Survey',
        xmlns = XMLNS,
        version = 1,
        languages = LANGUAGES,
        contents = [question]
    )
    assert actual == expectation, f"xml mismatch\nactual:\n{actual}\nvs.\nexpectation:\n{expectation}"


@pytest.mark.parametrize(
    "question_type", 
    [
        QuestionType.single_select,
        QuestionType.multi_select,
    ])
def test_question_types_with_options(question_type):
    xml = ET.parse(f'{EXPECTATIONS_DIR}/{question_type}.xml').getroot()
    actual = build_survey_from_xform(xml, xmlns = XMLNS, version = 1)
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
    expectation = Survey(
        title = 'Survey',
        xmlns = XMLNS,
        version = 1,
        languages = LANGUAGES,
        contents = [question]
    )
    assert actual == expectation, f"xml mismatch\nactual:\n{actual}\nvs.\nexpectation:\n{expectation}"


def test_question_required():
    xml = ET.parse(f'{EXPECTATIONS_DIR}/question_required.xml').getroot()
    actual = build_survey_from_xform(xml, xmlns = XMLNS, version = 1)
    question = Question(
        name = 'text',
        type = QuestionType.text,
        label = {
            Language.english: 'text',
            Language.artificial: 'text'
        },
        required = True
    )
    expectation = Survey(
        title = 'Survey',
        xmlns = XMLNS,
        version = 1,
        languages = LANGUAGES,
        contents = [question]
    )
    assert actual == expectation, f"xml mismatch\nactual:\n{actual}\nvs.\nexpectation:\n{expectation}"


def test_question_with_hint_help():
    xml = ET.parse(f'{EXPECTATIONS_DIR}/question_with_hint_help.xml').getroot()
    actual = build_survey_from_xform(xml, xmlns = XMLNS, version = 1)
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
    expectation = Survey(
        title = 'Survey',
        xmlns = XMLNS,
        version = 1,
        languages = LANGUAGES,
        contents = [question]
    )
    assert actual == expectation, f"xml mismatch\nactual:\n{actual}\nvs.\nexpectation:\n{expectation}"


def test_question_with_comment():
    xml = ET.parse(f'{EXPECTATIONS_DIR}/question_with_comment.xml').getroot()
    actual = build_survey_from_xform(xml, xmlns = XMLNS, version = 1)
    question = Question(
        name = 'text',
        type = QuestionType.text,
        label = {
            Language.english: 'text',
            Language.artificial: 'text'
        },
        comment = 'comment\nwith newline'
    )
    expectation = Survey(
        title = 'Survey',
        xmlns = XMLNS,
        version = 1,
        languages = LANGUAGES,
        contents = [question]
    )
    assert actual == expectation, f"xml mismatch\nactual:\n{actual}\nvs.\nexpectation:\n{expectation}"


def test_question_with_validation():
    xml = ET.parse(f'{EXPECTATIONS_DIR}/question_with_validation.xml').getroot()
    actual = build_survey_from_xform(xml, xmlns = XMLNS, version = 1)
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
    expectation = Survey(
        title = 'Survey',
        xmlns = XMLNS,
        version = 1,
        languages = LANGUAGES,
        contents = [question]
    )
    assert actual == expectation, f"xml mismatch\nactual:\n{actual}\nvs.\nexpectation:\n{expectation}"


def test_question_with_reference():
    xml = ET.parse(f'{EXPECTATIONS_DIR}/question_with_reference.xml').getroot()
    actual = build_survey_from_xform(xml, xmlns = XMLNS, version = 1)
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
    expectation = Survey(
        title = 'Survey',
        xmlns = XMLNS,
        version = 1,
        languages = LANGUAGES,
        contents = [referenced_question, question_with_reference]
    )
    assert actual == expectation, f"xml mismatch\nactual:\n{actual}\nvs.\nexpectation:\n{expectation}"


def test_question_with_show_logic():
    xml = ET.parse(f'{EXPECTATIONS_DIR}/question_with_show_logic.xml').getroot()
    actual = build_survey_from_xform(xml, xmlns = XMLNS, version = 1)
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
            # not mentioning option_1 as a `reference` below bc from_xml does not extract those as references.
            # this is okay as option mentions do not change (they're the constant string option_value)
            # whereas question mentions do change (they're the question_name, which depends on position)
            logic = "{} = 'option_1'",
            references = [referenced_question]
        )
    )
    expectation = Survey(
        title = 'Survey',
        xmlns = XMLNS,
        version = 1,
        languages = LANGUAGES,
        contents = [referenced_question, question_with_show_logic]
    )
    assert actual == expectation, f"xml mismatch\nactual:\n{actual}\nvs.\nexpectation:\n{expectation}"


def test_calculation():
    xml = ET.parse(f'{EXPECTATIONS_DIR}/calculation.xml').getroot()
    actual = build_survey_from_xform(xml, xmlns = XMLNS, version = 1)
    question = Question(
        name = 'calculation',
        type = QuestionType.calculation,
        calculation = Calculation("if(true(), 'value', 'other')")
    )
    expectation = Survey(
        title = 'Survey',
        xmlns = XMLNS,
        version = 1,
        languages = LANGUAGES,
        contents = [question]
    )
    assert actual == expectation, f"xml mismatch\nactual:\n{actual}\nvs.\nexpectation:\n{expectation}"


def test_calculation_with_references():
    xml = ET.parse(f'{EXPECTATIONS_DIR}/calculation_with_references.xml').getroot()
    actual = build_survey_from_xform(xml, xmlns = XMLNS, version = 1)
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
            # not mentioning option_1 as a `reference` below bc from_xml does not extract those as references.
            # this is okay as option mentions do not change (they're the constant string option_value)
            # whereas question mentions do change (they're the question_name, which depends on position)
            calculation = "if({} = 'option_1', 'value', 'other')",
            references = [referenced_question]
        )
    )
    expectation = Survey(
        title = 'Survey',
        xmlns = XMLNS,
        version = 1,
        languages = LANGUAGES,
        contents = [referenced_question, calculation_with_references]
    )
    assert actual == expectation, f"xml mismatch\nactual:\n{actual}\nvs.\nexpectation:\n{expectation}"


def test_group():
    xml = ET.parse(f'{EXPECTATIONS_DIR}/group.xml').getroot()
    actual = build_survey_from_xform(xml, xmlns = XMLNS, version = 1)
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
    expectation = Survey(
        title = 'Survey',
        xmlns = XMLNS,
        version = 1,
        languages = LANGUAGES,
        contents = [group]
    )
    assert actual == expectation, f"xml mismatch\nactual:\n{actual}\nvs.\nexpectation:\n{expectation}"


def test_repeat_group():
    xml = ET.parse(f'{EXPECTATIONS_DIR}/repeat_group.xml').getroot()
    actual = build_survey_from_xform(xml, xmlns = XMLNS, version = 1)
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
    expectation = Survey(
        title = 'Survey',
        xmlns = XMLNS,
        version = 1,
        languages = LANGUAGES,
        contents = [integer_question, group]
    )
    assert actual == expectation, f"xml mismatch\nactual:\n{actual}\nvs.\nexpectation:\n{expectation}"


def test_question_with_translation():
    xml = ET.parse(f'{EXPECTATIONS_DIR}/question_with_translation.xml').getroot()
    actual = build_survey_from_xform(
        xml,
        xmlns = XMLNS, 
        version = 1
    )
    question = Question(
        name = 'text',
        type = QuestionType.text,
        label = {
            Language.english: 'text',
            Language.artificial: 'text',
            Language.portuguese: 'translation'
        },
    )
    expectation = Survey(
        title = 'Survey',
        xmlns = XMLNS,
        version = 1,
        languages = {Language.english, Language.artificial, Language.portuguese},
        contents = [question]
    )
    assert actual == expectation, f"xml mismatch\nactual:\n{actual}\nvs.\nexpectation:\n{expectation}"