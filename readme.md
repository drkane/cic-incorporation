CIC text extraction
===================

Extract community interest statements, activities and community benefit from CIC36 documents.

Installation
------------

1. [Install python](https://wiki.python.org/moin/BeginnersGuide/Download)
2. Download this repository and extract to its own directory
3. Open your command line or terminal and navigate to the directory containing the code
4. Create a python virtual environment:
   ```
   python -m venv env
   ```
5. Activate the virtual environment:
   - Windows: `env\Scripts\activate`
   - Mac/Linux: `source env/bin/activate`
6. Install the dependencies:
    ```
    pip install -r requirements.txt
    ```

Run the extraction
------------------

To run the program, use the following command in the command line or terminal:

```
python -m extraction "path/to/files/**.*" "results.csv"
```

Replace the `"path/to/files/**.*"` with the location of your files. These can either contain PDF files or ZIP files that contain PDFs. The file path uses pythons [glob syntax](https://docs.python.org/3/library/glob.html) so you can match multiple files using the "*" wildcard.

The results are output as a csv to "results.csv" or another file if given. If the CSV already exists then the results will be appended rather than overwritten.
