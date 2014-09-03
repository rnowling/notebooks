import argparse
import json
import random
import re
import sys
import time

from bs4 import BeautifulSoup
import requests

def fetch_article(en_title, other_languages=None):
    if other_languages == None:
        other_languages = []
        
    articles = []
    
    url = "http://en.wikipedia.org/wiki/%s" % en_title
    r = requests.get(url)
    
    articles.append(("en", url, en_title))
    
    soup = BeautifulSoup(r.text)
    language_links = soup.find(id="p-lang").find_all("li", class_="interlanguage-link")
    for language_link in language_links:
        a_tag = language_link.find("a")
        language = a_tag["lang"]
        url = a_tag["href"]
        title = a_tag["title"].split(u"\u2013")[0].strip()
        #print language, url, title
        if language in other_languages:
            articles.append((language, "http:" + url, title))

    article_content = []
    for lang, url, title in articles:
        last_sep = url.rfind("/")
        encoded_title = url[last_sep+1:]
        content_url = "http://" + lang + ".wikipedia.org/w/index.php?title=" + encoded_title + "&action=edit"
        print content_url
        r = requests.get(content_url)
        
        soup = BeautifulSoup(r.text)
        textarea = soup.find("textarea")
        article_content.append((lang, title, textarea.text, en_title))
        
    return article_content

def remove_block_regex(text, start_delim, end_delim):
    block_regex = re.compile(start_delim + r".+?" + end_delim, flags=re.DOTALL)
    new_string = ""
    last_end = 0
    for match in block_regex.finditer(text):
        new_string += text[last_end:match.start(0)] + " " 
        last_end = match.end(0)
    new_string += text[last_end:]
    
    return new_string

def replace_link_block(block):
    if "|" in block:
        start = block.find("|")
        # remove links to files
        if ":" in block[:start]:
            return " "
        # return label, not article name
        return block[start+1:]
    
    return block

def replace_link_block2(block):
    if " " in block:
        s = block.find(" ")
        return block[s+1:]

    return " "

def substitute_links(text):
    while True:
        end_pos = text.find("]]")
        if end_pos == -1:
            break

        start_pos = text.rfind("[[", 0, end_pos)
        if start_pos == -1:
            break

        block = text[start_pos:end_pos+2]
        substitute = replace_link_block(block[2:-2])
        text = text[:start_pos] + substitute + text[end_pos+2:]

    while True:
        end_pos = text.find("]")
        if end_pos == -1:
            break

        start_pos = text.rfind("[", 0, end_pos)
        if start_pos == -1:
            break

        block = text[start_pos:end_pos+1]
        substitute = replace_link_block2(block[1:-1])
        text = text[:start_pos] + substitute + text[end_pos+1:]

    return text

def remove_tail(text):
    text_l = text.lower()

    headers = ["==See Also==", "== See Also ==", "==References==", "== References ==",
                "==External Links==", "== External Links ==", "==Further Reading==",
                "== Further Reading =="]
    positions = [text_l.find(s.lower()) for s in headers]
    positions = filter(lambda p: p != -1, positions)
    
    if len(positions) == 0:
        return text
    
    pos = min(positions)
    
    return text[:pos]

TAG_REGEX = re.compile(r"<\s*(\w+).+?/\1\s*>", flags=re.DOTALL)


def remove_html_tags(text):
    pos = 0
    start_pos = 0
    last_block_end = 0
    new_string = ""
    while pos < len(text):
        if text[pos] == "<":
            start_pos = pos
        elif text[pos:pos+2] == "/>":
            new_string += text[last_block_end:start_pos] + " "
            pos += 2
            last_block_end = pos
        pos += 1
    new_string += text[last_block_end:]
    text = new_string
    
    new_string = ""
    last_end = 0
    for match in TAG_REGEX.finditer(text):
        new_string += text[last_end:match.start(0)] + " " 
        last_end = match.end(0)
    new_string += text[last_end:]
    
    return new_string

def remove_blocks(text, start, end):
    while True:
        end_pos = text.find(end)
        if end_pos == -1:
            break

        start_pos = text.rfind(start, 0, end_pos)
        if start_pos == -1:
            break

        block = text[start_pos:end_pos+2]
        text = text[:start_pos] + " " + text[end_pos+2:]

    return text
        
def remove_wiki_formatting(text):
    #text = text.lower()
    
    text = remove_tail(text)
    
    text = remove_blocks(text, "{{", "}}")
    text = remove_blocks(text, "{|", "|}")
    text = substitute_links(text)

    text = remove_block_regex(text, r"<!--", r"-->")
    text = remove_html_tags(text)
   
    text = text.replace(">", " ")
    text = text.replace("<", " ")
    #text = text.replace("-", " ")
    text = text.replace("&nbsp;", " ")
    text = text.replace("&gt;", ">")
    text = text.replace("&lt;", "<")
    text = text.replace("&amp;", " ")
    text = text.replace("|", " ")
    text = text.replace("/", " ")
    text = text.replace("}}", " ")
    text = text.replace("{{", " ")
    
    text = text.replace("===", "")
    text = text.replace("==", "")
    text = text.replace("=", "")
    text = text.replace("'''", "")
    text = text.replace("''", "")
    text = text.replace("*", "")
    text = text.replace("#", "")

    #text = text.replace(".", "")
    #text = text.replace(",", "")
    #text = text.replace("\"", "")
    #text = text.replace("(", "")
    #text = text.replace(")", "")
    #text = text.replace("'", "")
    #text = text.replace("?", "")
    #text = text.replace(";", "")
    #text = text.replace(":", "")
    #text = text.replace("!", "")

    blocks = text.split("\n")
    paragraphs = []
    for b in blocks:
        b = b.strip()
        b = " ".join(b.split())
        if len(b) != 0:
            paragraphs.append(b)

    return paragraphs

def translate(text, source, target, key):
    if len(text) > 5000:
        print text
        raise Exception, "Text longer than 5000 characters - %s" % len(text)
    
    url = "https://www.googleapis.com/language/translate/v2"
    
    params = {"format" : "text",
          "key" : key,
          "source" : source,
          "target" : target,
          "q" : text}
    
    #time.sleep(1.0)
    r = requests.get(url, params=params)
    
    if r.status_code != 200:
        print r.text
        raise Exception, "Bad result " + str(r.status_code)
    
    
    return r.json()["data"]["translations"][0]["translatedText"]

def parse_args(argv):
    parser = argparse.ArgumentParser(description="Wikipedia article fetcher and cleaner")
    
    parser.add_argument("--title", required=True, help="English title of desired article")
    parser.add_argument("--output", required=True, help="name of resulting json file")
    parser.add_argument("--key", required=True, help="Google Translate API key")
    parser.add_argument("--languages", required=False, nargs="+")

    args = parser.parse_args()

    return args

if __name__ == "__main__":
    args = parse_args(sys.argv)

    print "Fetching articles"
    articles = fetch_article(args.title, args.languages)

    cleaned_articles = []
    print "Cleaning articles"
    for lang, title, text, en_title in articles:
        
        print "Cleaning article for language", lang
        cleaned = remove_wiki_formatting(text)

        record = {"lang" : lang,
                  "title" : title,
                  "text" : cleaned,
                  "en_title" : en_title}

        if lang != "en":
            print "Translating from", lang, "to en"
            en_translation = []
            for paragraph in cleaned:
                print "Translating paragraph"
                translated = translate(paragraph, lang, "en", args.key)
                en_translation.append(translated)
            record["en_translation"] = en_translation
        else:
            round_trip_trans = {}
            for other_lang in args.languages:
                print "Roundtrip to", other_lang
                translation = []
                for paragraph in cleaned:
                    print "Translating paragraph"
                    translated = translate(paragraph, "en", other_lang, args.key)
                    translated = translate(translated, other_lang, "en", args.key)
                    translation.append(translated)
                round_trip_trans[other_lang] = translation
            record["roundtrip_translations"] = round_trip_trans
            

        cleaned_articles.append(record)
        
    print "Writing out results"
    fl = open(args.output, "w")
    fl.write(json.dumps(cleaned_articles, indent=2))
    fl.write("\n")
    fl.close()
