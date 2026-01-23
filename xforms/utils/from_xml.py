import re
from xml.etree.ElementTree import Element

from commcare.xforms.classes import *


## Constants (do not touch!) ----

NAMESPACES = {
    "h": "http://www.w3.org/1999/xhtml",
    "default": "http://www.w3.org/2002/xforms",
}


## Main ----

def build_survey_from_xform(
    xform_root: Element,
    *,
    title: str = 'Survey',
    xmlns: str = 'http://openrosa.org/formdesigner/TEST_XMLNS',
    version: int|None = 1,
) -> Survey:

    # Extract XML elements
    instance_element = _get_instance_element(xform_root)
    data_element = _get_data_element(instance_element)
    data_subelements = _get_data_subelements(data_element)
    bind_elements = _get_bind_elements(xform_root)
    default_values = _get_default_values(xform_root)
    display_texts = _get_display_texts(xform_root)
    body_element = _get_body_element(xform_root)
    body_subelements = _get_body_subelements(body_element)

    # Create survey
    survey_contents = _get_survey_contents(
        data_subelements, 
        bind_elements,
        default_values,
        display_texts,
        body_subelements,
    )

    return Survey(
        title = title,
        xmlns = xmlns,
        contents = survey_contents,
        languages = get_languages_from_xform(xform_root),
        version = version,
    )


## Extract survey metadata ----

def get_languages_from_xform(xform_root: Element) -> set[str]:
    """
    Returns all the languages for which this survey defines display text translations.
    Gets this from the "translation" elements.
    """
    translation_elements = xform_root.findall("h:head/default:model/default:itext/default:translation", NAMESPACES)
    languages = {translation_element.attrib["lang"] for translation_element in translation_elements}
    if not languages:
        raise ValueError("Unable to extract languages from the provided xform.")
    return languages


## Extract XML elements ----

def _get_instance_element(xform_root: Element) -> Element:
    return xform_root.find("h:head/default:model/default:instance", NAMESPACES)


def _get_data_element(instance_element: Element) -> Element:
    instance_namespaces = _get_namespaces(instance_element)
    if len(instance_namespaces) != 1:
        raise ValueError(f"Expected exactly 1 namespace in <instance> (the xmlns) but found {len(instance_namespaces)} instead: {instance_namespaces}")
    return instance_element.find("ns0:data", instance_namespaces)

def _get_namespaces(element: Element) -> dict[str, str]:
    """
    Elements rendered by the xml library have their tags formatted like:
     - "tag" (if it has no namespace) or 
     - "{namespace}tag" (if it has a namespace).
    This function recursively iterates through all child elements of a given element and extracts namespaces from their tags.
    """
    namespaces = set()
    for i, subelement in enumerate(element.iter()):
        if i == 0:
            continue # first sub-element is the root element
        namespace_match = re.match(r"\{(.+)\}.+$", subelement.tag) # xml lib stores element tags as '{namespace}tag' and we can only extract via regex
        if namespace_match:
            namespaces.add(namespace_match.group(1))
    return {f"ns{i}": namespace for i, namespace in enumerate(namespaces)}


def _get_data_subelements(data_element: Element, data_subelements: dict[str, Element] | None = None, name: str = "") -> dict[str, Element]:
    """
    The "data" element in the xform contains child elements that mirror the form's structure. 
    For example, a root group is a child of "data" and any questions inside that group are a child element of that group's element.
    These child elements define a group or question's position within the survey and some metadata like comments or whether the group is a repeat group.
    
    This function recursively iterates over all child elements of the "data" element and returns a dict mapping each group or question's
    name to its corresponding child element, like:
    {
        "question_name": Element(...),
        ...
    }
    """

    data_subelements = data_subelements or {} # important that {} is not the default arg in func definition
    
    element_tag = re.search(r"^\{.*?\}(.*)$", data_element.tag).group(1)
    name = f"{name}/{element_tag}"
    
    for child in data_element:
        
        child_element_tag = re.search(r"^\{.*?\}(.*)$", child.tag).group(1)
        question_name = f"{name}/{child_element_tag}"
        
        data_subelements[question_name] = child

        if len(child) > 0:
            _get_data_subelements(child, data_subelements, name)
    
    return data_subelements


def _get_bind_elements(xform_root: Element) -> dict[str, Element]:
    """
    Each question has a corresponding "bind" element in the xform that define some metadata, such as 
    calculations, validations, display logic, whether the question is required, etc.

    This function iterates over all "bind" elements in the xform and returns a dict mapping each question's
    name to its corresponding "bind" element, like:
    {
        "question_name": Element(...),
        ...
    }
    """
    bind_elements = {}
    for element in xform_root.findall("h:head/default:model/default:bind", NAMESPACES):
        name = element.attrib["nodeset"]
        bind_elements[name] = element
    return bind_elements


def _get_default_values(xform_root: Element) -> dict[str, str]:
    """
    Each question has a corresponding "bind" element in the xform that define some metadata, such as 
    calculations, validations, display logic, whether the question is required, etc.

    This function iterates over all "bind" elements in the xform and returns a dict mapping each question's
    name to its corresponding "bind" element, like:
    {
        "question_name": Element(...),
        ...
    }
    """
    default_values = {}
    for setvalue_element in xform_root.findall("h:head/default:model/default:setvalue", NAMESPACES):
        name = setvalue_element.attrib["ref"]
        default_values[name] = setvalue_element.attrib["value"]
    return default_values


def _get_display_texts(xform_root: Element) -> dict[str, dict[str, str]]:
    """
    Iterates through all "translation" elements and their "text" subelements to extract every question's display text in each language used by the form.
    If a display text contains a reference to a previous question (i.e. renders the output of that question as a string), this function formats that as
    "<REFERENCE>question_name</REFERENCE>" within the display text's string.
    Output looks like:
    {
        "question_name": {
            "lang1": "Display text in language 1",
            ...
        },
        ...
    }
    """

    itext_elements = xform_root.find("h:head/default:model/default:itext", NAMESPACES)

    display_texts = {}
    for language_element in itext_elements.findall("default:translation", NAMESPACES):

        language = language_element.attrib["lang"]

        for text_element in language_element.findall("default:text", NAMESPACES):

            name = "/data/" + text_element.attrib["id"]
            value_element = text_element.find("default:value", NAMESPACES)
            display_text = value_element.text

            for child in value_element:
                display_text += f"<REFERENCE>{child.attrib['value']}</REFERENCE>"
                if child.tail:
                    display_text += child.tail

            display_texts.setdefault(name, {})[language] = display_text

    return display_texts


def _get_body_element(xform_root: Element) -> Element:
    return xform_root.find("h:body", NAMESPACES)


def _get_body_subelements(body_element: Element, body_subelements: dict[str, Element] | None = None) -> dict[str, Element]:
    """
    The "body" element in the xform contains child elements that mirror the form's structure. 
    For example, a root group is a child of "body" and any questions inside that group are a child element of that group's element.
    These child elements define some metadata like question type, display text, answer options, group repeat conditions, etc.
    
    This function recursively iterates over all child elements of the "body" element and returns a dict mapping each group or question's
    name to its corresponding child element, like:
    {
        "question_name": Element(...),
        ...
    }
    """

    body_subelements = body_subelements or {} # important that {} is not the default arg in func definition

    for child in body_element:

        if child.tag == "{http://www.w3.org/2002/xforms}label":
            continue
        
        if child.tag == "{http://www.w3.org/2002/xforms}group":
            
            repeat = child.find("default:repeat", NAMESPACES) 

            if repeat is not None:
                name = repeat.attrib["nodeset"]
                body_subelements[name] = child
                _get_body_subelements(repeat, body_subelements)
            else:
                name = child.attrib["ref"]
                body_subelements[name] = child
                _get_body_subelements(child, body_subelements)
        
        else:

            name = child.attrib["ref"]
            body_subelements[name] = child
            
    return body_subelements


## Extract group and question data from XML elements ----

def _get_survey_contents(
    data_subelements: dict[str, Element], 
    bind_elements: dict[str, Element],
    default_values: dict[str, str],
    display_texts: dict[str, dict[str, str]],
    body_subelements: dict[str, Element],
) -> list[Question | Group]:
    """
    In the xform, a group or question's metadata is scattered in multiple elements. 
    This function receives all relevant xform elements in searchable structures (dicts with question names as keys) 
    and goes through them all (via helper functions) to collect the metadata pertaining to each question/group.
    It builds a Question or Group for each one and, in doing so, places Questions inside their parent group's Group.contents list.
    Returns a list of Groups / Questions corresponding to the items in the survey's root location 
    (those not in the root location are contained in their parent's Group.contents).
    Output looks like:
    [
        Group(
            ...,
            contents = [
                Question(...),
                Question(...)
            ]
        ),
        ...
    ]
    """
    
    items = {}
    survey_contents = []

    for full_name, data_subelement in data_subelements.items():

        item_name = full_name.split('/')[-1]
        parent_name = re.sub(r"/[\w-]+$", "", full_name)

        bind_element = bind_elements[full_name]
        body_subelement = body_subelements.get(full_name) # will be missing for calculated questions
        
        item_type = _get_question_type(bind_element, body_subelement)

        if item_type == Group:

            if f"{full_name}-label" not in display_texts:
                raise ValueError(f"Missing label for {full_name}")

            item = Group(
                name = item_name,
                label = display_texts[f"{full_name}-label"],
                repeat = _get_repeat_question(body_subelement, items, item_name),
                show_logic = _format_show_logic(bind_element, items),
                comment = data_subelement.attrib.get("{http://commcarehq.org/xforms/vellum}comment"),
                contents = []
            )

        else:

            if item_type == QuestionType.calculation:
                label, references = None, []
            else:
                if f"{full_name}-label" not in display_texts:
                    raise ValueError(f"Missing label for {full_name}")
                label, references = _extract_label_references(display_texts[f"{full_name}-label"], items)

            item = Question(
                name = item_name,
                type = item_type,
                label = label,
                references = references,
                comment = data_subelement.attrib.get("{http://commcarehq.org/xforms/vellum}comment"),
                help = display_texts.get(f"{full_name}-help"),
                hint = display_texts.get(f"{full_name}-hint"),
                required = bind_element.attrib.get("required") == "true()",
                show_logic = _format_show_logic(bind_element, items),
                validation = _format_validation(bind_element, display_texts, full_name, items),
                options = _get_options(body_subelement, display_texts, full_name),
                calculation = _format_calculation(bind_element, items),
                default = default_values.get(full_name),
            )

        items[full_name] = item

        if parent_name == "/data":
            survey_contents.append(item)
        else:
            items[parent_name].contents.append(item)
    
    return survey_contents


## Group / question data helpers ----

# Question type

def _get_question_type(bind_element: Element, body_subelement: Element) -> str:
    """
    Information about a question's type is scattered in multiple elements of the xform.
    This function collects details from the appropriate elements and determines a question's type.
    """

    if "type" in bind_element.attrib and bind_element.attrib["type"] != "binary":
        string_type = re.sub(r"^xsd:", "", bind_element.attrib["type"])
        if string_type == 'string':
            return QuestionType.text
        if string_type == 'int':
            return QuestionType.integer
        if string_type == 'double':
            return QuestionType.decimal 
        if string_type == 'date':
            return QuestionType.date 
        if string_type == 'dateTime':
            return QuestionType.datetime
        if string_type == 'geopoint':
            return QuestionType.gps 
        if string_type == 'barcode':
            return QuestionType.barcode
        raise ValueError(f"Unrecognised question type {string_type}")

    if body_subelement is None:
        return QuestionType.calculation

    if body_subelement.tag == "{http://www.w3.org/2002/xforms}group":
        return Group
        
    if body_subelement.tag == "{http://www.w3.org/2002/xforms}upload":
        return QuestionType.signature if body_subelement.attrib.get("appearance") == "signature" else QuestionType.photo
    
    if body_subelement.tag == "{http://www.w3.org/2002/xforms}trigger":
        return QuestionType.label
    
    elif body_subelement.tag == "{http://www.w3.org/2002/xforms}select1":
        return QuestionType.single_select
    
    elif body_subelement.tag == "{http://www.w3.org/2002/xforms}select":
        return QuestionType.multi_select
    
    raise RuntimeError("Unable to determine question type")


# Repeat condition

def _get_repeat_question(body_subelement: Element, other_items: dict[str, Question|Group], group_name: str) -> str:
    """
    In Commcare, groups can repeat on an arbitrary xpath formula but our Group class only allows repeating on a Question's value.
    This function checks that the repeat condition is a direct reference to a previous question and returns that question's name, erroring otherwise.
    """
    
    repeat = body_subelement.find("default:repeat", NAMESPACES)
    if repeat is None or "{http://commcarehq.org/xforms/vellum}jr__count" not in repeat.attrib:
        return
    
    repeat_condition = re.sub(r"^#form", "/data", repeat.attrib["{http://commcarehq.org/xforms/vellum}jr__count"]) # repeat condition refers to questions with the "#form" prefix rather than the "/data" prefix
    
    if not re.match(r'^/data(/[\w-]+)+', repeat_condition):
        raise ValueError(f"For now, can only parse repeat conditions that are direct references to a Question. For group {group_name}, condition is:\n{repeat_condition}")
    
    if repeat_condition not in other_items:
        raise ValueError("Repeat condition references a question that doesn't exist or that is ordered after the group.")
    
    return other_items[repeat_condition]


# Labels with references

def _extract_label_references(display_texts: dict[str, dict[str, str]], other_items: list[Question|Group]) -> tuple[str, list[Question]]:
    """
    Checks display texts returned by _get_display_texts for references to other questions, rendered as "<REFERENCE>question_name</REFERENCE>".
    Returns a string and a list of references ready to be inputted into the Question class, i.e.
     - string has {} where references should go
     - list contains the Question instance that is referenced (in order)
    """
    
    new_label = {
        language: re.sub(r"<REFERENCE>.+?</REFERENCE>", "{}", label) # _get_display_texts renders references in labels as <REFERENCE>question_name</REFERENCE>
        for language, label in display_texts.items()
    }

    first_label = list(display_texts.values())[0]
    references = [
        other_items[reference]
        for reference in re.findall(r"<REFERENCE>(.+?)</REFERENCE>", first_label)
    ]
    
    return new_label, references


# Formulas

def _format_show_logic(bind_element: Element, other_items: list[Question|Group]) -> ShowLogic:
    if "relevant" not in bind_element.attrib:
        return
    logic, references = _extract_formula_references(bind_element.attrib["relevant"], other_items)
    return ShowLogic(logic = logic, references = references)

def _format_calculation(bind_element: Element, other_items: list[Question|Group]) -> Calculation:
    if "calculate" not in bind_element.attrib:
        return
    calculation, references = _extract_formula_references(bind_element.attrib["calculate"], other_items)
    return Calculation(calculation = calculation, references = references)

def _format_validation(
    bind_element: Element, 
    display_texts: dict[str, dict[str, str]], 
    full_name: str, 
    other_items: list[Question|Group]
) -> Validation:
    if "constraint" not in bind_element.attrib:
        return
    if f"{full_name}-constraintMsg" not in display_texts:
        raise ValueError(f"Missing validation message for {full_name}")
    validation, references = _extract_formula_references(bind_element.attrib["constraint"], other_items)
    return Validation(
        message = display_texts[f"{full_name}-constraintMsg"], 
        validation = validation, 
        references = references
    )

def _extract_formula_references(formula: str, other_items: list[Question|Group]) -> tuple[str, list[Question]]:
    """
    Checks formulas for references to other questions, rendered as "/data/path/to/question". 
    These are extracted since they depend on questions' positions within the survey. 
    Returns a string formula and a list of references ready to be inputted into the Calculation, Validation or ShowLogic classes, i.e.
     - string has {} where references should go
     - list contains the Question instance that is referenced (in order)
    Conscious limitation: 
        Does NOT extract mentions of option values into references. This is okay since option mentions are constant (the option_value string), 
        unlike question mentions which change depending on the question's position within the survey (the question_name)
    """
    formula_with_clean_property_references = _clean_property_references(formula)
    new_formula = re.sub(r"/data/[\w/\-]+", "{}", formula_with_clean_property_references)
    references = [
        other_items[reference] 
        for reference in re.findall(r"/data/[\w/\-]+", formula_with_clean_property_references)
    ]
    return new_formula, references

def _clean_property_references(formula: str) -> str:
    """
    Cleans the formula of strings that can be incorrectly interpreted as questions. 
    For now, these are references to case and user poroperties but we could include other kinds of properties in the future if needed.
    """
    # case property
    formula = formula.replace(
        "instance('casedb')/casedb/case[@case_id = instance('commcaresession')/session/data/case_id]/",
        "#case/"
    )
    # user properties
    formula = formula.replace(
        "instance('commcaresession')/session/user/data/",
        "#user/"
    )
    return formula


# Options

def _get_options(body_subelement: Element, display_texts: dict[str, dict[str, str]], full_name: str) -> list[Option]:
    """
    Builds Option instances based off of the information on options that is scattered across the xform.
    """

    if body_subelement is None:
        return []

    options = []
    for option_element in body_subelement.findall("default:item", NAMESPACES):

        option_name = option_element.find("default:value", NAMESPACES).text
        option_display_text_name = re.sub('[&"\'<>]', '_', option_name)
        if f"{full_name}-{option_display_text_name}-label" not in display_texts:
            raise ValueError(f'No label found for option {option_display_text_name} of question {full_name}')
        
        options.append(
            Option(
                name = option_name,
                label = display_texts[f"{full_name}-{option_display_text_name}-label"]
            )
        )
    
    return options
