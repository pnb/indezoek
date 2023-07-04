from collections import Counter
import argparse
import sqlite3


ALPHABET = "abcdefghijklmnopqrstuvwxyz"
SPACES = " \n"


def make_tables(sqlite_cursor: sqlite3.Cursor):
    sqlite_cursor.execute(
        """CREATE TABLE IF NOT EXISTS docs (
        doc_id INTEGER PRIMARY KEY,
        path TEXT UNIQUE);"""
    )
    sqlite_cursor.execute(
        """CREATE TABLE IF NOT EXISTS words (
        idx INTEGER PRIMARY KEY,
        word TEXT,
        doc_id INTEGER,
        count INTEGER,
        FOREIGN KEY(doc_id) REFERENCES docs(doc_id));"""
    )


def index_doc(sqlite_cursor: sqlite3.Cursor, path: str):
    with open(path, "r", encoding="utf8", errors="ignore") as infile:
        txt = "".join(
            [l for l in infile.read().lower() if l in ALPHABET or l in SPACES]
        )
    words = txt.split()
    word_counts = Counter(words)
    # Save to DB
    sqlite_cursor.execute("INSERT INTO docs (path) VALUES (?);", (path,))
    doc_id = sqlite_cursor.lastrowid
    sqlite_cursor.executemany(
        "INSERT INTO words (doc_id, word, count) VALUES (?, ?, ?)",
        [(doc_id, w, c) for w, c in word_counts.items()],
    )


def search_docs(sqlite_cursor: sqlite3.Cursor, terms: list[str], quiet: bool = False):
    term_words = []
    for term in terms:
        term_words.extend(term.split())  # Split multi-word quoted terms into words
    term_words = [w.lower() for w in term_words]
    # Find docs with all of the words in each of the terms
    doc_ids = set()
    for i, word in enumerate(term_words):
        if not quiet:
            print("Searching for:", " ".join(term_words[: i + 1]), end="\r")
        sqlres = sqlite_cursor.execute(
            "SELECT doc_id FROM words WHERE word = ?", (word,)
        )
        if i == 0:
            doc_ids.update([str(row[0]) for row in sqlres])
        else:
            doc_ids.intersection_update([str(row[0]) for row in sqlres])
    # This was a clever query to search all terms at once but makes it hard to see progress
    # q = 'SELECT doc_id FROM words WHERE word IN ("' + '", "'.join(term_words) + \
    #     '") GROUP BY doc_id HAVING COUNT(*) = ' + str(len(term_words)) + ';'
    # doc_ids = [str(row[0]) for row in sqlite_cursor.execute(q)]
    # Get paths of docs from result
    if not quiet:
        print("\nGetting document paths")
    q = "SELECT path FROM docs WHERE doc_id IN (" + ", ".join(doc_ids) + ");"
    paths = [row[0] for row in sqlite_cursor.execute(q)]
    paths_to_remove = set()
    # Search resulting files if needed (complex terms)
    if any(t not in term_words for t in terms):
        for i, path in enumerate(paths):
            if not quiet:
                print("Full-text searching result", i + 1, "/", len(paths), end="\r")
            with open(path, "r", encoding="utf8", errors="ignore") as infile:
                txt = " " + " ".join(infile.read().split()) + " "
            txtlower = txt.lower()
            for term in terms:
                if term not in term_words:
                    firstmatch = -1
                    matchlen = len(term)  # Future-proofing terms with markup
                    if term == term.lower():
                        firstmatch = txtlower.find(term)
                    else:
                        firstmatch = txt.find(term)
                    if (
                        firstmatch < 0
                        or txtlower[firstmatch - 1] in ALPHABET
                        or txtlower[firstmatch + matchlen] in ALPHABET
                    ):
                        paths_to_remove.add(path)  # Not a match
                        break
        if not quiet:
            print()
    paths = sorted(set(paths).difference(paths_to_remove))
    if len(paths):
        print("\n".join(paths))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("sqlite_db", help="Path to SQLite DB file (need not exist)")
    ap.add_argument(
        "--add-file-list",
        metavar="PATH",
        help="Path to newline-delimited list of paths to add",
    )
    ap.add_argument(
        "--search",
        metavar="TERM",
        nargs="+",
        help="Space-delimited list of search terms (ANDed together)",
    )
    ap.add_argument("--dbindex", action="store_true", help="Add SQL index to DB")
    ap.add_argument("--dbunindex", action="store_true", help="Remove SQL index from DB")
    ap.add_argument(
        "--quiet", action="store_true", help="Output only results in search"
    )
    args = ap.parse_args()

    sqlcon = sqlite3.connect(args.sqlite_db)
    cursor = sqlcon.cursor()
    make_tables(cursor)

    if args.add_file_list:
        with open(args.add_file_list, "r", encoding="utf8") as infile:
            paths = infile.readlines()
        for i, path in enumerate(paths):
            print("Indexing", i + 1, "/", len(paths), end="\r")
            if len(path.rstrip("\n")):
                index_doc(cursor, path.rstrip("\n"))
        print("\nCommitting SQL transaction")
        sqlcon.commit()
    if args.dbindex:
        print("Creating SQL word index")
        cursor.execute("CREATE INDEX idx_word ON words (word);")
    elif args.dbunindex:
        print("Deleting SQL word index")
        cursor.execute("DROP INDEX idx_word;")
    if args.search:
        search_docs(cursor, args.search, args.quiet)
