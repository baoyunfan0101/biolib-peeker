from bs4 import BeautifulSoup, Tag
from rubberneck import Item, Request, Response

ROOT_URL = 'https://www.biolib.cz/en/'
TAXON_URL = ROOT_URL + 'taxon/id{page_id}/'
ITEM_FORMAT = {
    'id': '',  # primary key
    'parent': '',
    'category': '',
    'rank': '',
    'scientific_name': '',
    'authority_year': '',
    'geological_range': '',
    'english_name': '',
}


def taxon_request(page_id: int) -> Request:
    return Request(
        TAXON_URL.format(page_id=page_id),
        meta={
            'page_id': page_id,
            'is_first_page': True,
            'cookiejar': 'biolib',
        },
    )


def _parse_children(taxa_soup):
    current_category = ''

    for child in taxa_soup.children:
        # skip children like '\n'
        if isinstance(child, Tag):

            if child.name == 'h2':
                current_category = child.text.split()[0].lower()
                # 'nomina' => 'nomina_dubia' or 'nomina_nuda'
                if current_category == 'nomina':
                    current_category += '_' + child.text.split()[1]
            elif child.name == 'div':
                child_class = child.get('class')
                if child_class is None or child_class[0] not in ['treediv', 'treeenddiv']:
                    continue

                div_item = ITEM_FORMAT.copy()

                div_item['category'] = current_category

                # extract rank
                first_content = str(child.contents[0]).split()
                if len(first_content) >= 1:
                    div_item['rank'] = first_content[0]

                # extract <a>
                a_tags = child.find_all('a')

                if len(a_tags) >= 1:
                    div_item['id'] = None if a_tags[0] is None else a_tags[0].get('href')[12:-1]
                    # disable strip in case like <em>Scientific synonym</em> var. <em>variata</em>
                    div_item['scientific_name'] = None if a_tags[0] is None else a_tags[0].get_text(strip=False)
                    if len(a_tags) >= 2 and current_category == 'fossil':
                        if a_tags[-1].get('href') == '#incertaesedis':
                            div_item['category'] += '_unplaced'
                        else:
                            div_item['category'] += '_included'

                # extract <small>
                small_tags = child.find_all('small')
                if len(small_tags) >= 2:
                    div_item['authority_year'] = small_tags[0].get_text(strip=True).replace('&amp;', '&')
                    div_item['geological_range'] = small_tags[1].get_text(strip=True).replace('&ndash;', '-')
                elif len(small_tags) == 1:
                    previous_tag = small_tags[0].find_previous_sibling()
                    if previous_tag is not None and previous_tag.name == 'br':
                        div_item['geological_range'] = small_tags[0].get_text(strip=True).replace('&ndash;', '-')
                    else:
                        div_item['authority_year'] = small_tags[0].get_text(strip=True).replace('&amp;', '&')

                # extract <strong>
                strong_tag = child.find('strong')
                div_item['english_name'] = None if strong_tag is None else strong_tag.get_text(strip=True)

                yield div_item


def _parse_synonyms(synonyms_soup):
    current_category = 'synonyms'

    p_tag = synonyms_soup.find('p')

    # create a new item
    synonym_item = ITEM_FORMAT.copy()
    synonym_item['category'] = current_category

    for child in p_tag.children:

        if isinstance(child, Tag):
            if child.name == 'br':
                if synonym_item['scientific_name'] != '' or synonym_item['authority_year'] != '':
                    yield synonym_item

                    # create a new item and reset the category
                    synonym_item = ITEM_FORMAT.copy()
                    current_category = 'synonyms'
                    synonym_item['category'] = current_category

            elif child.name == 'em':
                inner_text = child.get_text(strip=True)
                if not inner_text:
                    continue

                # if scientific_name is empty, set as scientific_name
                if synonym_item['scientific_name'] == '':
                    synonym_item['scientific_name'] = inner_text
                # if scientific_name is not empty, add to the end
                else:
                    synonym_item['scientific_name'] += ' ' + inner_text

            elif child.name == 'small':
                inner_text = child.get_text(strip=True)

                # get extra category in case like <small>{category}</small>
                if inner_text == '(nomen nudum)':
                    synonym_item['category'] = 'synonyms_nomen_nudum'
                elif inner_text == '(partim.)':
                    synonym_item['category'] = 'synonyms_partim.'
                elif inner_text == '(misspelling)':
                    synonym_item['category'] = 'synonyms_misspelling'
                elif inner_text == '(unjustified emendation)':
                    synonym_item['category'] = 'unjustified_emendation'
                elif inner_text == '(unjustified replacement name)':
                    synonym_item['category'] = 'unjustified_replacement_name'

                # case like <small>Authority, year</small>
                else:
                    synonym_item['authority_year'] = inner_text

        else:
            inner_text = child.strip()
            # if inner_text is None or empty
            if not inner_text:
                continue

            words = inner_text.split()

            # if it is the beginning or an incomplete line of included synonyms, case: id=128704
            if words[0] == 'incl.' or words[0] == ',':
                # if it is an incomplete line of included synonyms, append last synonym first
                if words[0] == ',':
                    yield synonym_item

                    # create a new item of category 'synonyms_included'
                    synonym_item = ITEM_FORMAT.copy()
                    synonym_item['category'] = current_category

                # mark current category as 'synonyms_included'
                current_category = 'synonyms_included'
                synonym_item['category'] = current_category

                last_end = 1
                for i in range(1, len(words)):
                    if words[i].endswith(','):
                        synonym_item['scientific_name'] = ' '.join(
                            words[last_end: i + 1]
                        ).rstrip(',').replace('"', '')
                        yield synonym_item
                        last_end = i + 1

                        # create a new item of category 'synonyms_included'
                        synonym_item = ITEM_FORMAT.copy()
                        synonym_item['category'] = current_category

                synonym_item['scientific_name'] = ' '.join(words[last_end:]).replace('"', '')

            else:
                # remove all '"', case with two double quotes: id=475820
                if synonym_item['scientific_name'] == '':
                    synonym_item['scientific_name'] = inner_text.replace('"', '')
                else:
                    synonym_item['scientific_name'] += ' ' + inner_text.replace('"', '')

    # in case of synonyms without a trailing <br>, case without a trailing <br>: id=191981
    if synonym_item['scientific_name'] != '':
        yield synonym_item


def parse_taxon_response(response: Response):
    request = response.request
    if request is not None and 'page_id' in request.meta:
        page_id = int(request.meta['page_id'])
    else:
        raise RuntimeError(f'missing page_id metadata for {response.url}')

    is_first_page = True
    if request is not None:
        is_first_page = bool(request.meta.get('is_first_page', True))

    soup = BeautifulSoup(response.text, 'html.parser')

    # parse synonyms (if applicable)
    if is_first_page:
        synonyms_soup = soup.find(
            'div',
            class_='clbarbodyl2'
        )
        if synonyms_soup is not None:
            h2_tag = synonyms_soup.find('h2')
            if h2_tag is not None and 'Scientific synonyms' in h2_tag.get_text():
                for item in _parse_synonyms(synonyms_soup):
                    item['parent'] = page_id
                    yield Item({
                        'type': 'synonym',
                        'parent': int(item['parent']),
                        'category': item['category'],
                        'synonym': item['scientific_name'],
                        'authority_year': item['authority_year'],
                    })

    # parse taxa children (if applicable)
    taxa_soup = soup.find(
        'div',
        class_='treeareadiv'
    )
    if taxa_soup is not None:
        for item in _parse_children(taxa_soup):
            item['parent'] = page_id
            child_page_id = item.get('id')
            if child_page_id:
                yield Item({
                    'type': 'taxon',
                    'id': int(item['id']),
                    'parent': int(item['parent']),
                    'category': item['category'],
                    'rank': item['rank'],
                    'scientific_name': item['scientific_name'],
                    'authority_year': item['authority_year'],
                    'geological_range': item['geological_range'],
                    'english_name': item['english_name'],
                })
                yield taxon_request(int(child_page_id))

    # recurse if this is not the last page, case with multiple pages: id=14772
    next_button = soup.find(
        'div',
        class_='clnextprevn'
    )
    if next_button is not None:
        next_a_tag = next_button.find('a')
        if next_a_tag is not None:
            yield Request(
                TAXON_URL.format(page_id=next_a_tag.get('href')[12:].rstrip('/')),
                meta={
                    'page_id': page_id,
                    'is_first_page': False,
                    'cookiejar': 'biolib',
                },
            )
