# Indezoek: Simple text file indexing and search

This is a very simple text indexing and search strategy using nothing but default Python libraries. The project was born from a need to select text documents from among hundreds of thousands, which is intractable to search with `find` and `grep`, and too large to work in a SQLite full-text search (FTS5) database.

There are much fancier/better solutions like Elasticsearch or Solr, but those are more power (and setup time and resource requirements) than I needed.

Indezoek is designed for fast indexing of a lot of documents, and search that requires a bit of patience.

## Usage

Requires Python 3.10+

```bash
python indezoek.py -h  # See help info
```

In a typical case you might want to find all documents of a particular type and index them, like this:

```bash
find . -type f -iname '*.txt' > files.list
python indezoek.py test.db --add-file-list files.list
python indezoek.py test.db --search chair fingers
```

If you're done adding files, it is also good to add an SQL index to the database. It is generally best to do that only at the end since, once indexed, inserting new documents will be much slower. For this reason, there is also a `--dbunindex` option to drop the index.

```bash
python indezoek.py test.db --dbindex  # Add SQL index
```

## Search terms

Documents are matched only if all search terms are present. Search terms are case-insensitive if specified in lowercase; any term with a capital letter in it will be searched for in a case-sensitive fashion. Only letters a-z are allowable in search terms, though spaces are possible by putting quotes around a term, like `--search "the whale" boat chair`.

It is best to **put uncommon words first**. The reason is that they are much faster to retrieve from the SQL index, and once the search space is narrow enough, it is faster to search the full text of the documents directly rather than via SQL. By default, Indezoek will switch over to full-text searching once there are fewer than 1,000 possible documents (which can be changed via `--full-text-switch`).
