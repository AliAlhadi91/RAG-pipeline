import copy
import json
import os
import pickle
import re
import sys
from argparse import ArgumentParser, Namespace
from copy import deepcopy
from typing import Any, List, Optional

from camel_tools.disambig.mle import MLEDisambiguator
from camel_tools.tokenizers import word  # to split text into a list of words
from camel_tools.tokenizers.morphological import (
    MorphologicalTokenizer,
)  # to tokenize according to morphology
from camel_tools.tokenizers.word import simple_word_tokenize
from camel_tools.utils.charmap import CharMapper
from camel_tools.utils.dediac import dediac_ar
from camel_tools.utils.normalize import (
    normalize_alef_maksura_ar,
    normalize_teh_marbuta_ar,
    normalize_unicode,
)
from camel_tools.utils.stringutils import force_unicode



def read_and_dediacritize(file_name: str) -> str:
    words = []
    with open(file_name, "r", encoding="utf-8") as file:  # Open the text file
        for line in file:
            word = line.strip()  # Remove any leading/trailing whitespace
            dediacritized_word = dediac_ar(word)  # Dediacritize the word
            words.append(dediacritized_word)
    return words


def is_utf8_encoded(filename: str) -> bool:
    """Check if the given file is UTF-8 encoded."""
    try:
        with open(filename, "r", encoding="utf-8") as file:
            file.read(1024)
        return True
    except Exception:
        return False


def par_is_utf8_encoded(paragraph: str) -> bool:
    try:
        paragraph.encode("utf-8")
        return True
    except UnicodeEncodeError:
        return False


def split_par(text: str) -> list[str]:
    # Split the text into paragraphs using one or more empty lines as delimiters
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    return paragraphs


class ArabicChars:
    alef_lam = b"\xd8\xa7\xd9\x84"  # ال
    lam_lam = b"\xd9\x84\xd9\x84"  # لل
    taa_marbouta_detached = b"\xef\xba\x93"  # ﺓ
    taa_marbouta_attached = b"\xd8\xa9"  # ة
    haa_attached = b"\xd9\x87"  # ه
    seen_attached = b"\xd8\xb3"  # س
    baa_attached = b"\xd8\xa8"  # ب
    faa_attached = b"\xd9\x81"  # ف
    waw = b"\xd9\x88"  # و

    haa = b"\xd9\x87\xd8\xa7"  # ها
    kaaf = b"\xd9\x83"  # ك
    lam = b"\xd9\x84"  # ل
    yaa = b"\xd9\x8a"  # ي
    maa = b"\xd9\x85\xd8\xa7"  # ما
    naa = b"\xd9\x86\xd8\xa7"  # نا
    alef = b"\xd8\xa3"  # أ
    nee = b"\xd9\x86\xd9\x8a"  # ني
    hum = b"\xd9\x87\xd9\x85"  # هم
    hunna = b"\xd9\x87\xd9\x86"  # هن
    koom = b"\xd9\x83\xd9\x85"  # كم
    houma = b"\xd9\x87\xd9\x85\xd8\xa7"  # هما


class DalleCamelPreprocess:
    def __init__(
            self,
            words_al_t: set[str],
            words_al: set[str],
            words_t: set[str],
            mle_msa: str = "calima-msa-r13",
            scheme: str = "d3tok",
            remove_all_suffix: bool = False,
            remove_all_prefix: bool = False,
    ) -> None:
        """
        > Remove all suffix when specified removes  taa_marbouta_detached,
        taa_marbouta_attached, and haa_attached
        > remove_all_prefix when set to True removes alef_lam, seen_attached,
        baa_attached, faa_attached
        """
        # Tokenizer related stuff
        self.scheme = scheme
        self.mle_msa = MLEDisambiguator.pretrained(mle_msa)
        self.msa_d3_tokenizer = MorphologicalTokenizer(
            disambiguator=self.mle_msa, scheme=scheme, split=True
        )
        # Unwanted tokens to remove at the end
        self.remove_all_suffix = remove_all_suffix
        self.remove_all_prefix = remove_all_prefix

        self.to_remove: set[str] = set()
        if self.remove_all_suffix:
            for token in [
                ArabicChars.taa_marbouta_detached,
                ArabicChars.taa_marbouta_attached,
                ArabicChars.haa_attached,
                ArabicChars.haa,
                ArabicChars.kaaf,
                ArabicChars.yaa,
                ArabicChars.maa,
                ArabicChars.naa,
                ArabicChars.nee,
                ArabicChars.hum,
                ArabicChars.hunna,
                ArabicChars.koom,
                ArabicChars.houma,
            ]:
                self.to_remove.add(f"+{token.decode('utf-8')}")
        if self.remove_all_prefix:
            for token in [
                ArabicChars.seen_attached,
                ArabicChars.baa_attached,
                ArabicChars.faa_attached,
                ArabicChars.alef_lam,
                ArabicChars.waw,
                ArabicChars.lam_lam,
                ArabicChars.lam,
                ArabicChars.alef,
                ArabicChars.kaaf,
            ]:
                self.to_remove.add(f"{token.decode('utf-8')}+")

        # Special words
        self.words_al_t: set[str] = words_al_t
        self.words_al: set[str] = words_al
        self.words_t: set[str] = words_t

    @staticmethod
    def simple_tokenize(text: str) -> Optional[list[str]]:
        # Check if the paragraph is UTF-8 encoded
        if par_is_utf8_encoded(text):
            text_list = word.simple_word_tokenize(text)
            return text_list
        else:
            return None

    @staticmethod
    def merge_alef_and_alef_lam(input_list: list[str]) -> list[str]:
        # utf-8 encoding of 1st element ل+ and 2nd element ال+
        pattern = [b"\xd9\x84+", b"\xd8\xa7\xd9\x84+"]
        # utf-8 encoding of لل+
        replacement = b"\xd9\x84\xd9\x84+".decode("utf-8")
        modified_list = []
        i = 0
        while i < len(input_list):
            if i < len(input_list) - 1:
                current_element = input_list[i].encode("utf-8")
                next_element = input_list[i + 1].encode("utf-8")
                if current_element == pattern[0] and next_element == pattern[1]:
                    modified_list.append(replacement)
                    i += 2
                    continue
            modified_list.append(input_list[i])
            i += 1
        return modified_list

    def process_noan_word(self, word: str) -> list[str]:
        """Tokenizes NOAN words that are not tokenized via the morphological tokenizer"""
        word_bytes = word.encode("utf-8")

        start = (
            2
            if word_bytes.startswith(ArabicChars.alef_lam)
               and (word in self.words_al_t or word in self.words_al)
            else 0
        )

        end = (
            -1
            if (
                       word_bytes.endswith(ArabicChars.taa_marbouta_detached)
                       or word_bytes.endswith(ArabicChars.taa_marbouta_attached)
               )
               and (word in self.words_al_t or word in self.words_t)
            else len(word)
        )

        raw_tokens = [
            f"{word[0:start]}+" if start > 0 else "",
            word[start:end],
            f"+{word[end:len(word)]}" if end < len(word) else "",
        ]

        tokens = [token for token in raw_tokens if token.strip()]
        return tokens

    @staticmethod
    def merge_tokens(tokens: list[str]) -> str:
        """Correcting tokens after the removal of al and t-marbota"""
        merged_word = ""
        parts: list[str] = []
        for token in tokens:
            start = 1 if token.startswith("+") else 0
            end = -1 if token.endswith("+") else len(token)
            parts.append(token if end - start == len(token) else token[start:end])

        merged_word = "".join(parts)

        return merged_word

    @staticmethod
    def split_token_on_t(list_toks: list[str]) -> list[str]:
        """
        Splits the token on ة and ه
        Replaces the end with prefix, + (token)
        """
        new_list = []

        for token in list_toks:
            token_bytes = token.encode("utf-8")
            if (
                    token_bytes.endswith(ArabicChars.taa_marbouta_detached)
                    or token_bytes.endswith(ArabicChars.taa_marbouta_attached)
                    or token_bytes.endswith(ArabicChars.haa_attached)
            ):
                if token_bytes == ArabicChars.haa_attached:  # replacing ه with ة

                    token = "+" + ArabicChars.taa_marbouta_attached.decode("utf-8")
                    new_list.append(token)
                else:
                    new_list.extend([token[:-1], f"+{token[-1]}"])

            else:
                new_list.append(token)

        return new_list

    def morph_tokenize(self, words: list[str], split: bool = True):
        """
        Generate morphological tokens for a given list of words.

        Args:
            words (list of str): List of words to tokenize.
            disambiguator: A disambiguator instance used for morphological analysis.
            scheme (str, optional): Tokenization scheme. Defaults to 'd3tok'.
            split (bool, optional): Whether to split the tokens. Defaults to True.

        Returns:
            list of str: List of morphologically tokenized words.
        """
        # # What is the difference between d3tok and bwtok.
        disambig_words = self.mle_msa.disambiguate(words)
        result: list[str] = []

        for disambig_word in disambig_words:
            scored_analyses = disambig_word.analyses
            original_word = dediac_ar(disambig_word.word)
            if not scored_analyses:
                result.append(original_word)
                continue

            analysis = scored_analyses[0].analysis

            token = dediac_ar(analysis.get(self.scheme, None))
            token_bw = dediac_ar(analysis.get("bwtok", None))
            original_word_bytes = original_word.encode("utf-8")

            if original_word_bytes.endswith(
                    ArabicChars.taa_marbouta_attached
            ) or original_word_bytes.endswith(ArabicChars.taa_marbouta_detached):
                if "+ة_+" in token_bw or "+ه" in token_bw:
                    tokens = token.split("_")
                    tokens = self.split_token_on_t(tokens)
                    tokens = self.merge_alef_and_alef_lam(tokens)
                    merged_tokens = dediac_ar(self.merge_tokens(tokens))

                    if merged_tokens == original_word:
                        result.extend(tokens)
                        continue
                    else:
                        result.append(original_word)
                        # log_errors

                        continue

            if token is None or "NOAN" in token:
                token = dediac_ar(disambig_word.word)
                # token = self.process_noan_word(original_word)
                token = self.process_noan_word(token)
                result.extend(token)

            else:
                token = dediac_ar(token)
                if not split:
                    result.append(token if token == original_word else original_word)

                else:
                    tokens = token.split("_")

                    tokens = self.merge_alef_and_alef_lam(tokens)
                    merged_tokens = dediac_ar(self.merge_tokens(tokens))

                    if merged_tokens == original_word:
                        result.extend(tokens)

                    else:
                        result.append(original_word)

        return list(result)

    def tokenize(self, content: str) -> list[str]:

        pars = []
        for par in split_par(content):
            par_list: list[str] = self.simple_tokenize(par)
            tokenized_par_i = self.morph_tokenize(par_list)
            tokenized_par = self.merge_alef_and_alef_lam(tokenized_par_i)
            pars.extend(
                [token for token in tokenized_par if token not in self.to_remove]
            )

        return pars


class CamelTextPreProcessor:
    def __init__(
            self,
            mapper=None,
            mapper_model: str = "arclean",
            words_al_t_path: str = "cleaning/noan/words_al_t.txt",
            words_al_path: str = "cleaning/noan/words_al.txt",
            words_t_path: str = "cleaning//noan/words_t.txt",
            mle_msa: str = "calima-msa-r13",
            scheme: str = "d3tok",
            remove_all_prefix: bool = True,
            remove_all_suffix: bool = True,
    ) -> None:
        self._mapper = mapper if mapper else CharMapper.builtin_mapper(mapper_model)
        self.mle_msa = mle_msa
        self.scheme = scheme
        self.remove_all_prefix = remove_all_prefix
        self.remove_all_suffix = remove_all_suffix
        self.list_al_t = set(read_and_dediacritize(words_al_t_path))
        self.list_al = set(read_and_dediacritize(words_al_path))
        self.list_t = set(read_and_dediacritize(words_t_path))

        self._tokenizer = DalleCamelPreprocess(
            remove_all_suffix=self.remove_all_suffix,
            remove_all_prefix=self.remove_all_prefix,
            words_al_t=self.list_al_t,
            words_al=self.list_al,
            words_t=self.list_t,
            mle_msa=self.mle_msa,
            scheme=self.scheme,
        )

    def clean(self, text: str) -> str:
        """Remove trailing spaces, special characters ..."""
        cleaned_text = self._arclean_text(text)
        cleaned_text = re.sub(r"\s+", " ", cleaned_text)
        cleaned_text = cleaned_text.strip()
        return cleaned_text

    def normalize(self, text: str) -> str:
        """Normalize the text"""
        return normalize_unicode(text)

    def _arclean_text(self, text: str) -> str:
        """Taken from https://github.com/CAMeL-Lab/camel_tools/blob/master/camel_tools/cli/camel_arclean.py#L83"""
        text = force_unicode(text)
        return self._mapper.map_string(text)

    def normalize_special_characters(self, text: str) -> str:
        """makes the alef maksura into regular alef, and the teh marbuta. returns the string in unicode"""
        text = normalize_alef_maksura_ar(text)
        text = normalize_teh_marbuta_ar(text)
        return text

    def simple_tokenize(self, text: str) -> list[str]:
        """Tokenizes the text"""
        simple = simple_word_tokenize(text)
        return simple

    def morphologically_tokenize(self, text: str) -> list[str]:
        """Tokenizes the text"""
        tokenized = self._tokenizer.tokenize(text)
        return tokenized

    def light_stem(self, text: str) -> str:
        """removes the prefixes and suffixes from the text, not being used currently"""
        words = text.split()
        result = []
        _ = [result.extend(self._tokenizer.tokenize(word)) for word in words]
        return " ".join(result)

    def preprocess_arabic(self, text: str) -> str:
        """Preprocesses the arabic text"""
        cleaned_text = self.clean(text)
        normalized_text = self.normalize(cleaned_text)

        return normalized_text

    def prepare_to_morphologically_tokenize(self, text: str) -> str:
        """Prepares the text for tokenization"""
        text = self.normalize_special_characters(text)
        return text