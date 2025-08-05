from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chromium.webdriver import ChromiumDriver
from selenium.webdriver.remote.webelement import WebElement
import pandas as pd
from album_types import AlbumRow
from typing import List
from tqdm import tqdm
from typing import Optional
import time, re

_SEARCH_URL = "https://www.discogs.com/artist/3264165-Dami%C3%A3o-Experien%C3%A7a"
_ALBUMS_FILEPATH = "files/albums.csv"

# Function to initialize the ChromeDriver instance
def _initialize_chromedriver():
    driver = webdriver.Chrome()
    try:
        driver.set_window_position(1920, 0)
        driver.maximize_window()
    except Exception as e:
        print(f"Error: {e}")
    return driver

def _navigate_to_element(web_element: WebElement):
    web_element._parent.execute_script("arguments[0].scrollIntoView({block: 'center'});", web_element)

def _close_popups(driver: ChromiumDriver):
    try:
        WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, "onetrust-accept-btn-handler"))
        ).click()

        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, 'gist-embed-container'))
        )
        container = driver.find_element(By.ID, 'gist-embed-container')
        iframe = container.find_element(By.TAG_NAME, 'iframe')
        driver.switch_to.frame(iframe)
        modal = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, '//div[@class="modal" and @role="dialog"]'))
        )
        close_container = modal.find_element(By.XPATH, './/div[contains(@class, "close-container")]')
        close_button = close_container.find_element(By.XPATH, './/button[contains(@class, "close-button")]')
        WebDriverWait(driver, 10).until(lambda d: close_button.is_enabled() and close_button.is_displayed())
        close_button.click()
        driver.switch_to.default_content()
    except Exception as e:
        print(f"Error closing popups: {e}")

def _update_table_parameters(driver: ChromiumDriver):
    try:
        # Click the button to switch to text-only view
        text_only_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, '//button[@title="Switch to text-only view"]'))
        )
        text_only_button.click()

        # Select the option with the greatest integer value in the dropdown
        select_container = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, '//div[contains(@class, "selectContainer")]'))
        )
        select_element = select_container.find_element(By.TAG_NAME, 'select')
        options = select_element.find_elements(By.TAG_NAME, 'option')
        max_option = max(options, key=lambda opt: int(opt.get_attribute('value') or 0))
        max_option.click()

        # Wait for the table to be recreated
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, '//table[contains(@class, "releases")]'))
        )

        # Wait for the correct table structure to appear
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, '//table[contains(@class, "releases")]/thead'))
        )
    except Exception as e:
        print(f"Error updating table parameters: {e}")
        raise e
    
def _find_albums_table(driver: ChromiumDriver) -> WebElement:
    try:
        tables = driver.find_elements(By.XPATH, '//table[contains(@class, "releases")]')
        assert len(tables) == 1, "Expected exactly one table with class 'releases'"
        content_table = tables[0]
        
        # Search for "Albums" header and body
        table_children = list(content_table.find_elements(By.XPATH, "./*"))
        
        album_thead = next(child for child in table_children if child.text.strip() == "Albums")
        assert album_thead.tag_name == "thead", "Expected 'Albums' header to be a thead element"

        album_thead_index = table_children.index(album_thead)
        albums_table = table_children[album_thead_index + 1]
        
        return albums_table
    except Exception as e:
        print(f"Error finding albums table: {e}")
        raise e

def _find_expand_button(tr: WebElement) -> Optional[WebElement]:
    try:
        title_td = tr.find_element(By.XPATH, './/td[contains(@class, "title")]')

        try:
            span = title_td.find_element(By.TAG_NAME, 'span')
        except Exception:
            span = None
            
        if span is None: return None # Skip rows without a span
        button = span.find_element(By.XPATH, './/button[contains(@class, "versionsButton")]')
        return button
    except Exception as e:
        print(f"Error finding expand button: {e}")
        raise e

def _expand_all_versions(driver: ChromiumDriver):
    
    albums_table = _find_albums_table(driver)
    
    try:
        trs = WebDriverWait(driver, 10).until(lambda d: albums_table.find_elements(By.TAG_NAME, 'tr'))
        expand_count = 0

        for tr in tqdm(trs, desc="Expanding versions", unit="row"):
            _navigate_to_element(tr)

            expand_button = _find_expand_button(tr)

            if expand_button is None:
                continue # Skip rows without an expand button

            assert expand_button.get_attribute('aria-expanded') == "false", "Expected aria-expanded to be 'false' before click"

            # extract number of versions from button text
            btn_text = expand_button.text
            match = re.search(r'(\d+)', btn_text)
            versions_count = int(match.group(1)) if match else 0
            expand_count += versions_count

            expand_button.click()
            WebDriverWait(driver, 10).until(lambda _: expand_button.get_attribute('aria-expanded') == "true") # pyright: ignore[reportOptionalMemberAccess]
            
        print(f"Added {expand_count} expanded rows in total.")
        
        return len(trs), expand_count
    except Exception as e:
        print(f"Error expanding all versions: {e}")
        raise e

def extract_album_row(tr: WebElement, is_version: bool = False) -> AlbumRow:
    # 1) formatsContainer div with "LP"
    expand_button = _find_expand_button(tr)
    if expand_button is None:
        WebDriverWait(tr, 10).until(
            EC.presence_of_element_located((By.XPATH, './/div[contains(@class, "formatsContainer")]'))
        )
        formats_div = tr.find_element(By.XPATH, './/div[contains(@class, "formatsContainer")]')
        assert "LP" in str(formats_div.get_attribute("innerHTML")), "Expected 'LP' in formatsContainer div"

    # 2) title td
    title_td = tr.find_element(By.XPATH, './/td[contains(@class, "title")]')
    title_a = title_td.find_element(By.TAG_NAME, 'a')
    title = title_a.text.strip()

    # 3) cat td
    album_id = None
    if expand_button is None:
        cat_td = tr.find_element(By.XPATH, './/td[contains(@class, "cat")]')
        if not is_version:
            cat_span = cat_td.find_element(By.TAG_NAME, 'span')
            cat_div = cat_span.find_element(By.TAG_NAME, 'div')
        else:
            cat_div = cat_td.find_element(By.TAG_NAME, 'div')
        assert cat_div.get_attribute('tabindex') == "0", "Expected tabindex to be '0' in cat_div"
        album_id = cat_div.text.strip()

    # 4) year td
    year_td = tr.find_element(By.XPATH, './/td[contains(@class, "year")]')
    year = year_td.text.strip()

    # 5) create dictionary
    album_row = AlbumRow(title=title)
    if album_id is not None and album_id != "non":
        album_row.ids.add(album_id)
    album_row.years.add(year)
    return album_row

def _extract_album_rows(driver: ChromiumDriver) -> tuple[List[AlbumRow], int]:
    
    albums_table = _find_albums_table(driver)
    first_tr = albums_table.find_element(By.TAG_NAME, 'tr')
    _navigate_to_element(first_tr)
    print("Waiting for albums table to load...")
    time.sleep(2)
    print("Loading completed!")
    
    try:
        trs = WebDriverWait(driver, 10).until(lambda d: albums_table.find_elements(By.TAG_NAME, 'tr'))
        album_rows: List[AlbumRow] = []
        
        for tr in tqdm(trs, desc="Extracting all rows", unit="row"):
            _navigate_to_element(tr)

            tr_class = tr.get_attribute("class")
            assert tr_class is not None, "Expected tr to have a class attribute"

            if "textOnlyRow" in tr_class:
                album_row = extract_album_row(tr)
                album_rows.append(album_row)
            elif "versionsTextOnlyRow" in tr_class:
                expanded_album_row = extract_album_row(tr, is_version=True)
                album_row = next(row for row in album_rows if row.title == expanded_album_row.title)
                album_row.ids.update(expanded_album_row.ids)
                album_row.years.update(expanded_album_row.years)
            elif "closeVersionsButton" in tr_class:
                close_versions_tr_index = trs.index(tr)
                text_only_tr = None
                
                for i in range(close_versions_tr_index - 1, -1, -1):
                    current_tr = trs[i]
                    current_tr_class = str(current_tr.get_attribute("class"))
                    
                    # Expanded rows
                    if "versionsTextOnlyRow" in current_tr_class:
                        continue
                    
                    # Original text-only row
                    elif "textOnlyRow" in current_tr_class:
                        text_only_tr = current_tr
                        break
                    
                    else:
                        raise ValueError(f"Unexpected check tr class: {current_tr_class}")

                assert text_only_tr is not None, "Could not find preceding row with textOnlyRow class"
            elif "mobileStackedVersions" in tr_class:
                continue  # Skip mobile stacked versions rows
            else:
                raise ValueError(f"Unexpected tr class: {tr_class}")

        # Just so we can visually confirm everything loaded correctly
        _navigate_to_element(first_tr)
        time.sleep(1)

        return album_rows, len(trs)
    except Exception as e:
        print(f"Error extracting album rows: {e}")
        raise e
    
def _save_to_csv(album_rows: List[AlbumRow]):
    try:
        df = pd.DataFrame([album.model_dump() for album in album_rows])
        df.to_csv(_ALBUMS_FILEPATH, index=False)
        print(f"Saved {len(album_rows)} albums to {_ALBUMS_FILEPATH}")
    except Exception as e:
        print(f"Error saving to CSV: {e}")
        raise e


def extract_from_webpage():
    driver = _initialize_chromedriver()
    try:
        # Navigate to the search URL
        driver.get(_SEARCH_URL)

        _close_popups(driver)
        _update_table_parameters(driver)

        original_trs_len, expand_count = _expand_all_versions(driver)
        album_rows, expanded_trs_len = _extract_album_rows(driver)

        assert len(album_rows) == original_trs_len, f"Expected {original_trs_len} album rows, but found {len(album_rows)}"
        assert original_trs_len + (expand_count * 2) == expanded_trs_len, f"Expected {original_trs_len} original rows + {expand_count * 2} expanded rows, but found {expanded_trs_len}"
        
        # Manually add an album that doesn't exist in the table
        new_album_row = AlbumRow(title="Planeta Lamma", ids={"DEPL108, musique brut 2"}, years={"2022"})
        album_rows.append(new_album_row)
        
        _save_to_csv(album_rows)

    finally:
        driver.quit()