import re

from enum import StrEnum
from dataclasses import dataclass, field
from typing import Optional, Union

from commcare.xforms.helpers import element
import xml.etree.ElementTree as ET


class QuestionType(StrEnum):
    single_select = 'single_select'
    multi_select = 'multi_select' 
    text = 'text'
    integer = 'integer'
    decimal = 'decimal'
    date = 'date'
    datetime = 'datetime'
    photo = 'photo'
    signature = 'signature'
    label = 'label'
    calculation = 'calculation'
    gps = 'gps'
    barcode = 'barcode'

class Language(StrEnum):
    english = 'en'
    artificial = 'art'
    portuguese = 'por'
    arabic = 'ara'
    kinyarwanda = 'kin'
    french = 'fra'


@dataclass
class Group:
    
    name: str
    label: dict[Language, str]
    contents: list[Union["Group", "Question"]]
    repeat: Optional["Question"] = field(default = None)
    comment: str | None = field(default = None)
    show_logic: Optional["ShowLogic"] = field(default = None)

    def __post_init__(self):
        assert re.match(r'[\w-]{,75}', self.name), \
            "`name` must be 75 characters at most and only contain \w characters (numbers, letters, underscores) and hyphens"

    def propagate_paths(self, parent_path = ''):
        self.path = f'{parent_path}/{self.name}' if parent_path else self.name
        for content in self.contents:
            content.propagate_paths(parent_path = self.path)

    def as_instance_element(self):
        attributes = {}
        if self.repeat:
            attributes["jr:template"] = ""
        if self.comment:
            attributes["vellum:comment"] = self.comment
        contents = [content.as_instance_element() for content in self.contents]
        return element(self.name, attributes, contents = contents)
    
    def as_bind_element(self):
        attributes = {
            'vellum:nodeset': f'#form/{self.path}',
            'nodeset': f'/data/{self.path}'
        }
        if self.show_logic:
            attributes.update(self.show_logic.get_bind_attributes())
        return element('bind', attributes)
    
    def get_content_bind_elements(self):
        bind_elements = [self.as_bind_element()]
        for content in self.contents:
            bind_elements += content.get_content_bind_elements()
        return bind_elements
    
    def as_text_element(self, language):
        return element(
            'text',
            {
                'id': f'{self.path}-label'
            },
            contents = [
                element('value', text = self.label[language])
            ]
        )
    
    def get_content_text_elements(self, language):
        text_elements = [self.as_text_element(language)]
        for content in self.contents:
            text_elements += content.get_content_text_elements(language)
        return text_elements
    
    def as_body_element(self):
        name = 'group'
        element_attributes = {}
        if not self.repeat:
            element_attributes = {
                'vellum:ref': f"#form/{self.path}",
                'ref': f"/data/{self.path}"
            }
        element_contents = [
            element('label', {'ref': f"jr:itext('{self.path}-label')"})
        ]
        group_contents = [
            content.as_body_element() 
            for content in self.contents 
            if content.as_body_element() is not None # calculated questions return None as they have no body element
        ]
        if self.repeat:
            element_contents.append(
                element(
                    'repeat',
                    {
                        'vellum:jr__count': f"#form/{self.repeat.path}",
                        'jr:count': f"/data/{self.repeat.path}",
                        'jr:noAddRemove': "true()",
                        'vellum:nodeset': f"#form/{self.path}",
                        'nodeset': f"/data/{self.path}"
                    },
                    contents = group_contents
                )
            )
        else:
            element_contents.extend(group_contents)
        return element(
            name,
            element_attributes,
            contents = element_contents
        )


@dataclass
class Question:
    
    name: str
    type: QuestionType
    label: dict[Language, str] | None = field(default = None)
    references: list["Question"] = field(default_factory = lambda: [])
    comment: str | None = field(default = None)
    help: dict[Language, str] | None = field(default = None)
    hint: dict[Language, str] | None = field(default = None)
    required: bool | None = field(default = False)
    show_logic: Optional["ShowLogic"] = field(default = None)
    validation: Optional["Validation"] = field(default = None)
    options: list["Option"] = field(default_factory = lambda: [])
    calculation: Optional["Calculation"] = field(default = None)
    default: Optional["Calculation"] = field(default = None) # TODO: not yet used below 

    def __post_init__(self):
        assert re.match(r'[\w-]{,75}', self.name), \
            "`name` must be 75 characters at most and only contain \w characters (numbers, letters, underscores) and hyphens"
        if not self.label:
            assert self.type == QuestionType.calculation, \
                "All non-calculated questions need a label"
        if self.options:
            assert self.type in (QuestionType.single_select, QuestionType.multi_select), \
                "You cannot add options to a question that is not of a `select` type"
        if self.calculation:
            assert self.type == QuestionType.calculation, \
                "You cannot add a calculation to a question that is not of `calculation` type"
        if self.type == QuestionType.calculation:
            self.calculation = self.calculation or Calculation(calculation = "") # TODO: consider if this is best done somewhere else
            self.required = None

    def propagate_paths(self, parent_path = ''):
        self.path = f'{parent_path}/{self.name}' if parent_path else self.name
        for option in self.options:
            option.propagate_paths(parent_path = self.path)
        if self.validation:
            self.validation.propagate_paths(parent_path = self.path)

    def as_instance_element(self):
        attributes = {}
        if self.comment:
            attributes["vellum:comment"] = self.comment
        return element(self.name, attributes)
    
    def as_bind_element(self):
        attributes = {
            'vellum:nodeset': f'#form/{self.path}',
            'nodeset': f'/data/{self.path}',
        }
        type_attribute = self._get_type_attribute()
        if type_attribute:
            attributes['type'] = type_attribute
        if self.show_logic:
            attributes.update(self.show_logic.get_bind_attributes())
        if self.validation:
            attributes.update(self.validation.get_bind_attributes())
        if self.type == QuestionType.calculation:
            attributes.update(self.calculation.get_bind_attributes())
        if self.required:
            attributes['required'] = 'true()'
        return element(
            'bind',
            attributes
        )
    
    def _get_type_attribute(self):
        if self.type == QuestionType.text:
            return 'xsd:string'
        if self.type == QuestionType.integer:
            return 'xsd:int'
        if self.type == QuestionType.decimal:
            return 'xsd:double'
        if self.type == QuestionType.date:
            return 'xsd:date'
        if self.type == QuestionType.datetime:
            return 'xsd:dateTime'
        if self.type in (QuestionType.photo, QuestionType.signature):
            return 'binary'
        if self.type in (QuestionType.label, QuestionType.single_select, QuestionType.multi_select, QuestionType.calculation):
            return
        if self.type == QuestionType.gps:
            return 'geopoint'
        if self.type == QuestionType.barcode:
            return 'barcode'
        raise ValueError(f'type {self.type} does not have a defined bind attribute')

    def get_content_bind_elements(self):
        return [self.as_bind_element()]
    
    def as_text_element(self, text_type, language):
        value_subelements = []
        if text_type == 'label':
            if self.references:
                split_label = self.label[language].split('{}')
                value_text = split_label.pop(0)
                for reference in self.references:
                    value_subelements.append(
                        element(
                            'output',
                            {
                                'value': f'/data/{reference.path}',
                                'vellum:value': f'#form/{reference.path}'
                            },
                            tail = split_label.pop(0)
                        )
                    )
            else:
                value_text = self.label[language]
        elif text_type == 'hint':
            value_text = self.hint[language]
        elif text_type == 'help':
            value_text = self.help[language]
        else:
            raise ValueError('text_type must be label, hint or help')
        value_element = element(
            'value', 
            text = value_text,
            contents = value_subelements)
        return element(
            'text',
            {'id': f'{self.path}-{text_type}'},
            contents = [value_element]
        )
    
    def get_content_text_elements(self, language):
        text_elements = []
        if self.label:
            text_elements.append(self.as_text_element('label', language))
        if self.hint:
            text_elements.append(self.as_text_element('hint', language))
        if self.help:
            text_elements.append(self.as_text_element('help', language))
        for option in self.options:
            text_elements.append(option.as_text_element(language))
        if self.validation:
            text_elements.append(self.validation.as_text_element(language))
        return text_elements
    
    def as_body_element(self):
        """Note: weird order in which I add attributes is so it matches UI's xml exactly and tests pass."""
        if self.type == QuestionType.calculation:
            return
        name = self._get_body_element_name() # Changes based on question type
        attributes = {}
        if self.type in (QuestionType.photo, QuestionType.signature):
            attributes['mediatype'] = "image/*"
        if self.type == QuestionType.photo:
            attributes['jr:imageDimensionScaledMax'] = "1000px"
        attributes['vellum:ref'] = f"#form/{self.path}"
        attributes['ref'] = f"/data/{self.path}"
        if self.type == QuestionType.photo:
            attributes['appearance'] = "acquire"
        if self.type == QuestionType.signature:
            attributes['appearance'] = "signature"
        if self.type == QuestionType.label:
            attributes['appearance'] = "minimal"
        contents = [
            # Will always contain label. Will also contain options, etc. if applicable.
            element(
                'label',
                {'ref': f"jr:itext('{self.path}-label')"}
            )
        ]
        if self.hint:
            contents.append(
                element(
                    'hint',
                    {'ref': f"jr:itext('{self.path}-hint')"}
                )   
            )
        if self.help:
            contents.append(
                element(
                    'help',
                    {'ref': f"jr:itext('{self.path}-help')"}
                )   
            )
        if self.validation:
            contents.append(
                self.validation.as_body_element()
            )
        for option in self.options:
            contents.append(
                option.as_body_element()
            )
        return element(
            name,
            attributes,
            contents = contents
        )
    
    def _get_body_element_name(self):
        if self.type in (QuestionType.text, QuestionType.integer, QuestionType.decimal, QuestionType.date, QuestionType.datetime, QuestionType.gps, QuestionType.barcode):
            return 'input'
        if self.type in (QuestionType.photo, QuestionType.signature):
            return 'upload'
        if self.type == QuestionType.label:
            return 'trigger'
        if self.type == QuestionType.single_select:
            return 'select1'
        if self.type == QuestionType.multi_select:
            return 'select'
        raise ValueError(f'type {self.type} does not have a defined body element name')


@dataclass
class Option:

    name: str
    label: dict[Language, str]

    def __post_init__(self):
        assert re.match(r'[\w-]{,75}', self.name), \
            "`name` must be 75 characters at most and only contain \w characters (numbers, letters, underscores) and hyphens"

    def propagate_paths(self, parent_path):
        self.path = f'{parent_path}-{self.name}'

    def as_text_element(self, language):
        return element(
            'text',
            {'id': f'{self.path}-label'},
            contents = [element('value', text = self.label[language])]
        )
    
    def as_body_element(self):
        label_element = element(
            'label',
            {'ref': f"jr:itext('{self.path}-label')"}
        )
        value_element = element(
            'value',
            text = self.name
        )
        return element(
            'item',
            contents = [
                label_element, 
                value_element
            ]
        )


@dataclass
class Calculation:
    
    calculation: str
    references: list[Question | Option] = field(default_factory = lambda: [])

    def get_bind_attributes(self):
        if self.references:
            return {
                'vellum:calculate': _replace_references(self.calculation, self.references, vellum = True),
                'calculate': _replace_references(self.calculation, self.references, vellum = False),
            }
        return {'calculate': self.calculation}

def _replace_references(formula, references, vellum):
    assert len(re.findall(r"\{\}", formula)) == len(references), \
        "Number of references must match number of `{}`s in the formula"
    question_prefix = "#form" if vellum else "/data"
    for reference in references:
        formula = re.sub(
            r"\{\}", 
            f'{question_prefix}/{reference.path}' if isinstance(reference, Question) else f"'{reference.name}'", 
            formula, 
            count = 1
        )
    return formula


@dataclass
class ShowLogic:
    
    logic: str
    references: list[Question | Option] = field(default_factory = lambda: [])

    def get_bind_attributes(self):
        if self.references:
            return {
                'vellum:relevant': _replace_references(self.logic, self.references, vellum = True),
                'relevant': _replace_references(self.logic, self.references, vellum = False),
            }
        return {'relevant': self.logic}

@dataclass
class Validation:

    message: dict[Language, str]
    validation: str
    references: list[Question | Option] = field(default_factory = lambda: [])
    
    def propagate_paths(self, parent_path):
        self.path = f'{parent_path}-constraintMsg'
    
    def get_bind_attributes(self):
        if self.references:
            return {
                'vellum:constraint': _replace_references(self.validation, self.references, vellum = True),
                'constraint': _replace_references(self.validation, self.references, vellum = False),
                'jr:constraintMsg': f"jr:itext('{self.path}')"
            }
        return {
            'constraint': self.validation,
            'jr:constraintMsg': f"jr:itext('{self.path}')"
        }

    def as_text_element(self, language):
        return element(
            'text',
            {
                'id': f'{self.path}'
            },
            contents = [
                element('value', text = self.message[language])
            ]
        )
    
    def as_body_element(self):
        return element(
            'alert',
            {'ref': f"jr:itext('{self.path}')"}
        )


@dataclass
class Survey:

    title: str
    xmlns: str
    contents: list[Union["Group", "Question"]]
    languages: list[Language]
    version: int | None

    def __post_init__(self):
        for content in self.contents:
            content.propagate_paths()

    def as_xml(self):
        html_attributes = {
            'xmlns:h': "http://www.w3.org/1999/xhtml",
            'xmlns:orx': "http://openrosa.org/jr/xforms", 
            'xmlns': "http://www.w3.org/2002/xforms",
            'xmlns:xsd': "http://www.w3.org/2001/XMLSchema",
            'xmlns:jr': "http://openrosa.org/javarosa",
            'xmlns:vellum': "http://commcarehq.org/xforms/vellum"
        }
        html = element(
            'h:html',
            html_attributes,
            contents = [
                self._get_xml_head(),
                self._get_xml_body()
            ]
        )
        tree = ET.ElementTree(html)
        ET.indent(tree, '\t')
        xml_str = ET.tostring(tree.getroot(), encoding="utf-8", xml_declaration=True).decode("utf-8")
        return xml_str

    ## Head ----
    def _get_xml_head(self):
        contents = [
            element(
                'title', 
                text = self.title, 
                namespace = 'h'
            ),
            element(
                'model',
                contents = [
                    self._get_instance_element(),
                    *self._get_bind_elements(),
                    self._get_itext_element()
                ]
            )
        ]
        return element('head', contents = contents, namespace = 'h')

    def _get_instance_element(self):
        """Version and UI Version are being set the same for now."""
        data_element = element(
            'data',
            {
                'xmlns:jrm': "http://dev.commcarehq.org/jr/xforms",
                'xmlns': self.xmlns,
                'uiVersion': str(self.version) if self.version else '1',
                'version': str(self.version) if self.version else '1',
                'name': self.title
            },
            contents = [content.as_instance_element() for content in self.contents]
        )
        return element(
            'instance',
            contents = [data_element]
        )
    
    def _get_bind_elements(self):
        binds = []
        for content in self.contents:
            binds += content.get_content_bind_elements()
        return binds
    
    def _get_itext_element(self):
        translation_elements = []
        for i, language in enumerate(self.languages):
            translation_attributes = {
                'lang': language
            }
            if i == 0:
                translation_attributes['default'] = ''
            translation_contents = []
            for content in self.contents:
                translation_contents.extend(content.get_content_text_elements(language))
            translation_elements.append(
                element(
                    'translation',
                    translation_attributes,
                    contents = translation_contents
                )
            )
        return element(
            'itext',
            contents = translation_elements
        )
    
    ## Body ----
    def _get_xml_body(self):
        return element(
            'body', 
            contents = [
                content.as_body_element() 
                for content in self.contents 
                if content.as_body_element() is not None # calculated questions return None as they have no body element
            ],
            namespace = 'h'
        )