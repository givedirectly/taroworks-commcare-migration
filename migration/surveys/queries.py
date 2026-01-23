from simple_salesforce import format_soql


def query_tw_job(salesforce, job_name):
    query = salesforce.query_all(
        format_soql(
            '''
            SELECT 
                gfsurveys__Form__r.gfsurveys__Survey__r.Name,
                gfsurveys__Form__r.gfsurveys__Version__c,
                gfsurveys__JobTemplate__r.gfsurveys__Hierarchy__c,
                gfsurveys__Mapping__c
            FROM 
                gfsurveys__TaskTemplate__c
            WHERE 
                gfsurveys__JobTemplate__r.Name = {job_name}
            ''',
            job_name = job_name
        )
    )
    return query['records'][0]

def query_tw_form(salesforce, form_name, form_version):
    query_results = salesforce.query_all(
        format_soql(
            """
            SELECT
                Id,
                Name, 
                Section_Question__c,
                gfsurveys__Type__c,
                gfsurveys__RepeatSourceValue__c,
                gfsurveys__Caption__c,
                gfsurveys__Hint__c,
                gfsurveys__Required__c,
                gfsurveys__Hidden__c,
                gfsurveys__DynamicOperationType__c,
                gfsurveys__DynamicOperation__c,
                gfsurveys__ResponseValidation__c,
                gfsurveys__SkipLogicBehavior__c,
                gfsurveys__SkipLogicOperator__c,
                (
                    SELECT
                        Id,
                        Name,
                        gfsurveys__Caption__c
                    FROM
                        gfsurveys__Options__r
                    ORDER BY
                        gfsurveys__Position__c
                ),
                (
                    SELECT
                        gfsurveys__Condition__c,
                        gfsurveys__Negate__c,
                        gfsurveys__SkipValue__c,
                        gfsurveys__SourceQuestion__c,
                        gfsurveys__Value__c
                    FROM
                        gfsurveys__SkipConditions__r
                ),
                (
                    SELECT
                        Object_mapping__c,
                        gfsurveys__FieldApiName__c
                    FROM
                        gfsurveys__QuestionMappings__r
                )
            FROM
                gfsurveys__Question__c
            WHERE
                gfsurveys__Survey__r.Name = {form_name} AND
                gfsurveys__SurveyVersion__r.gfsurveys__Version__c = {form_version}
            ORDER BY
                Section_Question__c
            """,
            form_name = form_name,
            form_version = form_version
        )
    )
    return query_results['records']