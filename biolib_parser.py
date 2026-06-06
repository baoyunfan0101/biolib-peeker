from bs4 import BeautifulSoup, NavigableString, Tag
import requests
import time

ROOT_URL = "https://www.biolib.cz/en/"
BASE_URL = ROOT_URL + "taxon/id"
ITEM_FORMAT = {
    "id": "",  # primary key
    "category": "",
    "rank": "",
    "scientific_name": "",
    "authority_year": "",
    "geological_range": "",
    "english_name": "",
}
MAX_RETRY = 3

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0"
})


def pass_security_check():
    # post payload
    session.post(
        ROOT_URL,
        data={
            "cntbtn": "Continue",
            "action": "passcheck",
            "hpsec": ""
        }
    )


def get_page(url, max_retries=MAX_RETRY):
    errors = []

    for _ in range(max_retries):
        try:
            resp = session.get(
                url,
                timeout=(5, 30),  # 5 seconds to connect, 30 seconds to read
            )
            # raise exception if failed
            resp.raise_for_status()

            soup = BeautifulSoup(resp.text, "html.parser")

            # if getting security checked
            if soup.find("input", {"name": "action", "value": "passcheck"}):
                errors.append(RuntimeError("security check triggered"))
                pass_security_check()
                continue

            return soup

        except requests.RequestException as e:
            errors.append(e)
            time.sleep(1)

    raise RuntimeError(
        f"failed to fetch {url}; "
        f"errors={[str(e) for e in errors]}"
    )


def parse_children(taxa_soup):
    content_of_interest = []

    current_category = ""

    for child in taxa_soup.children:
        # skip children like "\n"
        if isinstance(child, Tag):

            if child.name == "h2":
                current_category = child.text.split()[0].lower()

            elif child.name == "div":
                child_class = child.get("class")
                if child_class is None or child_class[0] not in ["treediv", "treeenddiv"]:
                    continue

                div_item = ITEM_FORMAT.copy()

                div_item["category"] = current_category

                # extract rank
                first_content = str(child.contents[0]).split()
                if len(first_content) >= 1:
                    div_item["rank"] = first_content[0]

                # extract <a>
                a_tags = child.find_all("a")

                if len(a_tags) >= 1:
                    div_item["id"] = None if a_tags[0] is None else a_tags[0].get("href")[12:-1]
                    div_item["scientific_name"] = None if a_tags[0] is None else a_tags[0].get_text(strip=True)
                    if len(a_tags) >= 2 and current_category == "fossil":
                        if a_tags[-1].get("href") == "#incertaesedis":
                            div_item["category"] += "_unplaced"
                        else:
                            div_item["category"] += "_included"

                # extract <small>
                small_tags = child.find_all("small")
                if len(small_tags) >= 2:
                    div_item["authority_year"] = small_tags[0].get_text(strip=True).replace("&amp;", "&")
                    div_item["geological_range"] = small_tags[1].get_text(strip=True).replace("&ndash;", "-")
                elif len(small_tags) == 1:
                    previous_tag = small_tags[0].find_previous_sibling()
                    if previous_tag is not None and previous_tag.name == "br":
                        div_item["geological_range"] = small_tags[0].get_text(strip=True).replace("&ndash;", "-")
                    else:
                        div_item["authority_year"] = small_tags[0].get_text(strip=True).replace("&amp;", "&")

                # extract <strong>
                strong_tag = child.find("strong")
                div_item["english_name"] = None if strong_tag is None else strong_tag.get_text(strip=True)

                content_of_interest.append(div_item)

    return content_of_interest


def parse_synonyms(synonyms_soup):
    content_of_interest = []

    current_category = "scientific_synonyms"

    p_tag = synonyms_soup.find("p")

    # create a new item
    synonym_item = ITEM_FORMAT.copy()
    synonym_item["category"] = current_category

    for child in p_tag.children:

        if isinstance(child, NavigableString):
            inner_text = child.strip()
            if inner_text:
                synonym_item["scientific_name"] = inner_text

        if isinstance(child, Tag):
            if child.name == "br":
                if synonym_item["scientific_name"] != "" or synonym_item["authority_year"] != "":
                    content_of_interest.append(synonym_item)

                    # create a new item
                    synonym_item = ITEM_FORMAT.copy()
                    synonym_item["category"] = current_category

            elif child.name == "em":
                synonym_item["scientific_name"] = child.get_text(strip=True)

            elif child.name == "small":
                synonym_item["authority_year"] = child.get_text(strip=True)

    return content_of_interest


# main entry
def resolve_page(page_id, max_retries=MAX_RETRY):
    if page_id is None or page_id == "":
        return []
    else:
        url = BASE_URL + page_id

    soup = get_page(url, max_retries=max_retries)
    content_of_interest = []

    # parse synonyms (if applicable)
    synonyms_soup = soup.find(
        "div",
        class_="clbarbodyl2"
    )
    if synonyms_soup is not None:
        h2_tag = synonyms_soup.find("h2")
        if h2_tag is not None and "Scientific synonyms" in h2_tag.get_text():
            content_of_interest += parse_synonyms(synonyms_soup)

    # parse taxa children (if applicable)
    taxa_soup = soup.find(
        "div",
        class_="treeareadiv"
    )
    if taxa_soup is not None:
        content_of_interest += parse_children(taxa_soup)

    # recurse if this is not the last page, case with multiple pages: id=14772
    next_button = soup.find(
        "div",
        class_="clnextprevn"
    )
    if next_button is not None:
        next_a_tag = next_button.find("a")
        if next_a_tag is not None:
            content_of_interest += resolve_page(next_a_tag.get("href")[12:])

    return content_of_interest


def display_content(content_of_interest):
    print("[")
    for item in content_of_interest:
        print("\t{")
        for key, value in item.items():
            print(f"\t\t{key}: {value},")
        print("\t},")
    print("]")


if __name__ == "__main__":
    # display_content(resolve_page("14772")) # initial page
    # display_content(resolve_page("14778")) # a cross-page case
    # display_content(resolve_page("464996")) # a leaf-node case
    # display_content(resolve_page("369498")) # a leaf-node case with a lot of synonyms
    # display_content(resolve_page("557990")) # a internal-node case without synonyms
    pass
