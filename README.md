# Wikipedia Graph
This project has 2 parts: 
1. [Extracting the data from Wikipedia dumps](#extracting-the-data)
2. [Creating the graph and visual representation](#creating-the-graph)

I am providing some project files that will allow you to expedite parts of the process if you are not interested in creating the graph entirely from scratch. You can download and extract the project files manually from [here](https://adumb-files.s3.us-west-2.amazonaws.com/project_files.zip) to the root directory of the project or by doing the following:
```
wget https://adumb-files.s3.us-west-2.amazonaws.com/project_files.zip
unzip project-files.zip
```
If you choose to use the project files then you can skip directly to part 2. The Jupyter notebook will explain how to use these project files.

Note: If you want to create the Wikipedia graph from scratch, there are parts where you will need a lot of RAM (up to 64GB). If you use the project files I created then you may only need around 8GB of RAM. If you need more ram, you can look at using cloud computing like [AWS EC2 instances](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/concepts.html). I used a `r6g.2xlarge` EC2 instance for most of this project.

## Associated Videos
- [Original YouTube video](https://www.youtube.com/watch?v=JheGL6uSF-4)

## Extracting the data
This part of the project will parse the Wikipedia dumps in order to create a csv file of the links of wikipedia. It will also create a csv for all of the categories for a given page. This ends up being a three step process:
1. [Extracting the pages](#extracting-the-pages)
2. [Extracting the links](#extracting-the-links)
3. [Extracting the categories](#extracting-the-categories)

### Prerequisites
- This part of the project is in [Rust](https://www.rust-lang.org/). View [this page](https://www.rust-lang.org/tools/install) for instructions on installing rust.
- This part of the project also uses [SQLite](https://www.sqlite.org/). View [this page](https://www.tutorialspoint.com/sqlite/sqlite_installation.htm) for installing SQLite.
- You will need to download one of the `pages-articles-multistream.xml.bz2` Wikipedia dumps. This contains data for each page on Wikipedia. You can download the latest Wikipedia dump [from here](https://dumps.wikimedia.org/enwiki/latest/enwiki-latest-pages-articles-multistream.xml.bz2). You do not need to extract the file, since we will directly read the `bz2` file. You can view more information on Wikipedia dumps [here](https://en.wikipedia.org/wiki/Wikipedia:Database_download).

### Extracting the pages
The first step to extract the data is to get a complete list of every article on Wikipedia. This is tricky because not every page in the Wikipedia dump will be a valid article. In particular, we don't want to include disambiguation pages, redirect pages, and soft redirect pages. [Read more about Wikipedia articles](https://en.wikipedia.org/wiki/Wikipedia:What_is_an_article%3F). We will do this with multiple regex expressions. However, we also want to keep track of where redirect pages redirect to. To do this we create a local SQLite database which will be saved to `pages.db` and will have three fields:
- `alias` - The Wikipedia title of the page
- `page` - If the page is a redirect page then this is the page it redirects to, otherwise this is the same as the alias field
- `id` - The unique ID of the page. Redirect pages do not have IDs

To run the Rust module do the following:
```
cd extract_data
cargo run -p extract_pages --release
```

### Extracting the links
Now we will parse the text each article and find the links to other articles. We will do this with multiple regex expressions. When we find the links we will reference the SQLite database to confirm that it is a link to a valid article and we will also resolve links to redirect pages. The output will be a csv file of links. The first column will be the page that the link originates from and the second column will be the page that is linked to. It will also output a txt file of dead end pages, pages which do not have any outgoing links. To run the Rust module do the following:
```
cargo run -p extract_links --release
```

### Extracting the categories
This module will extract the categories for each article on Wikipedia. If you are not interested in doing analysis of categories then you can skip this section. Once again, we will extract the categories using multiple regex expressions. The output will be a csv file. The first column will be the page name and the second column is a category for the page. Each category for each page will have its own row. To run the Rust module do the following:
```
cargo run -p extract_categories --release
```

## Creating the graph
This part of the project is in a Jupyter notebook. If you're not familiar with Jupyter, go to their [website](https://jupyter.org/) to learn more and [install](https://jupyter.org/install#jupyter-notebook) Jupyter.

### Prerequisites
Install python dependencies:
```
pip install -r requirements.txt
```

### Start the notebook
Run the following command to start Jupyter:
```
jupyter notebook
```
Then open the `wikigraph.ipynb` file to view and run the code. The notebook contains notes explaining the code and how to create the graph.