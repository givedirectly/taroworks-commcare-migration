import pytest
import xml.etree.ElementTree as ET

from migration.xforms import Language
from migration.xforms.classes import (
    Calculation,
    Group,
    Option,
    Question,
    QuestionType,
    ShowLogic,
    Survey,
    Validation
)

from migration.xforms import build_survey_from_xform

EXPECTATIONS_DIR = 'migration/xforms/tests/expectations/'
LANGUAGES = {Language.en}
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
            Language.en: question_type
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
            Language.en: 'option 1',
        }
    )
    option_2 = Option(
        name = 'option_2',
        label = {
            Language.en: 'option 2',
        }
    )
    question = Question(
        name = question_type,
        type = question_type,
        label = {
            Language.en: question_type.replace('_', ' '),
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
            Language.en: 'text',
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
            Language.en: 'text',
        },
        hint = {
            Language.en: 'hint message',
        },
        help = {
            Language.en: 'help message',
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
            Language.en: 'text',
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
            Language.en: 'text',
        },
        validation = Validation(
            message = {
                Language.en: 'Your answer must start with "test".',
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
            Language.en: 'text',
        }
    )
    question_with_reference = Question(
        name = 'label_with_reference',
        type = QuestionType.label,
        label = {
            Language.en: 'text was: {}',
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
            Language.en: 'option 1',
        }
    )
    option_2 = Option(
        name = 'option_2',
        label = {
            Language.en: 'option 2',
        }
    )
    referenced_question = Question(
        name = 'single_select',
        type = QuestionType.single_select,
        label = {
            Language.en: 'single select',
        },
        options = [option_1, option_2]
    )
    question_with_show_logic = Question(
        name = 'text',
        type = QuestionType.text,
        label = {
            Language.en: 'text',
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
            Language.en: 'option 1',
        }
    )
    option_2 = Option(
        name = 'option_2',
        label = {
            Language.en: 'option 2',
        }
    )
    referenced_question = Question(
        name = 'single_select',
        type = QuestionType.single_select,
        label = {
            Language.en: 'single select',
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
            Language.en: 'text',
        },
    )
    group = Group(
        name = 'group',
        label = {
            Language.en: 'group',
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
            Language.en: 'integer',
        }
    )
    question_in_group = Question(
        name = 'text',
        type = QuestionType.text,
        label = {
            Language.en: 'text',
        },
    )
    group = Group(
        name = 'repeat_group',
        label = {
            Language.en: 'repeat group',
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
            Language.en: 'text',
            Language.por: 'texto'
        },
    )
    expectation = Survey(
        title = 'Survey',
        xmlns = XMLNS,
        version = 1,
        languages = {Language.en, Language.por},
        contents = [question]
    )
    assert actual == expectation, f"xml mismatch\nactual:\n{actual}\nvs.\nexpectation:\n{expectation}"