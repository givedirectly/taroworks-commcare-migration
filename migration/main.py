import json, os, pickle, re
from dotenv import load_dotenv
from simple_salesforce import Salesforce

from gddata import get_picklist_translations 

from commcare.field_mappings.generate_mappings import get_mapping_file_text
from commcare.xforms.classes import Language

from commcare.migration.surveys import (
    query_tw_job,
    query_tw_form, 
    get_pulldown_mappings,
    migrate_survey
)
from commcare.migration.field_mappings import get_mappings


MASTER_DIRNAME = '/Users/gavarela/Google Drive/Meu Drive/GD Downloads/reusable_library/migration'

TW_JOBS = {
    '2.0 Bangladesh Google AA Follow Up [Recipient]': Language.english,
    '4.0 DRC PoN FLUP [Recipient]': Language.french,
    '1.0 DRC BHA MobileAid FLUP [Recipient]': Language.french,
    '1.0 DRC BHA Research [Recipient]': Language.french,
    '2.0 Kenya Standard Remote Audit [County]': Language.english,
    '2.0 KE UBI Follow-up [Recipient]': Language.english,
    '2.0 KE UBI Retail Followup [Recipient]': Language.english,
    '1.1 Liberia REALISE MOG 3 Followup [Recipient]': Language.english,
    '1.0 Liberia STYLI Followup [Recipient]': Language.english,
    '1.5 Liberia STYL Registration [Recipient]': Language.english,
    '1.0 Malawi SAVE PON In-Person Registration [Traditional Authority]': Language.english,
    '2.0 Malawi PON FLUP [Recipient]': Language.english,
    '3.5 Malawi Cash4Health MSF II Registration [Recipient]': Language.english,
    '2.2 Malawi Cash4Health MSF II Follow-up [Recipient]': Language.english,
    '3.0 Malawi STEP Flex/FCDO At Home Revisit [District]': Language.english,
    '2.0 Malawi STEP Flex Large Transfer New ID Capture [Village]': Language.english,
    '1.4 Malawi STEP Flex SIM Registration [GVH]': Language.english,
    '1.0 Malawi STEP FLEX /FCDO M&E Midline [TA]': Language.english,
    '1.0 Malawi STEP FLEX /FCDO Monitoring and Evaluation [TA]': Language.english,
    '2.8 Malawi STEP Large Transfer Follow-up [TA]': Language.english,
    '4.0 Moz CSA FLUP [Recipient]': Language.portuguese,
    '1.6 Rwanda STEP Large Transfer FLUP[Recipient]': Language.kinyarwanda,
    '3.0 Rwanda STEP MnE [District]': Language.kinyarwanda,
    '5.1 Rwanda STEP Large Transfer At Home[District]': Language.kinyarwanda,
    '2.0 RW STEP Registration [District]': Language.kinyarwanda,
    '1.0 Uganda Kiryandongo New Arrivals Flup [Recipient]': Language.english,
    '1.3 Uganda Kiryandongo New Arrivals Phone Distribution [Recipient]': Language.english,
}


## Constants ---- (do not touch!)

sf_language_codes = {
    Language.english: None,
    Language.portuguese: 'pt_BR',
    Language.french: 'fr',
    Language.kinyarwanda: 'fi',
    Language.arabic: 'ar_YE'
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

    print(f'Migrating form {form_name}, version {int(form_version)}.')

    pulldown_mappings = get_pulldown_mappings(tw_job)
    
    try:
        with open(f'{dirname}/tw_form.json', 'r') as file:
            tw_form = json.load(file)
    except FileNotFoundError:
        tw_form = query_tw_form(salesforce, form_name, form_version)
        with open(f'{dirname}/tw_form.json', 'w') as file:
            json.dump(tw_form, file, indent = 4)

    sf_language_code = sf_language_codes[survey_language]
    if sf_language_code:

        print(f'Pulling all picklist translations from {sf_language_code}. This may take a few minutes.')

        mapped_objects = set()
        for question in tw_form:
            if question['gfsurveys__QuestionMappings__r']:
                for mapping in question['gfsurveys__QuestionMappings__r']['records']:
                    mapped_objects.add(mapping['Object_mapping__c'])

        try:
            with open(f'{dirname}/../picklist_translations__{sf_language_code}.json', 'r') as file:
                picklist_translations = json.load(file)
        except FileNotFoundError:
            picklist_translations = get_picklist_translations(
                salesforce,
                sobjects = mapped_objects,
                language_code = sf_language_code
            )
            with open(f'{dirname}/../picklist_translations__{sf_language_code}.json', 'w') as file:
                json.dump(picklist_translations, file, indent = 4)

    else:

        picklist_translations = None

    print('Converting TW form into xform.')

    migrated_survey, (groups, questions) = migrate_survey(
        tw_form, 
        pulldown_mappings, 
        tw_job_name, 
        cc_survey_xmlns, 
        survey_language, 
        picklist_translations
    )

    with open(f'{dirname}/survey_class.pkl', 'wb') as file:
        pickle.dump(migrated_survey, file)

    with open(f'{dirname}/migrated_survey.xml', 'w') as file:
        file.write(migrated_survey.as_xml())

    case_properties = [field.replace('.', '__') for field in pulldown_mappings.values()]
    with open(f'{dirname}/case_properties.txt', 'w') as file:
        file.write('\n'.join(case_properties))
    
    # Migrate mappings
    print('Creating a mapping python file.')

    mappings = get_mappings(
        salesforce, 
        form_name, 
        form_version,
        groups = groups, 
        questions = questions
    )

    mapping_file_text = get_mapping_file_text(mappings, cc_survey_xmlns)

    with open(f'{dirname}/migrated_mappings.py', 'w') as file:
        file.write(mapping_file_text)

    print('All done')

    return case_properties


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

        case_properties = main(
            salesforce, 
            job_name, 
            language,
            dirname = dirname
        )