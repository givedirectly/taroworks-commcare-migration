import os, re
from dotenv import load_dotenv
from simple_salesforce import Salesforce

from migration.xforms.classes import Language

from migration.migration import (
    query_tw_job,
    query_tw_form, 
    get_pulldown_mappings,
    migrate_survey
)


MASTER_DIRNAME = 'dirname'

TW_JOBS = {
    'tw_job_name': Language.language_code,
    ...: ...,
}


## Main ----

def main(
    salesforce, 
    tw_job_name, 
    survey_language = Language.english, 
    cc_survey_xmlns = 'http://openrosa.org/formdesigner/TEST_XMLNS',
    dirname = '.'
):
    
    # Migrate survey
    tw_job = query_tw_job(salesforce, tw_job_name)

    form_name = tw_job['gfsurveys__Form__r']['gfsurveys__Survey__r']['Name']
    form_version = tw_job['gfsurveys__Form__r']['gfsurveys__Version__c']

    pulldown_mappings = get_pulldown_mappings(tw_job)
    
    tw_form = query_tw_form(salesforce, form_name, form_version)

    migrated_survey = migrate_survey(
        tw_form, 
        pulldown_mappings, 
        tw_job_name, 
        cc_survey_xmlns, 
        survey_language,
    )

    with open(f'{dirname}/migrated_survey.xml', 'w') as file:
        file.write(migrated_survey.as_xml())

    case_properties = [field.replace('.', '__') for field in pulldown_mappings.values()]
    with open(f'{dirname}/case_properties.txt', 'w') as file:
        file.write('\n'.join(case_properties))


if __name__ == "__main__":

    load_dotenv()

    for job_name, language in TW_JOBS.items():

        print(f'\n\n----\n\nMigrating job {job_name} ({language})')

        dirname = MASTER_DIRNAME + '/' + re.sub(r'\s+', ' ', re.sub(r'\W', ' ', job_name))

        try:
            os.mkdir(dirname)
        except FileExistsError:
            pass

        salesforce = Salesforce(
            username = os.getenv('SALESFORCE_USERNAME'),
            privatekey_file = os.getenv('SALESFORCE_PRIVATEKEY_FILE'),
            consumer_key = os.getenv('SALESFORCE_CONSUMER_KEY')
        ) # reload sf for each job in case connection times out

        main(
            salesforce, 
            job_name, 
            language,
            dirname = dirname
        )