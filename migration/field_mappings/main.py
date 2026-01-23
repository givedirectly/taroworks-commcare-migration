from commcare.field_mappings.field_mapping_types import (
    Action,
    Mapping
)
from .queries import (
    query_form_mappings,
    query_object_relationships,
    query_question_mappings,
    get_field_metadata
)


## Constants ----

MAPPINGS_TO_SKIP = [
    # these fields are populated by the exporter based on submission metadata
    # so don't need to be explicitly mapped
    "Survey_Attempt__c.Start_Time__c",
    "Survey_Attempt__c.End_Time__c",
    "Survey_Attempt__c.Survey_Duration__c",
    "Survey_Attempt__c.DeviceId__c"
]


## Build mappings ----

def get_mappings(salesforce, form_name, form_version, *, groups, questions):

    # Get SF data
    form_mappings = query_form_mappings(salesforce, form_name, form_version)
    object_relationships = query_object_relationships(salesforce, form_name, form_version)
    question_mappings = query_question_mappings(salesforce, form_name, form_version)

    sf_objects = set(m['gfsurveys__ObjectApiName__c'] for m in form_mappings)
    external_id_fields, gps_fields = get_field_metadata(salesforce, sf_objects)
    
    # Build mappings
    mappings = {}

    for form_mapping in form_mappings:
        
        object_name = form_mapping['gfsurveys__ObjectApiName__c']
        mapping_key = object_name.lower().rstrip('__c')

        mapping = Mapping(
            id = mapping_key,
            object_name = object_name,
            action = (
                Action.read if form_mapping['gfsurveys__IsReference__c'] else # never 'read_or_skip' in taroworks, as far as i know
                Action.create_or_update if form_mapping['gfsurveys__MatchingField__c'] else # never 'update' in taroworks, as far as i know
                Action.create
            )
        )
        
        if form_mapping['gfsurveys__Repeat__c']:
            mapping.repeat_on = groups[form_mapping['gfsurveys__Repeat__c']].path.replace('/', '.')

        if mapping.action != Action.create:
            mapping.lookup_field = _get_lookup_field(form_mapping, question_mappings, object_name, questions, mapping.repeat_on)
        
        mappings[mapping_key] = mapping


    for relationship_mapping in object_relationships:

        child_object_name = relationship_mapping['gfsurveys__ChildSurveyMapping__r']['gfsurveys__ObjectApiName__c']
        child_mapping_key = child_object_name.lower().rstrip('__c')
        child_mapping = mappings[child_mapping_key]

        parent_object_name = relationship_mapping['gfsurveys__ParentSurveyMapping__r']['gfsurveys__ObjectApiName__c']
        parent_mapping_key = parent_object_name.lower().rstrip('__c')
        parent_mapping = mappings[parent_mapping_key]

        if parent_mapping.action != Action.create and f'{parent_object_name}.{parent_mapping.lookup_field[0]}' in external_id_fields:
            relationship_field = relationship_mapping['gfsurveys__FieldApiName__c'].replace('__c', '__r').rstrip('Id')
        else:
            relationship_field = relationship_mapping['gfsurveys__FieldApiName__c']

        child_mapping.child_relationships[relationship_field] = parent_mapping_key

    for question_mapping in question_mappings:
        
        object_name = question_mapping['Object_mapping__c']
        field_name = f"{question_mapping['gfsurveys__FieldApiName__c']}"

        full_field_name = f"{object_name}.{field_name}"
        if full_field_name in MAPPINGS_TO_SKIP:
            continue

        mapping_key = object_name.lower().rstrip('__c')
        mapping = mappings[mapping_key]

        if mapping.action in (Action.read, Action.read_or_skip):
            continue

        if mapping.lookup_field and mapping.lookup_field[0] == field_name:
            continue

        question_path = questions[question_mapping['gfsurveys__Question__c']].path.replace('/', '.')

        if mapping.repeat_on:
            question_path = question_path.replace(mapping.repeat_on, f"{mapping.repeat_on}[*]")

        if full_field_name in gps_fields:
            mapping.fields[field_name.rstrip('__c') + '__Latitude__s'] = question_path + '.latitude'
            mapping.fields[field_name.rstrip('__c') + '__Longitude__s'] = question_path + '.longitude'
        else:
            mapping.fields[field_name] = question_path

    for mapping in mappings.values():
        mapping.fields = dict(sorted(mapping.fields.items()))

    return mappings


def _get_lookup_field(form_mapping, question_mappings, object_name, questions, repeat_on):
    lookup_question_id = next(
        m['gfsurveys__Question__c']
        for m in question_mappings
        if m['Object_mapping__c'] == object_name and
        m['gfsurveys__FieldApiName__c'] == form_mapping['gfsurveys__MatchingField__c']
    )
    lookup_question_path = questions[lookup_question_id].path.replace('/', '.')
    if repeat_on:
        lookup_question_path = lookup_question_path.replace(repeat_on, f"{repeat_on}[*]")
    return (
        form_mapping['gfsurveys__MatchingField__c'],
        lookup_question_path
    )