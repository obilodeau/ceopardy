# Ceopardy
# https://github.com/obilodeau/ceopardy/
#
# Olivier Bilodeau <olivier@bottomlesspit.org>
# Copyright (C) 2017 Olivier Bilodeau
# All rights reserved.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
import re

from model import FinalQuestion


def parse_questions(filename):
    """Parses a question file.
       Returns a dict (of categories) of lists of questions (in score order)
    """
    # TODO should drop the old format entirely?
    # if so use html and integrate answers into question file
    # people can then use asciidoctor or markdown to render questions from
    # a simpler format
    questions = {}
    cur_category = None
    try:
        with open(filename, 'r') as f:
            for line in f:
                line = line.rstrip("\r\n")

                # skip comments or whitespace lines
                if re.match(r'^\s*(#|$)', line):
                    continue

                # it's a category
                m = re.match(r'^>(.*)$', line)
                if m:
                    # create category entry
                    questions[m.group(1)] = list()
                    cur_category = m.group(1)
                    continue

                # convert fake new-lines into real ones
                line = re.sub(r'\\n', '\n', line)

                # it's a question
                questions[cur_category].append(line)

    except Exception as e:
        context = "Problem parsing the question file: {}".format(filename)
        raise QuestionParsingError(context) from e

    return questions


def parse_gamefile(filename):
    """Parses a game file. A game file holds the categories that are going to be
        played in order.
       Returns a list of category strings and a final question dict
    """
    # TODO should drop the old format entirely?
    # if so we need to be able to express final question somehow
    categories = list()
    final = None
    try:
        with open(filename, 'r') as f:
            for line in f:
                line = line.rstrip("\r\n")

                # match: final: [category] text
                m = re.match(r'final: \[([^]]+)\] (.*)$', line)
                if m:
                    final = FinalQuestion(category=m.group(1),
                                          question=m.group(2))
                    continue

                categories.append(line)

    except Exception as e:
        context = "Problem parsing the game file: {}".format(filename)
        raise GamefileParsingError(context) from e

    return categories, final


def question_to_html(question_text):
    return "<p>" + question_text + "</p>"


class QuestionParsingError(Exception):
    pass

class GamefileParsingError(Exception):
    pass
