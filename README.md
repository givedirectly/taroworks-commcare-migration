# TW -> CC Migration

The code in this repository aims to make it easy to migrate surveys from Taroworks to Commcare. Specifically, given the name of a Taroworks job, the code can read the specifications of your Taroworks job and will generate an `.xml` file containing the xform for your new Commcare survey that file can be uploaded to a Commcare Application.

In the sections below, I explain how to run this code and the suggested process to follow in order to migrate your Taroworks surveys into Commcare.

If you are interested in more detail about the components of the code, there are READMEs in `migration/migration/` and in `migration/xforms/` you can consult.


## How do I run this?


### Pre-requisites


#### Salesforce Connected App

To run this, you will need to generate a [Salesforce Connected App](https://help.salesforce.com/s/articleView?id=xcloud.connected_app_client_credentials_setup.htm&type=5) so that you can access your Salesforce data via API. You can follow the instructions in the link above to set this up. Make sure your Connected App is connected to a user/profile that has Read permissions on all the Salesforce objects and fields holding Taroworks metadata (these objects are prefixed with `gfsurveys__`).

Once you have set up a Connected App, you will need to generate a `.env` file that contains the credentials for that Connected App. It should be a text file called `.env` (nothing before the dot), it should be located inside the root of this directory (i.e. inside `migration/`) and it should contain only these three lines:
```
SALESFORCE_USERNAME = "your_salesforce_username"
SALESFORCE_PRIVATEKEY_FILE = "path/to/your/private/key/file"
SALESFORCE_CONSUMER_KEY = "your_consumer_key"
```


#### Python environment

You will need Python 3 and the following packages:
- `esprima-python`
- `pytest` 
- `python-dotenv`
- `simple-salesforce`

If you use conda, you can use the following `.yaml` file to create a new conda environment with these packages:
```yaml
name: migration
channels:
  - defaults
dependencies:
  - python=3.12
  - conda-forge::esprima-python
  - pytest
  - python-dotenv
  - pip
  - pip:
    - simple-salesforce # insall via pip (not conda) to get latest version
```


### Running the code

You can run this from the command-line of your terminal like:

```
> cd path/to/folder/containing/migration/
> python migration/main.py --tw_job "Your TW Job Name" \
    --survey_language "en" \
    --directory "path/to/save/outputs"
```

Note that the `--survey-language` argument should match one of the language **codes** from `migration/xforms/languages.py`. So it should be "en" instead of "english", for example.

This will generate two files:
1. A `.xml` file containing the xform for your new Commcare survey
    - This can be uploaded to a Commcare app and will present you with a complete Commcare survey
2. A `.txt` file containing a list of case properties expected by the survey
    - These will correspond to the Salesforce data fields that were being pulled into the TW Form by the drill down in the TW job


### Upload the migrated survey into Commcare

1. **Set up your Commcare application**

    a. Create an application in Commcare
    
    b. Configure it to use the same language you specified when you ran `main.py`

2. **Set up your Commcare cases**

    You only need to do this if your Taroworks job filled in certain Form questions with data from the drill down. If this was not the case, skip step 2. See the section **Assumptions on database management** below for more information on why this is used.
    
    a. Create a case type in the Commcare data dictionary (Data > Data Dictionary)

    b. Create case properties should match the pulled-down fields printed in `case_properties.txt`

3. **Upload your survey**

    a. Add a Survey / Form to your Application
    
    - If your Taroworks Job filled in certain Form questions with data from its drill down, add a new Case List to your application (tied to the case type you just created) and add a Followup Form to that Case List. 
    - Otherwise, you may choose to add a Survey or a Registration Form.

    b. Upload `survey.xml` by click the gear next to your survey/form and selecting Actions > Xform Upload

    c. Create a second Survey / Form and copy the contents of your newly uploaded survey into this new Survey/Form
    
    - It is unfortunate this is needed but it is required for the backend (it ensures your Survey / Form will have an auto-generated and unique xml namespace)

    d. Delete the old Survey / Form so you have only one copy (the one you made in step c)

4. **Fix formulas in your new survey**

    a. Manually translate formulas (calculations and validations) for questions with particularly complicated formulas
    
    - These will be clearly highlighted in red since they have an invalid formula that block deployment. Your form may not have any of these

    - You can see the formula you need to translate in the question's comment

    - Generative AI chatbots (like ChatGPT) are typically pretty good at translating javascript formulas into xpath formulas. Do try them out!

    b. Once translated, delete the “untranslated calculation” from the question's comment

5. **Fix repeat group**

    For each repeat group in your survey, follow these steps
    
    i. Create a new calculated question positioned as the first question of your repeat group
    
    ii. Add the following calculation and replace `{num_repetitions}` with a reference to your repeat group's repeat condition: 
        
    `if((position(..) + 1) > {num_repetitions}, true(), '')`
        
    iii. Move all other groups and questions in the repeat group into a new group, placed right after the new calculated question

    iv. Set the display condition of the group created in step (iii) as `boolean({new_calculated_question})`, replacing `{new_calculated_question}` with a reference to the  question created in step (i)

6. **Deploy**
    
    a. Attempt to start the survey in the formbuilder. Some more errors may pop up at this point. If they do, fix them.

    b. Deploy a new version of your application


### Common errors

The errors we have run into while using this code have usually been caused by misconfigured Taroworks forms. For example: in Taroworks, if a question's show logic references a previous question but that previous question is deleted, it seems the show logic continues to exist in the metadata and this script will error because it cannot find the now-deleted question referenced in the show logic. 

In these situations, you will need to debug the error and fix the Taroworks form before re-running the script.


## Appendix: How does this code work?

This section doesn't describe in detail the entire workings of the code here but instead digs in on a few important areas, namely:
* how form data is stored in the taroworks data model
* how the code attempts to translate formulas
* how the code handles non-hidden calculated questions
* what the code assumes about database integrations


### Taroworks Data

Taroworks stores metadata on its jobs and forms in custom Salesforce objects named like `gfsurveys__{...}__c`. The main ones are:
1. `gfsurveys__Task__c`
    - represents a taroworks job, which is a construct that contains one or more forms and that defines how other Salesforce data may be referenced by those forms
2. `gfsurveys__Survey__c`
    - represents a taroworks form 
    - is connected to (though not a direct child of) `Task`
3. `gfsurveys__Question__c`: 
    - represents individual form questions 
    - is a child of `Survey`
    - contains data like question API name, label, help text, calculation/validation javascript, etc.
4. `gfsurveys__Option__c`
    - represents answer options for multiple-choice questions
    - is a child of `Question`
5. `gfsurveys__SkipCondition`
    - represents show/hide logic for questions
    - is a child of `Question`
6. `gfsurveys__QuestionMapping__c`
    - represents field mappings for questions
    - is a child of `Question`

The queries in `queries.py` pull all relevant data from taroworks jobs and forms. As an example, for the simple survey mentioned in `xml_forms/README.md`, this data might look like this (simplified):

<img src="images/demo_taroworks_data.png"/>

With this data, we can re-define the taroworks survey as a `Survey` containing `Group`s and `Question`s from `xml_forms/utils.py` and use that to save the survey as an XML file.

Most of the question metadata can be directly 'translated' to the commcare format (e.g. type, label, etc.). The main nuances are translating formulas (calculations, validations and show logic) and migrating non-hidden calculated questions (possible in TW but not in CC).


### Translating formulas

Formulas in Taroworks can be almost arbitrary javascript snippets, whereas in Commcare formulas are defined using much more restrictive xpath functions. `surveys/formulas.py` uses `esprima` to parse the javascript into 'nodes' and defines translations for a subset of available nodes. It would be very hard to define universal translations for all nodes but since our taroworks calculations **mostly** follow a few simple formats, we can define translations for a few nodes and that will work for most formulas. 

For the rest, we leave the formulas untranslated but ensure that (1) the uploaded XML file will noisily fail in CC but (2) be easily fixable. We do this by: (1) setting the formula to something that will fail (i.e. `#form/fake_formula`) and adding the untranslated formula to the question comment so it easily accessible.

For questions with calculations that do not follow those common formats, we would like to leave the formulas untranslated but ensure that (1) the uploaded XML file will noisily fail in CC but (2) be easily fixable. I do this by:
1. Add a comment containing the untranslated calculation
2. Add a 'broken' calculation that will noisily crash the form, forcing TPMs to manually translate the calculation before they can deploy the migrated survey

**This is the riskiest part of the migration process.** Some formulas may be incorrectly translated and there is a risk of them silently failing. In most cases, it is likely that you will easily catch this while testing the form.

Some formulas I know will be translated incorrectly are:
- Formulas that contain strings with escaped quotation marks, like: `"here is a string with a \" hidden within it"`
  - This should be very rare - I expect this will be uncommon
  - The translated formula will noisily fail once the XML is uploaded to CC (and be easy to fix there)
- Formulas that reference themselves
  - The translated formula will noisily fail once the XML is uploaded to CC (and be easy to fix there)


### Translating non-hidden calculated questions

Taroworks allows users to add calculations to questions that are not hidden, which Commcare does not. The way I get around this is by adding two CC questions for every non-hidden calculated TW question:
1. A hidden calculated question that performs the calculation
2. A 'label' question that displays the result


### Assumptions on database management

Taroworks is natively integrated to Salesforce and uses that as its database. So any information collected by the form is stored in Salesforce objects/fields (via Field Mappings) and any information that is needed as an input to the form is provided by Salesforce objects/fields too.

This has to be adapted to the environment available in Commcare, both in terms of (1) how data is ingested into the form and (2) where form submission data is stored. 

#### Where form submission data is stored

This code makes no assumptions about how you will store form submission data. It only keeps a record of where the Taroworks forms used to store data. Every question in the TW form that was mapped to a SF field will have that field's name recorded in the question's comment in CC.

#### How data is ingested into the form

It is assumed that the data being ingested into TW forms will be added to Commcare in the form of Cases. These should match 1:1 the Salesforce records that could be selected in TW job drilldowns:
* Salesforce objects -> Commcare case types
* Salesforce fields -> Commcare case properties
* Salesforce records -> Commcare cases

The code does not set up these cases but assumes you have done it. The migrated surveys will by uploaded into Commcare as Forms (not Surveys) so that they can read data from cases, similar to how TW Forms receive SF data from a TW Job.