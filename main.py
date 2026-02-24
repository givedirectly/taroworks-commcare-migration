import argparse
import os
from dotenv import load_dotenv
from simple_salesforce import Salesforce

from migration.xforms import Language

from migration.surveys import (
    get_pulldown_mappings,
    migrate_survey
)
from migration.queries import (
    query_tw_form,
    query_tw_job
)


## Main ----

def main(
    salesforce: Salesforce,
    tw_job_name: str,
    survey_language: Language = Language.en,
    survey_xmlns: str = 'http://openrosa.org/formdesigner/TEST_XMLNS',
    dirname: str = '.'
) -> None:
    
    tw_job = query_tw_job(salesforce, tw_job_name)

    form_name = tw_job['gfsurveys__Form__r']['gfsurveys__Survey__r']['Name']
    form_version = tw_job['gfsurveys__Form__r']['gfsurveys__Version__c']

    pulldown_mappings = get_pulldown_mappings(tw_job)
    
    tw_form = query_tw_form(salesforce, form_name, form_version)

    migrated_survey = migrate_survey(
        tw_form,
        pulldown_mappings,
        tw_job_name,
        survey_xmlns,
        survey_language,
    )

    with open(f'{dirname}/migrated_survey.xml', 'w') as file:
        file.write(migrated_survey.as_xml())

    case_properties = [field.replace('.', '__') for field in pulldown_mappings.values()]
    with open(f'{dirname}/case_properties.txt', 'w') as file:
        file.write('\n'.join(case_properties))


if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description = (
            "Migrates a taroworks survey to commcare (queries TW survey data and "
            "outputs a commcare survey xform and a list of case properties needed)."
        )
    )

    parser.add_argument("--tw_job")
    parser.add_argument("--survey_language", default="en")
    parser.add_argument("--directory", default=".")
    
    args = parser.parse_args()

    load_dotenv()

    salesforce = Salesforce(
        username = os.getenv('SALESFORCE_USERNAME') + ".dev",
        privatekey_file = os.getenv('SALESFORCE_PRIVATEKEY_FILE'),
        consumer_key = os.getenv('SALESFORCE_CONSUMER_KEY'),
        domain = "test"
    )

    if args.directory != ".":
        os.makedirs(args.directory)

    main(
        salesforce,
        args.tw_job,
        args.survey_language,
        dirname = args.directory
    )