# Migrating field mappings

Here are the relevant objects & fields storing Taroworks field mapping data:

1. `gfsurveys__SurveyMapping__c`
    - represents the mappings to a Salesforce object across all fields of a Taroworks form
    - fields describe:
      - what section to 'repeat on' (i.e. create/update multiple records of that object),
      - how to identify which record to read/update (i.e. what question's value should we look up in which field)
2. `gfsurveys__ObjectRelationshipMapping__c`
    - represents the relationship between two Salesforce objects mapped to in a Taroworks form
    - i.e. if we map to Contact and Account, a record will indicate that the Contact should be a child of Account
3. `gfsurveys__QuestionMapping__c`: 
    - represents a field mapping for an individual question

The data from these objects can be directly translated into a `Mapping` object (from the exporter). Once we define multiple `Mapping`s, we can easily write a python config file line-by-line that defines all those `Mappings`.