import json
import os
import uuid
import xml.etree.ElementTree as ET
from defusedxml.ElementTree import fromstring as safe_fromstring

from django.conf import settings

DATA_DIR = os.path.join(settings.MEDIA_ROOT, 'data')
os.makedirs(DATA_DIR, exist_ok=True)

ALLOWED_EXTS = ('.json', '.xml')
ALLOWED_DIFFICULTY = ('easy', 'medium', 'hard')


def generate_safe_name(original_name: str, prefix: str = 'file') -> str:
    """Игнорируем имя от пользователя, оставляем только расширение и uuid."""
    _, ext = os.path.splitext(original_name or '')
    ext = ext.lower()
    if ext not in ALLOWED_EXTS:
        ext = '.dat'
    return f"{prefix}_{uuid.uuid4().hex}{ext}"


def recipe_to_dict(recipe) -> dict:
    return {
        'name': recipe.name,
        'ingredients': recipe.ingredients,
        'cooking_time': recipe.cooking_time,
        'difficulty': recipe.difficulty,
        'description': recipe.description or '',
    }


def _dict_to_xml_element(data: dict) -> ET.Element:
    root = ET.Element('recipe')
    for key, value in data.items():
        child = ET.SubElement(root, key)
        child.text = '' if value is None else str(value)
    return root


def save_recipe_to_file(recipe, fmt: str) -> str:
    if fmt not in ('json', 'xml'):
        raise ValueError('Неподдерживаемый формат')

    data = recipe_to_dict(recipe)
    filename = f"recipe_{uuid.uuid4().hex}.{fmt}"
    path = os.path.join(DATA_DIR, filename)

    if fmt == 'json':
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    else:
        root = _dict_to_xml_element(data)
        tree = ET.ElementTree(root)
        try:
            ET.indent(tree, space='  ')
        except AttributeError:
            pass
        tree.write(path, encoding='utf-8', xml_declaration=True)

    return filename


def _validate_data_dict(data: dict) -> dict:
    if not isinstance(data, dict):
        raise ValueError('Ожидается объект (dict).')

    required = ('name', 'ingredients', 'cooking_time', 'difficulty')
    for field in required:
        if field not in data or data[field] in (None, ''):
            raise ValueError(f'Отсутствует обязательное поле: {field}')

    try:
        ct = int(data['cooking_time'])
    except (TypeError, ValueError):
        raise ValueError('cooking_time должно быть целым числом.')

    if ct <= 0 or ct > 1440:
        raise ValueError('cooking_time должно быть в диапазоне 1..1440.')

    if data['difficulty'] not in ALLOWED_DIFFICULTY:
        raise ValueError(f"difficulty должно быть одним из: {ALLOWED_DIFFICULTY}")

    return {
        'name': str(data['name']).strip(),
        'ingredients': str(data['ingredients']).strip(),
        'cooking_time': ct,
        'difficulty': data['difficulty'],
        'description': str(data.get('description', '') or '').strip(),
    }


def validate_json_content(content: str) -> list:
    try:
        data = json.loads(content)
    except json.JSONDecodeError as e:
        raise ValueError(f'Некорректный JSON: {e}')

    if isinstance(data, dict):
        return [_validate_data_dict(data)]
    if isinstance(data, list):
        if not data:
            raise ValueError('JSON-массив пуст.')
        return [_validate_data_dict(item) for item in data]
    raise ValueError('JSON должен быть объектом или массивом объектов.')


def _xml_node_to_dict(node):
    result = {}
    for child in node:
        result[child.tag] = (child.text or '').strip()
    return result


def validate_xml_content(content: str) -> list:
    try:
        root = safe_fromstring(content)
    except Exception as e:
        raise ValueError(f'Ошибка парсинга XML: {e}')

    recipes = []
    if root.tag == 'recipe':
        recipes.append(_xml_node_to_dict(root))
    elif root.tag == 'recipes':
        for child in root:
            if child.tag != 'recipe':
                raise ValueError(f'Неожиданный тег внутри <recipes>: <{child.tag}>')
            recipes.append(_xml_node_to_dict(child))
    else:
        raise ValueError('Корневой элемент должен быть <recipe> или <recipes>.')

    if not recipes:
        raise ValueError('Файл не содержит рецептов.')

    return [_validate_data_dict(r) for r in recipes]


def read_data_file(filename: str) -> dict:
    safe = os.path.basename(filename)
    path = os.path.join(DATA_DIR, safe)
    if not os.path.isfile(path):
        raise FileNotFoundError('Файл не найден')

    ext = os.path.splitext(safe)[1].lower()
    if ext not in ALLOWED_EXTS:
        raise ValueError('Недопустимое расширение файла')

    with open(path, 'r', encoding='utf-8') as f:
        raw = f.read()

    if ext == '.json':
        recipes = validate_json_content(raw)
    else:
        recipes = validate_xml_content(raw)

    return {'filename': safe, 'ext': ext, 'raw': raw, 'recipes': recipes}


def list_data_files() -> list:
    result = []
    if not os.path.isdir(DATA_DIR):
        return result
    for name in sorted(os.listdir(DATA_DIR)):
        ext = os.path.splitext(name)[1].lower()
        if ext in ALLOWED_EXTS:
            full = os.path.join(DATA_DIR, name)
            result.append({'name': name, 'size': os.path.getsize(full)})
    return result