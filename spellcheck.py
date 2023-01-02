"""
An interactive spell-checker program designed for bookify.
"""
from spellchecker import SpellChecker
import os
from string import punctuation

punctuation += "—"
home = os.path.expanduser("~")
spell = SpellChecker()
ignore_all = []
replacements = {}
add_to_dictionary = []
bookify_dictionary = os.path.join(home, '.bookify-dictionary')


try:
    spell.word_frequency.load_text_file(bookify_dictionary)
except FileNotFoundError:
    open(bookify_dictionary, 'a+').close()  # creates new file
    spell.word_frequency.load_text_file(bookify_dictionary)  # try again

def clear():
    os.system('cls' if os.name == 'nt' else 'clear')


def error(message):
    clear()
    print('=== ERROR! ===')
    print(message)
    input('Press enter to continue...')

def menu(title, *options, clearscreen=True):
    while True:
        if clearscreen: clear()
        x = menu_sub(title, *options)
        if x is not None: break
        error('Please choose one of the provided options.')
    return x


def menu_sub(title, *options):
    print('=' * 3, title, '=' * 3)
    for option, n in zip(options, range(0, len(options))):
        print(f'[{str(n)}] {option}')
    try:
        response = input('\n[>] ')
        # noinspection PyUnboundLocalVariable
        response = int(response)
        return response if response < len(options) else None
    except ValueError:
        return None

class UnknownWord:
    def __init__(self, word: str, context_before: list, context_after: list, position: int, punctuation_before, punctuation_after):
        self.word = word
        self.context_before = context_before
        self.context_after = context_after
        self.position = position
        candidates = spell.candidates(word)
        self.suggestions = list(candidates) if candidates else []
        self.punctuation_before = punctuation_before
        self.punctuation_after = punctuation_after
        self.as_written = punctuation_before + word + punctuation_after


def find_all_indexes(item, text: list):
    indexes = [i for i, x in enumerate(text) if x == item]
    return indexes


def depunctuate(text: list, from_beginning=False):
    # Only removes punctuation from the end/start. Not ideal in all circumstances, but better than the alternative
    depunctuated = []
    punctuation_removed = []
    for word in text:
        if not word:  # empty string
            # We can't merely remove empty strings since they will reappear later and will throw off indexes
            depunctuated.append('valid')  # Placeholder which will be ignored
            punctuation_removed.append('')
        elif word[0 if from_beginning else -1] in punctuation and len(word) > 1:
            # Grab ALL punctuation from the end/start, not just the last character
            i = 1 if from_beginning else -1
            try:
                while True:
                    if word[i] in punctuation:
                        i += 1 if from_beginning else -1
                    else:
                        i -= 1 if from_beginning else -1  # Go back to last correct index
                        break
            except IndexError:  # Only punctuation
                depunctuated.append(word)  # The spell-checker will cry about this, but it's best to let it do so.
                punctuation_removed.append('')
                continue
            depunctuated.append(word[i+1:] if from_beginning else word[:i])
            punctuation_removed.append(word[:i+1] if from_beginning else word[i:])
        else:
            # A single punctuation mark won't be yelled at by the spell-checker
            depunctuated.append(word)
            punctuation_removed.append('')
    return depunctuated, punctuation_removed


def find_unknown_words(text):
    split_text = text.split(' ')
    depunctuated, punctuation_before = depunctuate(split_text, from_beginning=True)
    depunctuated, punctuation_after = depunctuate(depunctuated, from_beginning=False)
    unknown = spell.unknown(depunctuated)
    for word in list(unknown):  # Create a copy of the list
        # Don't yell at all hyphenated words
        word_fixed = word.replace('—', '-')
        if '-' in word_fixed:
            unknown_subwords = spell.unknown(word_fixed.split('-'))
            if not unknown_subwords: unknown.remove(word)  # If it knows both of the words, preserve original character
    out = []
    positions = []
    for word in unknown:
        indexes = find_all_indexes(word, depunctuated)
        for index in indexes:
            if index not in positions:
                positions.append(index)
                # max/min prevents IndexErrors
                context_before = split_text[max(0, index-10):index]
                context_after = split_text[index+1:min(len(text), index+10)]
                out.append(UnknownWord(word, context_before, context_after, index, punctuation_before[index], punctuation_after[index]))
    return out


def replace_instances(incorrect: UnknownWord, correct: str, text: str, unknown_words: list):
    instances = [item for item in unknown_words if item.word == incorrect.word]
    text = text.split(' ')
    for instance in instances:
        text[instance.position] = incorrect.punctuation_before + correct + incorrect.punctuation_after
    return ' '.join(text)


# noinspection DuplicatedCode
def interactive_spellcheck(text):
    unknown_words = find_unknown_words(text)
    while True:
        # This allows us to modify the list as we remove elements, and the first item should always be a new word or instance.
        clear()
        try:
            word = unknown_words[0]
        except IndexError:  # The list is empty
            break
        if word in ignore_all:  # Cross-chapter ingore-all
            unknown_words = [item for item in unknown_words if item.word != word.word]  # Removes the word from the list
            continue
        elif word in replacements.keys():  # cross-chapter replace-all
            text = replace_instances(word, replacements[word], text, unknown_words)
            unknown_words = [item for item in unknown_words if item.word != word.word]
            continue
        print(f'{" ".join(word.context_before)} \033[1;31m{word.word}\033[1;0m{word.punctuation_after} {" ".join(word.context_after)}')
        choice = menu("Suggestions", '[Ignore]', '[Ignore all]', "[Add to dictionary]", "[Choose custom word]", *word.suggestions[:4], clearscreen=False)
        if choice == 0:
            unknown_words.remove(word)
        elif choice == 1:
            unknown_words = [item for item in unknown_words if item.word != word.word]
            ignore_all.append(word.word)  # Other chapters may use this word, but it wouldn't be detected otherwise
        elif choice == 2:
            spell.word_frequency.add(word.word)  # Add to dictionary
            add_to_dictionary.append(word.word)  # Remember for later runs of the program
            unknown_words = [item for item in unknown_words if item.word != word.word]
        elif choice == 3:
            print()
            replace_punctuation = menu("Replace punctuation also?", "No", "Yes", clearscreen=False)
            if replace_punctuation:
                word.punctuation_before, word.punctuation_after = ("", "")
                word.word = word.as_written
            print()
            correct = input('Type the correct word [>] ')
            replace_all = menu("Replace all instances?", "No", "Yes")
            if replace_all:
                text = replace_instances(word, correct, text, unknown_words)
                unknown_words = [item for item in unknown_words if item.word != word.word]
                replacements[word] = correct
            else:
                text = replace_instances(word, correct, text, [word])  # Replaces single word
                unknown_words.remove(word)
        else:
            correct = word.suggestions[choice-4]
            replace_all = menu("Replace all instances?", "No", "Yes")
            if replace_all:
                text = replace_instances(word, correct, text, unknown_words)
                unknown_words = [item for item in unknown_words if item.word != word.word]
                replacements[word] = correct
            else:
                text = replace_instances(word, correct, text, [word])
                unknown_words.remove(word)
    with open(bookify_dictionary, 'a+') as file:  # Save added words
        file.write('\n'.join(add_to_dictionary) + '\n')
    return text