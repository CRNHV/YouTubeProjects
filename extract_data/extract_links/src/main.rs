use std::io::{BufWriter, Write};
use std::{collections::HashSet, fs::File};
use std::time::Instant;
use std::char::from_u32;
use std::error::Error;

use parse_mediawiki_dump_reboot::schema::Namespace;
use rusqlite::{Connection, Result};
use regex::Regex;

extern crate parse_mediawiki_dump_reboot;
extern crate bzip2;

struct Page {
    alias: String,
    page: String,
    id: Option<i32>
}

fn main() -> Result<(), Box<dyn Error>> {
    // Open connection to a new database in memory. In memory database will run significantly faster than loading the database from a file
    let conn = Connection::open_in_memory()?;
    // Create the 'pages' table with the fields 'alias', 'page', and 'id'
    // alias => the Wikipedia name of the page
    // page => if the page is a redirect page then this is the page it redirects to, otherwise this is the same as the alias field
    // id => the unique ID of the page. Redirect pages do not have IDs
    conn.execute(
        "create table if not exists pages (
            alias text primary key,
            page text not null,
            id integer
        )", ())?;

    // Copy the data from the pages.db database to the in memory database
    conn.execute("attach database 'pages.db' as file", ())?;
    conn.execute("insert into pages select * from file.pages", ())?;

    println!("Database setup complete!");

    // Open and read the Wikipedia dump
    let file_path = "enwiki-latest-pages-articles-multistream.xml.bz2";
    let file = std::fs::File::open(file_path).unwrap();
    let file = std::io::BufReader::new(file);
    let file = bzip2::bufread::MultiBzDecoder::new(file);
    let file = std::io::BufReader::new(file);

    // Create a new csv writer to write the links to a csv
    let mut csv_writer = csv::Writer::from_path("links_raw.csv")?;
    csv_writer.write_record(&["source", "target"])?;

    // Create a file for dead end pages
    let deadend_file = File::create("deadends.txt")?;
    let mut deadend_writer = BufWriter::new(deadend_file);

    // Regex for matching disambiguation pages
    let disambig_regex = Regex::new(r"(?i)\{\{(dis|disam|disamb|disambig|dab|hndis|hndisambig|hndab|mathdab|geodis|geo-dis|geodab|geodisambig|roaddis|schooldis|[^\|\{\}#]*disambiguation( cleanup)?)(#|\||\}\})").unwrap();
    // Regex for matching soft redirect pages
    let soft_redir_regex = Regex::new(r"(?i)\{\{(wiktionary redirect|wi|wtr|soft redirect with wikidata item|wikidata redirect)(#|\||\}\})").unwrap();
    // Regex for matching links
    let link_regex = Regex::new(r"\[\[[^\[\]]+?\]\]").unwrap();
    // A more strict regex for matching wikilinks to other Wikipedia pages
    let wikilink_regex = Regex::new(r"(?i)\[\[:?(w:|en:)*(?<wikilink>.+?)(#|\||\]\])").unwrap();
    // Regex for matching the content outside of the main article. Everything after See Also, References, or External Links sections will be matched
    let article_regex = Regex::new(r"(?i)(?s)==\s*(see also|references|external links|notes).*").unwrap();
    // Regex for matching wikitext comments
    let comment_regex = Regex::new(r"(?s)<!--.*?-->").unwrap();
    // Regex for matching whitespace
    let spaces_regex = Regex::new(r"\s+").unwrap();

    let mut start_time = Instant::now();
    let mut article_count = 0;

    // Iterate over every wikipedia page in the dump
    for result in parse_mediawiki_dump_reboot::parse(file) {
        match result {
            Err(error) => {
                eprintln!("Error: {}", error);
                break;
            }
            // Check that page is in the correct namespace and format
            Ok(page) => if page.namespace == Namespace::Main && match &page.format {
                None => false,
                Some(format) => format == "text/x-wiki"
            } && match &page.model {
                None => false,
                Some(model) => model == "wikitext"
            } {
                // Continue to next page if page is a redirect page
                if page.text.trim_start().to_ascii_lowercase().starts_with("#redirect") {
                    continue;
                } 

                // Remove all wikitext comments
                let page_text = comment_regex.replace_all(&page.text, "");

                // Continue to next page if page is a disambiguation page
                if disambig_regex.is_match(&page_text) {
                    continue;
                }

                // Continue to next page if page is a soft redirect page
                if soft_redir_regex.is_match(&page_text) {
                    continue;
                }

                article_count += 1;
                // Remove content outside of the main article body
                let article_text = &article_regex.replace(&page_text, "");

                // Use HashSet to automatically ignore duplicate links on the same page
                let mut wikilinks: HashSet<String> = HashSet::new();
                // Find all links in the article
                for link_match in link_regex.find_iter(&article_text) {
                    // Check that the link is a wikilink
                    let Some(wikilink_capture) = wikilink_regex.captures(link_match.as_str()) else {
                        continue;
                    };

                    // Ignore wikilinks which are links for files or images
                    if wikilink_capture["wikilink"].starts_with("File:") || wikilink_capture["wikilink"].starts_with("Image:") {
                        continue;
                    }

                    // Add wikilink to set
                    wikilinks.insert(canonical_title(&wikilink_capture["wikilink"], &spaces_regex));
                }

                let mut wikilink_count = 0;
                let page_title = canonical_title(&page.title, &spaces_regex);
                // Iterate over each wikilink in the set and verify that it is a valid wikilink to a Wikipedia page
                for wikilink in wikilinks.iter() {
                    let verified_link = verify_link(wikilink, &conn);
                    // If link is valid, write it to the csv
                    match verified_link {
                        Some(link) => {
                            csv_writer.write_record(&[&page_title, &link])?;
                            wikilink_count += 1;
                        }
                        None => continue
                    }
                }

                // If page is a deadend, write it to the dead end file
                if wikilink_count == 0 {
                    writeln!(deadend_writer, "{}", page_title)?;
                    deadend_writer.flush()?;
                } else {
                    csv_writer.flush()?;
                }

                // Print progress
                if article_count % 10_000 == 0 {
                    println!("Extracted {} articles", article_count);
                    println!("Time taken: {}", start_time.elapsed().as_secs());
                    start_time = Instant::now();
                }
            }
        }
    }
    Ok(())
}

// Convert string to proper Wikipedia title formatting according to: https://en.wikipedia.org/wiki/Wikipedia:Naming_conventions_(technical_restrictions)
// Since the page title may not be properly formatted in the link, we need to format it with this function
fn canonical_title(data: &str, spaces_regex: &Regex) -> String {
    let mut result = String::new();
    let mut first = true;
    // Capitalize first letter
    for value in data.chars() {
        if first {
            first = false;
            let upper_char_u32 = unicode_case_mapping::to_uppercase(value)[0];

            if upper_char_u32 == 0 {
                result.push(value);
                continue;
            }
            
            match from_u32(upper_char_u32) {
                Some(upper_char) => result.push(upper_char),
                None => result.push(value)
            }
        } else {
            result.push(value);
        }
    }
    // Replace illegal characters with spaces
    result = result.replace("&nbsp;", " ");
    result = result.replace("_", " ").trim().to_string();
    result = spaces_regex.replace_all(&result, " ").to_string();
    result
}

fn verify_link(link: &String, conn: &Connection) -> Option<String> {
    // Query database and verify that link points to a valid page
    let linked_page = match query_db(link, conn) {
        Some(page) => page,
        None => return None
    };

    // Page is an article, so link is valid
    if linked_page.id.is_some() {
        return Some(linked_page.page);
    }

    // Page in link is a redirect page, query database again to find the destination of the redirect page
    let redir_page = match query_db(&linked_page.page, conn) {
        Some(page) => page,
        None => return None
    };

    // Verify that new page is an article
    if redir_page.id.is_some() {
        return Some(redir_page.page)
    }
    None
}

// Query the database for a page
fn query_db(alias: &String, conn: &Connection) -> Option<Page> {
    let query = format!("select alias, page, id from pages where alias=\"{}\"", alias.replace("\"", "\"\""));

    let query_result = conn.query_row(&query, [], |row| {
        Ok(Page {
            alias: row.get(0)?,
            page: row.get(1)?,
            id: row.get(2)?
        })
    });

    match query_result {
        Ok(page) => {
            Some(page)
        }
        Err(_) => {
            None
        }
    }
}
