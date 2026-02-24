# TW -> CC Migration

The code in this repository aims to make it easy to migrate surveys from Taroworks to Commcare. Specifically, given the name of a Taroworks job, the code can read the specifications of your Taroworks job and will generate an `.xml` file containing the xform for your new Commcare survey that file can be uploaded to a Commcare Application.

In the sections below, I explain how to run this code and the suggested process to follow in order to migrate your Taroworks surveys into Commcare.

If you are interested in more detail about the components of the code, there are READMEs in `migration/migration/` and in `migration/xforms/` you can consult.


## How do I run this?


### Pre-requisites


#### Salesforce Connected App

To run this, you will need to generate a [Salesforce Connected App](https://help.salesforce.com/s/articleView?id=xcloud.connected_app_client_credentials_setup.htm&type=5) so that you can access your Salesforce data via API. You can follow the instructions in the link to set this up.

Once you have set up a Connected App, you will need to generate a `.env` file that contains the credentials for that Connected App. It should be a text file called only `.env`, should be located inside the root of this directory (i.e. inside `migration/`) and should contain only these three lines:
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
name: commcare_migration
channels:
  - defaults
dependencies:
  - python=3.12
  - conda-forge::esprima-python
  - pytest
  - python-dotenv
  - pip
  - pip:
    - simple-salesforce # insall via pip to get latest version
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


## How do I generate a Commcare survey from this code?


### Background info

Explain decisions made regarding pulldowns and field mappings.

The outputs:

1. A `.xml` file containing the xform for your new Commcare survey
    - This can be uploaded to a Commcare app and will present you with a complete Commcare survey
2. A `.txt` file containing a list of case properties expected by the survey
    - These will correspond to the Salesforce data fields that were being pulled into the TW Form by the drill down in the TW job


The process:

- If you are pulling down data into your TW form, create a case type and use a followup form in a case list. Else, just use a survey or a registration form in a case list.
- Suggestions for what to do about your field mappings. 


### Steps

1. **Application setup**

    a. Create an application in Commcare
    
    b. Configure it to use the same language you specified when you ran `main.py`

2. **Case setup**

    a. You must do this if ...
    
    b. Create a case type in the Commcare data dictionary (Data > Data Dictionary)

    c. Create case properties should match the pulled-down fields printed in `case_properties.txt`

3. **Upload your survey**

    a. Add a new Case List to your application, tied to the case type you just created
    
    b. Add a Followup form to your case list if ..., otherwise add a Registration form

    c. Upload `survey.xml` by click the gear next to your form and selecting Actions > Xform Upload

    d. Copy the contents of your new survey, create a new Followup Form then paste the contents of the form into this new Form

    e. Delete the 

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


## How does this code work?

This section doesn't describe in detail the entire workings of the code here but instead digs in on a few important areas, namely:
* how form data is stored in the taroworks data model
* how the code attempts to translate formulas
* how the code handles non-hidden calculated questions


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

**This is the riskiest part of the migration process.** Some formulas may be incorrectly translated and there is a risk of them silently failing. In most cases, it is likely that we will easily catch this while testing the form.

Some formulas I know will be translated incorrectly are:
- Formulas that contain strings with escaped quotation marks, like: `"here is a string with a \" hidden within it"`
  - This should be very rare - I expect we won't find this
  - The translated formula will noisily fail once the XML is uploaded to CC (and be easy to fix there)
- Formulas that reference themselves
  - The translated formula will noisily fail once the XML is uploaded to CC (and be easy to fix there)


### Translating non-hidden calculated questions

Taroworks allows users to add calculations to questions that are not hidden, which Commcare does not. The way I get around this is by adding two CC questions for every non-hidden calculated TW question:
1. A hidden calculated question that performs the calculation
2. A 'label' question that displays the result