import json

from urllib.parse import unquote

from migration.xforms.classes import *
from migration.migration.formulas import (
    translate_calculation,
    translate_validation,
    CalcIsValError
)


## Constants (do not touch) ----

FAKE_FORMULA = '#form/fake_formula'

TW_QUESTION_TYPES = {
    'date-datetime': QuestionType.datetime,
    'picture': QuestionType.photo,
    'text-long': QuestionType.text,
    'static-content': QuestionType.label,
    'signature': QuestionType.signature,
    'text-short': QuestionType.text,
    'checkbox': QuestionType.multi_select,
    'gps-location': QuestionType.gps,
    'number-integer': QuestionType.integer,
    'radio': QuestionType.single_select,
    'number-decimal': QuestionType.decimal,
    'date-date': QuestionType.date,
    'barcode': QuestionType.barcode,
}


## Migration function ----

def migrate_survey(tw_form, pulldown_mappings, survey_name, survey_xmlns, survey_language, picklist_translations):

    groups_by_index = {}
    groups_by_id, questions_by_id, options_by_id = {}, {}, {}

    records_in_order = sorted(tw_form, key = lambda r: _clean_section_question(r['Section_Question__c']))

    for record in records_in_order:

        if record['gfsurveys__Type__c'] in ('section', 'repeat'):
            
            # Make section
            group = Group(
                name = record['Name'],
                label = {language: record['gfsurveys__Caption__c'] for language in (survey_language, Language.artificial)},
                contents = [],
                repeat = questions_by_id[record['gfsurveys__RepeatSourceValue__c']] if record['gfsurveys__RepeatSourceValue__c'] else None,
                show_logic = get_question_show_logic(record, 'group', questions_by_id, options_by_id, survey_language)
            )

            groups_by_id[record['Id']] = group

            group_index = _clean_section_question(record['Section_Question__c'])[0]
            groups_by_index[group_index] = group
        
        else:
            
            # Make options
            options = get_question_options(record, picklist_translations, survey_language)
            options_by_id.update(options)
            
            # Make question
            question_type = get_question_type(record, pulldown_mappings, questions_by_id)

            question = Question(
                name = record['Name'],
                type = question_type,
                label = {
                    language: record['gfsurveys__Caption__c'] 
                    for language in (survey_language, Language.artificial)
                },
                comment = get_question_comment(record, questions_by_id, question_type),
                hint = {
                    language: record['gfsurveys__Hint__c'] or '' 
                    for language in (survey_language, Language.artificial)
                }, # not needed for calculated questions but is discarded once xform is uploaded
                required = record['gfsurveys__Required__c'] if question_type != QuestionType.calculation else None,
                show_logic = get_question_show_logic(record, question_type, questions_by_id, options_by_id, survey_language),
                validation = get_question_validation(record, questions_by_id, question_type, survey_language),
                options = list(options.values()) if question_type != QuestionType.calculation else [],
                calculation = get_question_calculation(record, pulldown_mappings, questions_by_id)
            )

            questions_by_id[record['Id']] = question

            group_index = _clean_section_question(record['Section_Question__c'])[0]
            groups_by_index[group_index].contents.append(question)

            if question_type == QuestionType.calculation and not record['gfsurveys__Hidden__c']:
                
                label_question = Question(
                    name = f"label_{record['Name']}",
                    type = QuestionType.label,
                    label = {
                        language: f"{record['gfsurveys__Caption__c']}\n\n{{}}"
                        for language in (survey_language, Language.artificial)
                    },
                    references = [question],
                    hint = {
                        language: record['gfsurveys__Hint__c'] or '' 
                        for language in (survey_language, Language.artificial)
                    },
                    required = None if question_type == QuestionType.calculation else record['gfsurveys__Required__c'],
                    show_logic = get_question_show_logic(record, question_type, questions_by_id, options_by_id, survey_language),
                )

                groups_by_index[group_index].contents.append(label_question)
    
    # Set up survey
    root_group = Group(
        name = 'survey',
        label = {language: 'Survey' for language in (survey_language, Language.artificial)},
        contents = list(groups_by_id.values()),
    )

    survey = Survey(
        title = survey_name,
        xmlns = survey_xmlns,
        contents = [root_group],
        languages = [survey_language, Language.artificial],
        version = None
    )

    survey.__post_init__() # unclear why i need to force-run this but it fixes issues with show logic

    return survey, (groups_by_id, questions_by_id)


## Helpers ----

def _clean_section_question(section_question):
    section, question = tuple(int(n) for n in section_question.split('-'))
    if section == 0:
        section, question = question, section
    return section, question


## Question metadata ----

def get_question_type(question, pulldown_mappings, questions_by_id):

    if question['Name'] in pulldown_mappings:
        return QuestionType.calculation
    
    if question['gfsurveys__DynamicOperationType__c'] == 'Calculation':
        try:
            translate_calculation(question['gfsurveys__DynamicOperation__c'], question['Name'], list(questions_by_id.values()))
        except CalcIsValError:
            pass
        except NotImplementedError:
            return QuestionType.calculation
        else:
            return QuestionType.calculation
    
    try:
        return TW_QUESTION_TYPES[question['gfsurveys__Type__c']]
    except:
        raise ValueError(f"Missing CC type conversion for TW type: {question['gfsurveys__Type__c']}")


def get_question_comment(question, questions_by_id, question_type):

    comment = ''

    # Mappings
    if question['gfsurveys__QuestionMappings__r']:
        mappings = _get_mappings(question)
        comment += '\n'.join(mappings)

    # Untranslated formula
    if question['gfsurveys__DynamicOperation__c']:

        translation_function = translate_calculation if question['gfsurveys__DynamicOperationType__c'] == 'Calculation' else translate_validation

        try:
            translation_function(question['gfsurveys__DynamicOperation__c'], question['Name'], list(questions_by_id.values()))
        except NotImplementedError:
            comment += f"\n\nUntranslated {question['gfsurveys__DynamicOperationType__c']}:\n{question['gfsurveys__DynamicOperation__c']}"
        except CalcIsValError:
            try:
                translate_validation(question['gfsurveys__DynamicOperation__c'], question['Name'], list(questions_by_id.values()))
            except NotImplementedError:
                comment += f"\n\nUntranslated {question['gfsurveys__DynamicOperationType__c']}:\n{question['gfsurveys__DynamicOperation__c']}"
    
    return comment


def _get_mappings(question) -> list[str]:

    if not question['gfsurveys__QuestionMappings__r']:
        return []
    
    mappings = []

    for mapping in question['gfsurveys__QuestionMappings__r']['records']:
        mappings.append(f"{mapping['Object_mapping__c']}.{mapping['gfsurveys__FieldApiName__c']}")

    return mappings


def get_question_options(question, picklist_translations, survey_language) -> dict[Option]:

    if not question['gfsurveys__Options__r']:
        return {}
    
    if question['gfsurveys__QuestionMappings__r']:
        mapping = _get_mappings(question)[0]
    else:
        mapping = None

    options = {}
    for option in question['gfsurveys__Options__r']['records']:
        caption = unquote(option['gfsurveys__Caption__c'])
        options[option['Id']] = Option(
            name = _get_option_api_name(caption),
            label = {
                survey_language: caption,
                Language.artificial: _get_art_translation(caption, mapping, survey_language, picklist_translations)
            }
        )

    return options

def _get_option_api_name(option_caption):
    api_name = re.sub(r'\W+', '_', option_caption)
    api_name = api_name.lower()
    api_name = api_name[:min(len(api_name), 75)]
    return api_name

def _get_art_translation(translated_value, mapped_field, survey_language, picklist_translations):

    if survey_language == Language.english or not mapped_field:
        return translated_value
    
    if mapped_field in picklist_translations:
        for english_value, translation in picklist_translations[mapped_field].items():
            if translation == translated_value:
                return english_value
            
    return translated_value


def get_question_show_logic(question, question_type, all_questions, all_options, survey_language):
    
    if question['gfsurveys__Hidden__c']:
        if question_type == QuestionType.calculation:
            return
        return ShowLogic('false()')
    
    if not question['gfsurveys__SkipConditions__r']:
        return
    
    conditions = []
    references = []
    for skip_condition in question['gfsurveys__SkipConditions__r']['records']:
        
        try:
            referenced_question = all_questions[skip_condition['gfsurveys__SourceQuestion__c']]
        
        except:
            raise ValueError(f"Unable to find question with ID {skip_condition['gfsurveys__SourceQuestion__c']} referenced in show logic of question with ID {question['Id']}")
        
        if skip_condition['gfsurveys__Condition__c'] == 'Answered' or skip_condition['gfsurveys__SkipValue__c'] is None:
            condition_to_append = 'boolean({})'
            references_to_extend = [referenced_question]
        
        else:
            tw_operator = skip_condition['gfsurveys__Condition__c']
            operator = '=' if tw_operator == 'Is' else '>' if tw_operator == 'GreaterThan' else '<' # alternative is 'LesserThan'
            
            if re.match(r'a0J\w{15}', skip_condition['gfsurveys__SkipValue__c']):
                # SkipValue is an option ID
                referenced_option_id = skip_condition['gfsurveys__SkipValue__c']
                try:
                    referenced_option = all_options[referenced_option_id]
                except KeyError:
                    if question['gfsurveys__SkipLogicOperator__c'] == 'All':
                        raise ValueError(f"Unable to find option with ID {skip_condition['gfsurveys__SkipValue__c']} referenced in show logic of question with ID {question['Id']}")
                    else:
                        continue
                if referenced_question.type == QuestionType.calculation:
                    condition_to_append = f"{{}} {operator} '{referenced_option.label[survey_language]}'"
                    references_to_extend = [referenced_question]
                else:
                    condition_to_append = f'{{}} {operator} {{}}'
                    references_to_extend = [referenced_question, referenced_option]
        
            else:
                value = skip_condition['gfsurveys__SkipValue__c'] or ''
                try:
                    float(value)
                except ValueError:
                    condition_to_append = f"{{}} {operator} '{value}'"
                else:
                    condition_to_append = f'{{}} {operator} {value}'
                references_to_extend = [referenced_question]
        
        if skip_condition['gfsurveys__Negate__c']:
            condition_to_append = f'not({condition_to_append})'
        
        conditions.append(condition_to_append)
        references.extend(references_to_extend)
    
    operator = 'or' if question['gfsurveys__SkipLogicOperator__c'] == 'Any' else 'and' # alternative is 'All'
    logic = f' {operator} '.join(conditions)
    
    if question['gfsurveys__SkipLogicBehavior__c'] == 'Hide': # alternative is 'Show'
        logic = f'not({logic})'
    
    return ShowLogic(
        logic = logic,
        references = references
    )


def get_question_calculation(question, pulldown_mappings, questions_by_id):

    if question['Name'] in pulldown_mappings:
        case_property = pulldown_mappings[question['Name']].replace('.', '__')
        return Calculation(f"#case/{case_property}")
    
    if question['gfsurveys__DynamicOperationType__c'] != 'Calculation':
        return
    
    try:
        translated_calculation = translate_calculation(question['gfsurveys__DynamicOperation__c'], question['Name'], list(questions_by_id.values()))
    except NotImplementedError:
        return Calculation(FAKE_FORMULA)
    except CalcIsValError:
        return
    
    return Calculation(translated_calculation)


def get_question_validation(question, questions_by_id, question_type, survey_language):

    # Translate response validation (regex)
    if question['gfsurveys__ResponseValidation__c']:
        regex = re.sub(r'(^/|/$)', '', question['gfsurveys__ResponseValidation__c'])
        regex = regex.replace('{', '{{').replace('}', '}}') # to 'escape' the braces since the Validation class will try to format the validation string
        return Validation(
            message = {language: 'Your answer has an invalid format.' for language in (survey_language, Language.artificial)},
            validation = f"regex(., '{regex}')"
        )
    
    # Check for validation dynamic operation (as val or as misplaced calc)
    has_validation_operation = question['gfsurveys__DynamicOperationType__c'] == 'Validation'
    if question['gfsurveys__DynamicOperationType__c'] == 'Calculation':
        try:
            translate_calculation(question['gfsurveys__DynamicOperation__c'], question['Name'], list(questions_by_id.values()))
        except CalcIsValError:
            has_validation_operation = True
        except NotImplementedError:
            pass

    # Translate dynamic operation if applicable
    if not has_validation_operation:
        return
    try:
        translated_validation, validation_message = translate_validation(question['gfsurveys__DynamicOperation__c'], question['Name'], list(questions_by_id.values()))
    except NotImplementedError:
        return Validation(
            message = {language: '...' for language in (survey_language, Language.artificial)},
            validation = FAKE_FORMULA
        )
    else:
        return Validation(
            message = {language: validation_message for language in (survey_language, Language.artificial)},
            validation = translated_validation
        )


## Pulldowns ----

def get_pulldown_mappings(tw_job):
    
    hierarchy = json.loads(tw_job['gfsurveys__JobTemplate__r']['gfsurveys__Hierarchy__c'])
    mappings = json.loads(tw_job['gfsurveys__Mapping__c'])

    flat_hierarchy = _flatten_list(hierarchy)
    
    pulldown_mappings = {}
    for mapping in mappings:
        object_name = next(h['objectName'] for h in flat_hierarchy if h['objectId'] == mapping['objectId'])
        pulldown_mappings[mapping['question']] = f"{object_name}.{mapping['field']}"

    return pulldown_mappings

def _flatten_list(x):
    if not isinstance(x, list):
        return [x]
    ret = []
    for el in x:
        ret += _flatten_list(el)
    return ret