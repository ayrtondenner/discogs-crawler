import pandas as pd

_FILES_FOLDER = "files"
_ALBUMS_FILEPATH = f"{_FILES_FOLDER}/albums.csv"
_OWNED_ALBUMS_FILEPATH = f"{_FILES_FOLDER}/owned_albums.txt"
_NOT_OWNED_ALBUMS_FILEPATH = f"{_FILES_FOLDER}/not_owned_albums.txt"

# Update 'owned' column
def _is_owned(row: pd.Series, owned_albums: list[str]) -> bool:
    title = str(row["title"])
    if title == "Planeta Lamma" and "Planeta Lamma" in owned_albums:
        return True

    owned = any(album for album in owned_albums if album in title)
    return owned

def update_csv():
    # Read owned_albums.txt as a list of strings
    try:
        with open(_OWNED_ALBUMS_FILEPATH, "r", encoding="utf-8") as f:
            owned_albums = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        print(f"{_OWNED_ALBUMS_FILEPATH} not found. No updates will be made.")
        return

    # Load albums.csv as a pandas DataFrame
    try:
        df = pd.read_csv(_ALBUMS_FILEPATH, encoding="utf-8")
    except FileNotFoundError:
        print(f"{_ALBUMS_FILEPATH} not found. No updates will be made.")
        return

    df["owned"] = df.apply(lambda row: _is_owned(row, owned_albums), axis=1)

    # Save updated DataFrame back to CSV
    df.to_csv(_ALBUMS_FILEPATH, index=False, encoding="utf-8")
    not_owned_albums = df.loc[~df["owned"], "title"].tolist()

    with open(_NOT_OWNED_ALBUMS_FILEPATH, "w", encoding="utf-8") as f:
        for album in not_owned_albums:
            f.write(f"{album}\n")

    total = len(df)
    not_owned_count = len(not_owned_albums)
    owned_count = total - not_owned_count    

    owned_percentage = (owned_count / total) * 100 if total else 0
    not_owned_percentage = (not_owned_count / total) * 100 if total else 0

    print(f"Owned: {owned_count} ({owned_percentage:.2f}%)")
    print(f"Not Owned: {not_owned_count} ({not_owned_percentage:.2f}%)")
    
    print("\nNot Owned Albums:")
    for album in not_owned_albums:
        print(f"- {album}")