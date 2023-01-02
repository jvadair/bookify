from pypdf import PdfReader
from ocrmypdf import ocr
from word2number import w2n
from ebooklib import epub
from uuid import uuid4
import spellcheck


# Metadata collection
PDF = input('Path to PDF [>] ')
OCR = ''
while not OCR in ('y', 'n'):
    OCR = input("Is the PDF text-searchable? y/n [>] ")
OCR = True if OCR == 'y' else False
TITLE = input('Book title [>] ')
IDENTIFIER = input('ISBN (leave blank for random book identifier) [>] ')
if not IDENTIFIER:
    IDENTIFIER = str(uuid4())
LANGUAGE = input('Language code (leave blank for "en") [>] ')
if not LANGUAGE:
    LANGUAGE = "en"
AUTHOR = input("Author [>] ")
COVER = input('Path to cover image [>] ')
PAGE_NUMBERS = ''
while not PAGE_NUMBERS in ('top', 'bottom', 'none'):
    PAGE_NUMBERS = input("Where are the page numbers? Choose either 'top', 'bottom', or 'none' [>] ")
SPELL_CHECK = ''
while not SPELL_CHECK in ('y', 'n'):
    SPELL_CHECK = input('Would you like to spell-check the book? y/n [>] ')
SPELL_CHECK = True if SPELL_CHECK == 'y' else False


if not OCR:
    new_file = PDF.replace('.pdf', '_searchable.pdf')
    print("Creating new text-searchable file: " + new_file)
    print("Please wait...")
    ocr(PDF, new_file)
    PDF = new_file
    print('OCR complete!')

print("Loading PDF file...")
reader = PdfReader(PDF)
chapter_headers = []


# noinspection PyShadowingNames
def find_chapter_locations(reader: PdfReader) -> list:
    chapter_positions = []
    for page, page_number in zip(reader.pages, range(0, len(reader.pages))):
        text = page.extract_text()
        text_lines = text.split('\n')
        for line in text_lines:
            original_line = line
            line = line.lower().replace(' ', '')
            if line.lower().startswith('chapter'):
                chapter_num = line.replace('chapter', '')  # Chapter one -> one
                try:
                    chapter_num = w2n.word_to_num(chapter_num)  # str(two) -> int(2) or str(2) -> int(2)
                    # If valid chapter,
                    chapter_positions.append(page_number)
                    chapter_headers.append(original_line)
                except ValueError:
                    pass
    return chapter_positions

def reflow_text(text):  # Also replaces the weird punctuation alternative characters
    text = text\
        .replace('-\n', '')\
        .replace('\n-', '')\
        .replace('- \n', '')\
        .replace('\n -', '')\
        .replace('\n', ' ')\
        .replace('  ', ' ')\
        .replace('”', '"')\
        .replace('“', '"')\
        .replace('’', "'")\
        .replace('‘', "'")
    return text


def fix_page_numbers(text):
    split_text = text.split(' ')
    if PAGE_NUMBERS == 'top':
        if split_text[0].replace('\n', '').isnumeric():
            text = ' '.join(split_text[1:])  # Removes the first section if it's a number
    elif PAGE_NUMBERS == 'bottom':
        if split_text[-1].replace('\n', '').isnumeric():
            text = ' '.join(split_text[:-1])  # Removes the last section if it's a number
    return text


def get_chapter_text(reader, num):
    starting_page = chapter_locations[num]
    try:
        ending_page = chapter_locations[num + 1]
    except IndexError:
        ending_page = len(reader.pages)
    pages = reader.pages[starting_page:ending_page]
    text = []
    for page in pages:
        text.append(fix_page_numbers(page.extract_text()))
    text[0] = text[0].replace(chapter_headers[num] + '\n', '')
    text = '\n'.join(text)
    text = reflow_text(text)
    if SPELL_CHECK:
        text = spellcheck.interactive_spellcheck(text)
    return text

def create_chapter(reader, num):  # Remember, num for chapter 1 is 0
    text = get_chapter_text(reader, num)
    # create chapter
    chapter = epub.EpubHtml(title=f"Chapter {str(num+1)}", file_name=f"ch{str(num+1)}.xhtml", lang=LANGUAGE)
    chapter.content = (
        f"<h1>Chapter {str(num+1)}</h1>"
        f"<p>{text}</p>"
    )
    return chapter

def generate_chapters(reader):
    chapters = []
    for i in range(0, len(chapter_locations)):
        chapters.append(create_chapter(reader, i))
    return chapters


book = epub.EpubBook()
chapter_locations = find_chapter_locations(reader)

# set metadata
book.set_identifier(IDENTIFIER)
book.set_title(TITLE)
book.set_language(LANGUAGE)

book.add_author(AUTHOR)
# book.add_author(  # May be implemented some day
#     "Danko Bananko",
#     file_as="Gospodin Danko Bananko",
#     role="ill",
#     uid="coauthor",
# )

# create image from the local image
image_content = open(COVER, "rb").read()
img = epub.EpubImage(
    uid="cover",
    file_name=COVER,
    media_type=f"image/{COVER.rsplit('.', maxsplit=1)[-1]}",  # Gets the extension from the filename
    content=image_content,
)

# add chapters
print('Please wait...')
chapters = generate_chapters(reader)
for chapter in chapters: book.add_item(chapter)
# add image
book.add_item(img)

# define Table Of Contents
book.toc = [epub.Link(f'ch{str(i+1)}.xhtml', f'Chapter {str(i+1)}', f'ch{str(i+1)}') for i in range(0, len(chapter_locations))]


# add default NCX and Nav file
book.add_item(epub.EpubNcx())
book.add_item(epub.EpubNav())

# define CSS style
style = "BODY {color: white;}"
nav_css = epub.EpubItem(
    uid="style_nav",
    file_name="style/nav.css",
    media_type="text/css",
    content=style,
)

# add CSS file
book.add_item(nav_css)

# basic spine
book.spine = ["nav", *chapters]

# write to the file
epub.write_epub(TITLE + '.epub', book, {})

print('Done!')