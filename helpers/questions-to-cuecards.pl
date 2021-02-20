#!/usr/bin/env perl
#
# pass me the Jeopardy file and i'll give you asciidoc for cuecards
#
# meant to be run with cat Jeopardy | perl -n questions-to-cuecards.pl

# removed stricture because then I have problems with my BEGIN block globals
#use strict;
use warnings;

use feature 'say';

BEGIN {
    # state variables
    $in_category = 0;
    # number of questions parsed
    $q = 0;
}

chomp;

# hit the start of a category
if (/^>(.*)$/) {
    $in_category = 1;
    $q = 0;
    say "== $1\n";
    next;
}

if ($in_category) {
    # empty lines ends categories
    if (/^\s*$/) {
        $in_category = 0;
        say "\n<<<\n";
        next;
    }

    # meta comment is irrelevant to the show
    next if (/^# META:/);
    # NOTE comments goes on cue cards
    if (/^# NOTE: (.*)$/) {
        say "* $1";
        next;
    }
    # Every other comments are answers
    if (/^# (.*)$/) {
        say "* [$q] $1";
        next;
    }

    # otherwise its a question
    $q+=100;
}

# anything outside category is dropped
