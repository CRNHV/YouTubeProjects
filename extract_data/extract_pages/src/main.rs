use rusqlite::{Connection, Result};
use parse_mediawiki_dump_reboot::schema::Namespace;
use regex::Regex;
use std::time::Instant;
use std::char::from_u32;

extern crate parse_mediawiki_dump_reboot;
extern crate bzip2;

fn main() -> Result<()> {
    // Open connection to a local sqlite3 database saved to pages.db
    let conn = Connection::open("pages.db")?;
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

    // Open and read the Wikipedia dump
    let file_path = "enwiki-latest-pages-articles-multistream.xml.bz2";
    let file = std::fs::File::open(file_path).unwrap();
    let file = std::io::BufReader::new(file);
    let file = bzip2::bufread::MultiBzDecoder::new(file);
    let file = std::io::BufReader::new(file);

    // Regex for matching links
    let link_regex = Regex::new(r"(?i)\[\[:?(w:|en:)*(?<alias>.+?)(#|\||\]\])").unwrap();
    // Regex for matching disambiguation pages
    let disambig_regex = Regex::new(r"(?i)\{\{(dis|disam|disamb|disambig|dab|hndis|hndisambig|hndab|mathdab|geodis|geo-dis|geodab|geodisambig|roaddis|schooldis|[^\|\{\}#]*disambiguation( cleanup)?)(#|\||\}\})").unwrap();
    // Regex for matching soft redirect pages
    let soft_redir_regex = Regex::new(r"(?i)\{\{(wiktionary redirect|wi|wtr|soft redirect with wikidata item|wikidata redirect)(#|\||\}\})").unwrap();
    // Regex for matching wikitext comments
    let comment_regex = Regex::new(r"(?s)<!--.*?-->").unwrap();
    // Regex for matching whitespace
    let spaces_regex = Regex::new(r"\s+").unwrap();

    let mut article_count = 0;
    let mut start_time = Instant::now();
    
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
                // Check if page is a redirect page
                if page.text.trim_start().to_ascii_lowercase().starts_with("#redirect") {
                    // Match the redirect link in the page
                    let Some(link_capture) = link_regex.captures(&page.text) else {
                        println!("The page {} is a redirect, but does not contain a redirect link", canonical_title(&page.title, &spaces_regex));
                        continue;
                    };

                    let link = &link_capture["alias"];
                    // Insert redirect page into database with it's redirect link and continue to next page
                    conn.execute(
                        "INSERT OR IGNORE INTO pages (alias, page) values (?1, ?2)",
                        &[&canonical_title(&page.title, &spaces_regex), &canonical_title(link, &spaces_regex)]
                    )?;
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
                // Insert article into database
                conn.execute(
                    "INSERT OR IGNORE INTO pages (alias, page, id) values (?1, ?2, ?3)", 
                    &[&canonical_title(&page.title, &spaces_regex), &canonical_title(&page.title, &spaces_regex), &article_count.to_string()]
                )?;

                // Print progress
                if article_count % 10_000 == 0 {
                    println!("Extracted {} articles", article_count);
                    println!("Time taken: {}", start_time.elapsed().as_secs());
                    start_time = Instant::now();
                }
            }
        }
    }

    println!("Articles: {article_count:?}", article_count=article_count);
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
