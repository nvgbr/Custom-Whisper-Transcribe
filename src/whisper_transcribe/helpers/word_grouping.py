#!/usr/bin/env python
# coding: utf-8
import itertools
import json
import re
from datetime import timedelta
from pathlib import Path
from typing import List

import nltk
import srt
from nltk import sent_tokenize, word_tokenize
from rich.console import Console
from rich.theme import Theme
from srt import Subtitle

custom_theme = Theme(
    {"success": "grey3 on pale_green1 bold", "error": "grey93 on red bold"}
)

console = Console(highlight=True, emoji=True, theme=custom_theme, emoji_variant="emoji")


def read_file(file_path: Path) -> str:
    """Read a file and return its contents as a string.

    Args:
        file_path (pathlib.WindowsPath): The path to the file to be read.

    Returns:
        str: The contents of the file.
    """
    with open(file_path, "r", encoding="utf-8") as file:
        if Path(file_path).suffix == '.json':
            content = json.load(file)
        else:
            content = file.read()
    return content


def get_save_path(file_path: Path) -> Path:
    """Get the directory path where the file is located.

    Args:
        file_path (pathlib.WindowsPath): The path to the file.

    Returns:
        pathlib.WindowsPath: The directory path where the file is located.
    """
    return Path(file_path).parent


def get_new_file_path_to_save(file_path: Path, text_to_add, suffix) -> Path:
    if not suffix.startswith('.'):
        suffix = '.' + suffix
    new_filename = f"{file_path.stem}_{text_to_add}{suffix}"
    return Path(file_path.parent / new_filename)

def build_new_srt(srt_sentences):
    """Sort and reindex the given SRT sentences.

    Args:
        srt_sentences (list): A list of SRT sentences.

    Returns:
        list: The sorted and reindexed list of SRT sentences.
    """
    new_srt = srt.sort_and_reindex(srt_sentences, in_place=True, skip=False)
    return list(new_srt)

def build_srt(data):
    word = str(srt.make_legal_content(data[3]))
    sub = [Subtitle(index=data[0],
                    start=timedelta(seconds=data[1]),
                    end=timedelta(seconds=data[2]),
                    content=word,
                    )]
    return list(sub)


# Initialize an empty list to store the new Subtitle objects
# Iterate through the srt_list, grouping the words into 2-4 word chunks
# while preserving the original sentence structure and timestamps

def tokenize_text(text: str, language: str = 'german') -> nltk.Text:
    """Tokenize the given text into sentences.

    Args:
        text (str): The text to be tokenized.
        language (str, optional): The language of the text. Defaults to 'german'.

    Returns:
        nltk.Text: The tokenized text as an NLTK Text object.
    """
    # text_tokenized = [word_tokenize(sentence) for sentence in sent_tokenize(text, language)]
    text_tokenized = sent_tokenize(text, language)
    return nltk.Text(text_tokenized)


def tokenize_words(words: str, language: str = 'german') -> nltk.Text:
    """Tokenize the given words into individual words.

    Args:
        words (str): The words to be tokenized.
        language (str, optional): The language of the words. Defaults to 'german'.

    Returns:
        nltk.Text: The tokenized words as an NLTK Text object.
    """
    srt_words_tokenized = word_tokenize(words, language="german")
    return nltk.Text(srt_words_tokenized)


def remove_punctuation(text: List[str]) -> List[List[str]]:
    """Remove punctuation from the given text and group the words into sentences.

    Args:
        text (list): A list of sentences.

    Returns:
        list: A list of sentences with punctuation removed and words grouped.
    """
    splitted_and_stripped_text = []
    grouped_words = []
    sentences = []
    for sentence in text:

        cleaned_string = re.sub("[%$!.,;:’“”—-]", '', sentence).split()
        grouped = list(itertools.chain.from_iterable(split_sentence_into_word_groups(cleaned_string)))
        if len(grouped) > 0:
            sentences.append(grouped)

    return sentences


def split_sentence_into_word_groups(sentence: List[str]) -> List[List[str]]:
    """Split the given sentence into word groups of 3 or 4 words.

    Args:
        sentence (list): A list of words.

    Returns:
        list: A list of word groups.
    """
    grouped_words = []

    if len(sentence) % 2 == 0:
        grouped_words.append([sentence[i:i + 4] for i in range(0, len(sentence), 4)])

    elif len(sentence) % 1 == 0:
        grouped_words.append([sentence[i:i + 3] for i in range(0, len(sentence), 3)])
    return grouped_words


def remove_processed_parts(data: List[dict], words_count: int) -> List[dict]:
    """Remove the processed parts from the given data.

    Args:
        data (list): The data to be processed.
        words_count (int): The number of words to be removed.

    Returns:
        list: The updated data with the processed parts removed.
    """
    for i, processed_part in enumerate(data[:words_count]):
        data.pop(0)
    return data


def build_srt_with_sentences(json_data, text_list: List[str]) -> List[Subtitle]:
    """Build a list of SRT subtitle objects from the given JSON data and text list.

    Args:
        json_data (): A list of JSON data containing word information.
        text_list (): A list of sentences.

    Returns:
        list: A list of SRT subtitle objects.
    """
    srt_words = []
    text_list_without_punctuation = remove_punctuation(text_list)
    sub_index_total = sum(len(sub_index) for sub_index in text_list_without_punctuation)
    words_total = sum(sum(len(words) for words in sentence) for sentence in text_list_without_punctuation)
    word_iterator = iter(range(words_total))
    json_data = clean_up_splitted_numbers(json_data)
    current_sub_index = 0

    for word_group in list(itertools.chain.from_iterable(text_list_without_punctuation)):
        word_to_json_map = list(map(lambda w: next((j for j in json_data if j['word'] == w), None), word_group))
        word_to_json_map = [item for item in word_to_json_map if item is not None]

        try:
            start_time = word_to_json_map[0]['start']
        except (IndexError, TypeError) as e:
            console.log(e)
            break

        joined_words = " ".join(item['word'] for item in word_to_json_map)

        try:
            end_time = word_to_json_map[-1]['end']
        except (IndexError, TypeError):
            end_time = json_data[-1]['end']

        srt_words.append(build_srt([current_sub_index, start_time, end_time, joined_words]))
        current_sub_index += 1

        json_data = remove_processed_parts(json_data, len(word_to_json_map))

    return list(itertools.chain.from_iterable(srt_words))


def clean_up_splitted_numbers(json_data: List[dict]) -> List[dict]:
    """Clean up the split numbers in the given JSON data.

    Args:
        json_data (list): A list of JSON data containing word information.

    Returns:
        list: The updated JSON data with split numbers cleaned up.
    """
    id_to_pop = []
    new_json = []
    for i, sub in enumerate(json_data):
        if re.fullmatch(r"\d", sub['word']):
            # print(sub)
            if re.fullmatch(r"\d", json_data[i + 1]['word']):
                sub['word'] = f"{sub['word']},{json_data[i + 1]['word']}"
                id_to_pop.append(i + 1)
                new_json.append(sub)
            else:
                new_json.append(sub)
        else:
            new_json.append(sub)

    for id in id_to_pop:
        new_json.pop(id)

    return new_json


def save_new_srt_file(new_srt_list: List[Subtitle], new_save_path: Path) -> None:
    """Save the new SRT file with the updated subtitle information.

    Args:
        new_srt_list (list): A list of SRT subtitle objects.
    """
    with open(new_save_path, "w", encoding="utf-8") as file:
        file.write(srt.compose(new_srt_list))



def main(text_file_path: Path, json_file_path: Path, **kwargs) -> None:
    """Main function to process the text and JSON data and save the new SRT file.

    Args:
        text_file_path (pathlib.WindowsPath): The path to the text file.
        json_file_path (pathlib.WindowsPath): The path to the JSON file.
    """
    console.print(f"{json_file_path=!r}")
    status = None
    if kwargs.get("status", None) != None:
        status = kwargs["status"]

    text_data = read_file(text_file_path)
    json_data = read_file(json_file_path)
    output_folder = get_save_path(json_file_path)
    # srt_list = build_srt(json_data)
    tokenized_text_sentences = tokenize_text(text_data, 'german')
    status.update("Building new SRT file...")
    srt_sentences = build_srt_with_sentences(json_data, tokenized_text_sentences.tokens)
    new_srt_data = build_new_srt(srt_sentences)
    status.update("Saving new SRT file...")
    new_file_path = get_new_file_path_to_save(text_file_path, "more_words", ".srt")
    save_new_srt_file(new_srt_data, new_file_path)


if __name__ == '__main__':
    json_file = Path(input("Please provide a path to the json file: "))
    text_file = Path(input("Please provide a Path to the text only file."))
    main(text_file_path=text_file, json_file_path=json_file)
