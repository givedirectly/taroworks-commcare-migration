# Translating formulas

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