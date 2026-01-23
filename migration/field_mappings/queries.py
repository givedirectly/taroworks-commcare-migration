from simple_salesforce import format_soql


def query_form_mappings(salesforce, form_name, form_version):
    query = salesforce.query_all(
        format_soql(
            """
            SELECT
                Id,
                gfsurveys__ObjectApiName__c,
                gfsurveys__Repeat__c,
                gfsurveys__IsReference__c,
                gfsurveys__MatchingField__c
            FROM
                gfsurveys__SurveyMapping__c
            WHERE
                gfsurveys__Survey__r.Name = {form_name} AND
                gfsurveys__SurveyVersion__r.gfsurveys__Version__c = {form_version}
            """,
            form_name = form_name,
            form_version = form_version
        )
    )
    return query['records']


def query_object_relationships(salesforce, form_name, form_version):
    query = salesforce.query_all(
        format_soql(
            """
            SELECT
                gfsurveys__ChildSurveyMapping__r.gfsurveys__ObjectApiName__c,
                gfsurveys__ParentSurveyMapping__r.gfsurveys__ObjectApiName__c,
                gfsurveys__FieldApiName__c
            FROM
                gfsurveys__ObjectRelationshipMapping__c
            WHERE
                gfsurveys__ParentSurveyMapping__r.gfsurveys__Survey__r.Name = {form_name} AND
                gfsurveys__ParentSurveyMapping__r.gfsurveys__SurveyVersion__r.gfsurveys__Version__c = {form_version}
            """,
            form_name = form_name,
            form_version = form_version
        )
    )
    return query['records']


def query_question_mappings(salesforce, form_name, form_version):
    query = salesforce.query_all(
        format_soql(
            """
            SELECT
                gfsurveys__Question__c,
                gfsurveys__FieldApiName__c,
                Object_mapping__c
            FROM
                gfsurveys__QuestionMapping__c
            WHERE
                gfsurveys__Question__r.gfsurveys__Survey__r.Name = {form_name} AND
                gfsurveys__Question__r.gfsurveys__SurveyVersion__r.gfsurveys__Version__c = {form_version}
            """,
            form_name = form_name,
            form_version = form_version
        )
    )
    return query['records']


def get_field_metadata(salesforce, sf_objects):
    external_id_fields, gps_fields = [], []
    for sf_object in sf_objects:
        fields = getattr(salesforce, sf_object).describe()['fields']
        for field in fields:
            if field['externalId'] or field['nameField']:
                external_id_fields.append(f"{sf_object}.{field['name']}")
            if field['type'] == 'location':
                gps_fields.append(f"{sf_object}.{field['name']}")
    return external_id_fields, gps_fields